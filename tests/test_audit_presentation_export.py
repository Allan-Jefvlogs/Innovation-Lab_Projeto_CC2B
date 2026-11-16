from __future__ import annotations

import re
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from Meu_projeto.services.audit_export import (
    AuditExportConsistencyError,
    AuditExportLimitError,
    collect_all_audit_logs,
)
from Meu_projeto.services.audit_format import format_changes, present_event
from Meu_projeto.services.audit_pdf import COLUMNS, build_audit_pdf, extract_hex_pdf_text


class AuditPresentationTests(unittest.TestCase):
    def test_user_update_without_details_is_explicit(self):
        event = present_event({
            "occurred_at": 1794700000000,
            "actor_name": "Operador",
            "action_type": "atualizado",
            "entity_type": "usuario",
            "summary": "Cadastro atualizado; dados pessoais omitidos.",
            "changes": None,
        })
        self.assertEqual(event["alteracoes"], "Detalhes não registrados")
        self.assertEqual(event["acao"], "Atualizado")
        self.assertEqual(event["entidade"], "Usuário")

    def test_created_user_profile_is_resolved_only_from_supplied_map(self):
        changes = {"inventory_profile_id": 4}
        self.assertEqual(
            format_changes(changes, profile_names={4: "Compras"}),
            "Perfil atribuído: Compras",
        )
        self.assertEqual(format_changes(changes), "Perfil atribuído: Perfil (ID 4)")

    def test_supplier_contact_values_are_omitted(self):
        result = format_changes({"contato": True, "endereco": True})
        self.assertIn("Contato atualizado (valores omitidos)", result)
        self.assertIn("Endereço atualizado (valores omitidos)", result)
        self.assertNotIn("True", result)

    def test_supplier_creation_does_not_reveal_possible_person_name_or_document(self):
        result = format_changes({
            "nome_razao_social": "Pessoa Exemplo",
            "tipo_documento": "CPF",
            "documento": "12345678900",
        })
        self.assertNotIn("Pessoa Exemplo", result)
        self.assertNotIn("12345678900", result)
        self.assertIn("Nome/razão social alterado (valores omitidos)", result)
        self.assertIn("Tipo de documento: CPF", result)

    def test_sensitive_values_are_never_rendered(self):
        changes = {
            "before": {"email": "private@example.test", "cpf": "12345678900", "token": "secret-token", "api_key": "key-before"},
            "after": {"email": "new@example.test", "cpf": "99999999999", "token": "new-secret", "api_key": "key-after"},
        }
        result = format_changes(changes)
        for secret in ("private@example.test", "new@example.test", "12345678900", "99999999999", "secret-token", "new-secret", "key-before", "key-after"):
            self.assertNotIn(secret, result)
        self.assertIn("E-mail atualizado (valores omitidos)", result)

    def test_permission_codes_are_translated_and_product_status_is_preserved(self):
        permissions = format_changes({
            "revision_before": 1,
            "revision_after": 2,
            "permissions_added": ["purchase_request.manage"],
            "permissions_removed": ["product.read"],
        })
        self.assertIn("Gerenciar solicitações de compra", permissions)
        self.assertIn("Consultar produtos", permissions)
        self.assertNotIn("purchase_request.manage", permissions)
        status = format_changes({"before": {"status": "inativo"}, "after": {"status": "ativo"}})
        self.assertEqual(status, "Status: Inativo → Ativo")

    def test_unknown_json_is_not_echoed(self):
        raw = {"unknown_secret_field": "do-not-display"}
        result = format_changes(raw)
        self.assertNotIn("unknown_secret_field", result)
        self.assertNotIn("do-not-display", result)


class AuditExportCollectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_collects_all_pages_with_same_filters(self):
        calls = []
        filters = {"date_from": 10, "date_to": 99, "actor_user_id": 7, "action_type": "criado", "entity_type": "usuario"}

        async def fetch_page(*, page, per_page, **kwargs):
            calls.append((page, per_page, kwargs))
            start = (page - 1) * per_page
            items = [{"id": row_id} for row_id in range(start + 1, min(start + per_page, 205) + 1)]
            return {"items": items, "itemsTotal": 205, "curPage": page, "perPage": per_page}

        rows = await collect_all_audit_logs(fetch_page, filters=filters)
        self.assertEqual(len(rows), 205)
        self.assertEqual([call[0] for call in calls], [1, 2, 3])
        self.assertTrue(all(call[2] == filters for call in calls))

    async def test_limit_refuses_partial_export_without_fetching_more_pages(self):
        calls = []

        async def fetch_page(*, page, per_page, **kwargs):
            calls.append(page)
            return {"items": [{"id": 1}], "itemsTotal": 501, "curPage": 1, "perPage": per_page}

        with self.assertRaises(AuditExportLimitError):
            await collect_all_audit_logs(fetch_page, filters={})
        self.assertEqual(calls, [1])

    async def test_empty_filtered_result_returns_empty_list(self):
        async def fetch_page(*, page, per_page, **kwargs):
            return {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": per_page}

        self.assertEqual(await collect_all_audit_logs(fetch_page, filters={}), [])

    async def test_changed_total_or_duplicate_pages_fail_closed(self):
        async def changed_total(*, page, per_page, **kwargs):
            total = 2 if page == 1 else 3
            return {"items": [{"id": page}], "itemsTotal": total, "curPage": page, "perPage": per_page}

        with self.assertRaises(AuditExportConsistencyError):
            await collect_all_audit_logs(changed_total, filters={})

        async def duplicate(*, page, per_page, **kwargs):
            return {"items": [{"id": 1}], "itemsTotal": 2, "curPage": page, "perPage": per_page}

        with self.assertRaises(AuditExportConsistencyError):
            await collect_all_audit_logs(duplicate, filters={})

    async def test_transport_or_authorization_error_is_not_converted_to_partial_success(self):
        async def failing(*, page, per_page, **kwargs):
            raise PermissionError("denied")

        with self.assertRaises(PermissionError):
            await collect_all_audit_logs(failing, filters={})


class AuditPdfTests(unittest.TestCase):
    @staticmethod
    def _extract_text_and_fill_colors(pdf: bytes) -> list[tuple[str, tuple[float, float, float]]]:
        """Inspect each text operator with the active PDF fill color."""
        streams = re.findall(rb"stream\n(.*?)\nendstream", pdf, flags=re.DOTALL)
        token = re.compile(
            rb"(?P<color>-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+rg)"
            rb"|<(?P<text>[0-9A-F]+)> Tj"
        )
        rendered = []
        for stream in streams:
            active_color = (0.0, 0.0, 0.0)
            for match in token.finditer(stream):
                if match.group("color"):
                    active_color = tuple(float(value) for value in match.group("color").split()[:3])
                else:
                    text = bytes.fromhex(match.group("text").decode("ascii")).decode("cp1252")
                    rendered.append((text, active_color))
        return rendered

    def test_pdf_contains_required_header_filters_columns_and_wrapped_long_text(self):
        long_text = "Descrição com informação longa " * 110
        pdf = build_audit_pdf(
            [{
                "data": "15/11/2026 12:30:00",
                "usuario": "Operador",
                "acao": "Atualizado",
                "entidade": "Produto",
                "registro": "42",
                "resumo": long_text,
                "alteracoes": "Descrição: antes → " + long_text,
            } for _ in range(4)],
            filters_description="Período: 2026-11-01 a 2026-11-15; Ação: atualizado",
            emitted_at=datetime(2026, 11, 15, 12, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        )
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"startxref", pdf)
        xref_offset = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
        self.assertTrue(pdf[xref_offset:].startswith(b"xref\n"))
        page_count = int(re.search(rb"/Count (\d+)", pdf).group(1))
        self.assertGreater(page_count, 1)
        self.assertEqual(len(re.findall(rb"/Type /Page\b", pdf)), page_count)
        self.assertGreaterEqual(pdf.count(b"/MediaBox [0 0 842.00 595.00]"), page_count)
        extracted = extract_hex_pdf_text(pdf)
        for expected in (
            "NextStock", "Relatório de Auditoria", "Emitido em", "Período:",
            "Data e hora", "Usuário", "Ação", "Entidade", "Registro", "Resumo", "Alterações",
            "Página 1 de", "Descrição com informação longa",
        ):
            self.assertIn(expected, extracted)
        self.assertIn("->", extracted)

    def test_empty_pdf_is_structurally_valid_but_empty_result_is_handled_by_state(self):
        pdf = build_audit_pdf([], filters_description="Ação: criado")
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertEqual(int(re.search(rb"/Count (\d+)", pdf).group(1)), 1)


    def test_exported_audit_text_is_visible_and_uses_safe_presented_values(self):
        event = present_event({
            "occurred_at": 1794760200000,
            "actor_name": "Operador QA",
            "action_type": "atualizado",
            "entity_type": "produto",
            "entity_id": 42,
            "summary": "Produto atualizado para apresentaÃ§Ã£o.",
            "changes": {
                "before": {"status": "inativo", "email": "private@example.test", "cpf": "12345678900"},
                "after": {"status": "ativo", "email": "other@example.test", "cpf": "99999999999"},
            },
        })
        pdf = build_audit_pdf(
            [event],
            filters_description="AÃ§Ã£o: atualizado",
            emitted_at=datetime(2026, 11, 15, 12, 30, tzinfo=ZoneInfo("America/Sao_Paulo")),
        )

        rendered = self._extract_text_and_fill_colors(pdf)
        texts = [text for text, _ in rendered]
        combined = " ".join(texts)
        for label, _, _ in COLUMNS:
            self.assertIn(label, combined)
        for expected in ("Operador QA", "Atualizado", "Status: Inativo -> Ativo"):
            self.assertIn(expected, combined)
        for sensitive in ("private@example.test", "other@example.test", "12345678900", "99999999999"):
            self.assertNotIn(sensitive, combined)

        self.assertTrue(rendered)
        for text, color in rendered:
            self.assertLessEqual(max(color), 0.2, f"Text was rendered too pale: {text!r} with {color}")


class AuditAuthorizationContractTests(unittest.TestCase):
    def test_page_and_xano_endpoint_keep_administrator_checks(self):
        root = Path(__file__).resolve().parents[1]
        page_source = (root / "Meu_projeto/pages/auditoria.py").read_text(encoding="utf-8")
        endpoint_source = (root / "xano/api/inventory_stock/audit_logs_get.xs").read_text(encoding="utf-8")
        export = page_source.split("async def export_pdf", 1)[1]
        self.assertIn("if not auth.is_administrator", export)
        self.assertLess(export.index("if not auth.is_administrator"), export.index("auth_client.list_audit_logs"))
        self.assertIn('permission_code: "administrator"', endpoint_source)


if __name__ == "__main__":
    unittest.main()
