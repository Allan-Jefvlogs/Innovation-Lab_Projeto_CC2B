"""Contratos locais do perfil Compras, sem chamadas ou escritas no Xano."""

from __future__ import annotations

import unittest
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from Meu_projeto.pages.compras import STATUS_OPTIONS, PurchaseManagementState, _log_list_failure, _log_detail_failure
from Meu_projeto.services.xano_client import (
    XanoAuthClient, XanoRequestError, XanoServerError, XanoConnectionError,
    XanoAuthError, XanoPermissionError, XanoRateLimitError,
)
from Meu_projeto.services.session_read_cache import session_read_cache
from Meu_projeto.state.auth import AuthState


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PurchaseManagementStructureTests(unittest.TestCase):
    def test_detail_back_is_secondary_button_and_history_controls_are_conditional(self):
        xs = source("Meu_projeto/pages/compras.py")
        detail = xs.split("def compra_detalhe()", 1)[1]
        self.assertIn('rx.button(rx.icon("arrow-left", size=16), "Voltar", on_click=rx.redirect("/compras"), variant="soft"', detail)
        self.assertNotIn("Voltar para Compras solicitadas", detail)
        self.assertIn("rx.cond(PurchaseManagementState.history_page_total > 1, rx.hstack(", detail)
        self.assertIn('rx.text("Página ", PurchaseManagementState.history_page, " de ", PurchaseManagementState.history_page_total', detail)
        self.assertIn("on_click=PurchaseManagementState.previous_history_page", detail)
        self.assertIn("on_click=PurchaseManagementState.next_history_page", detail)

    def test_detail_history_preserves_pagination_and_authorization_before_history(self):
        xs = source("xano/api/inventory_stock/purchase_requests_by_id_get.xs")
        query = xs.split("db.query purchase_request_history", 1)[1]
        projection = re.search(r'output\s*=\s*\[(.*?)\]', query, re.S)
        self.assertIsNotNone(projection)
        fields = re.findall(r'"([^"]+)"', projection.group(1))
        for field in ("itemsTotal", "curPage", "perPage", "items.id", "items.evento"):
            self.assertIn(field, fields)
        self.assertIn('paging: {page: $input.history_page, per_page: $input.history_per_page, totals: true}', query)
        self.assertIn("historico: $history_page", xs)
        self.assertEqual(xs.count("db.query "), 1)
        self.assertLess(xs.index("precondition ($scope.all_access || $request.solicitante_usuario_id == $auth.id)"), xs.index("db.query purchase_request_history"))
        self.assertIn('sort = {data_evento: "desc", id: "desc"}', query)

    def test_list_query_preserves_root_pagination_metadata_in_public_projection(self):
        xs = source("xano/api/inventory_stock/purchase_requests_get.xs")
        projection = re.search(r'output\s*=\s*\[(.*?)\]', xs, re.S)
        self.assertIsNotNone(projection)
        fields = re.findall(r'"([^"]+)"', projection.group(1))
        for field in ("itemsTotal", "curPage", "perPage"):
            self.assertIn(field, fields)
            self.assertNotIn(f"items.{field}", fields)
        self.assertIn('"items.id"', projection.group(0))
        self.assertIn('paging: {page: $input.page, per_page: $input.per_page, totals: true}', xs)
        self.assertIn("response = $requests_page", xs)
        self.assertEqual(xs.count("db.query "), 1)
        self.assertNotIn('type: "count"', xs)
        self.assertNotIn("|count", xs)
        self.assertIn("$scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id", xs)
        self.assertIn('sort = {data_criacao: "desc", id: "desc"}', xs)

    def test_profile_grants_are_module_scoped_and_selective(self):
        xs = source("xano/function/inventory/provision_purchase_profile.xs")
        for code in ("purchase_request.read", "purchase_request.manage", "purchase_request.status.update"):
            self.assertIn(code, xs)
        self.assertIn("PURCHASE_PROFILE_EXTRA_GRANTS", xs)
        self.assertNotIn("db.add user", xs)
        self.assertNotIn("inventory_audit_log", xs)
        self.assertNotIn('code: "administrator"', xs)

    def test_read_only_scope_and_history_authorization(self):
        listing = source("xano/api/inventory_stock/purchase_requests_get.xs")
        detail = source("xano/api/inventory_stock/purchase_requests_by_id_get.xs")
        summary = source("xano/api/inventory_stock/purchase_requests_summary_get.xs")
        for xs in (listing, detail, summary):
            self.assertIn('permission_code: "purchase_request.read"', xs)
            self.assertIn("Inventory/purchase_request_notification_all_access", xs)
            self.assertIn("$auth.id", xs)
        self.assertIn("$scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id", listing)
        self.assertLess(detail.index("$scope.all_access || $request.solicitante_usuario_id == $auth.id"), detail.index("db.query purchase_request_history"))
        self.assertIn("$scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id", summary)

    def test_native_status_update_and_history_share_transaction(self):
        xs = source("xano/api/inventory_stock/purchase_requests_by_id_status_patch.xs")
        self.assertIn('permission_code: "purchase_request.status.update"', xs)
        txn = xs.split("db.transaction {", 1)[1].split("\n  response =", 1)[0]
        self.assertEqual(txn.count("db.edit purchase_request {"), 2)
        self.assertEqual(txn.count("db.add purchase_request_history {"), 1)
        self.assertLess(txn.index("db.edit purchase_request"), txn.index("db.add purchase_request_history"))
        self.assertIn('evento: $input.novo_status == "rejeitada" ? "rejeitada" : "status_alterado"', txn)
        self.assertIn("actor_user_id: $auth.id", txn)
        self.assertIn("dados: {status_anterior: $input.status_esperado, status_novo: $input.novo_status}", txn)
        self.assertLess(txn.index("db.add purchase_request_history"), txn.index("var.update $updated_request"))
        self.assertIn("INVALID_JUSTIFICATION", xs)
        for forbidden in ("db.direct_query", "WHERE id", "lock =", "isolation =", "inventory_stock", "inventory_movement", "inventory_audit_log", "email_delivery", "api.request", "try_catch", "throw {"):
            self.assertNotIn(forbidden, xs)

    def test_native_status_checks_exist_and_expected_state_before_any_write(self):
        xs = source("xano/api/inventory_stock/purchase_requests_by_id_status_patch.xs")
        first_write = xs.index("db.edit purchase_request")
        for check in (
            "precondition ($input.request_id > 0)",
            "precondition ($current_request != null)",
            "precondition ($current_request.status == $input.status_esperado)",
        ):
            self.assertLess(xs.index(check), first_write)
        self.assertIn('error = "PURCHASE_REQUEST_NOT_FOUND"', xs)
        self.assertIn('error = "PURCHASE_REQUEST_STATUS_CONFLICT"', xs)
        self.assertLess(xs.index('permission_code: "purchase_request.status.update"'), xs.index("db.get purchase_request"))
        self.assertNotIn('permission_code: "purchase_request.manage"', xs)
        response = xs.split("  response =", 1)[1]
        for forbidden in ("active_product_id", "chave_idempotencia", "email_destinatario"):
            self.assertNotIn(forbidden, response)

    def test_rejection_alone_releases_active_product_and_closes_request(self):
        xs = source("xano/api/inventory_stock/purchase_requests_by_id_status_patch.xs")
        rejected = xs.split('if ($input.novo_status == "rejeitada")', 1)[1].split("else {", 1)[0]
        regular = xs.split("else {", 1)[1].split("db.add purchase_request_history", 1)[0]
        self.assertIn("active_product_id: null", rejected)
        self.assertIn("data_encerramento: now", rejected)
        self.assertNotIn("active_product_id:", regular)
        self.assertNotIn("data_encerramento:", regular)
        self.assertIn('$input.justificativa != null && $input.justificativa != ""', xs)

    def test_only_approved_manual_transitions(self):
        self.assertEqual(STATUS_OPTIONS, {
            "aberta": [("em_analise", "Em análise")],
            "em_analise": [("aprovada", "Aprovada"), ("rejeitada", "Rejeitada")],
            "aprovada": [("em_compra", "Em compra")],
            "em_compra": [("aguardando_recebimento", "Aguardando recebimento")],
        })
        xs = source("xano/api/inventory_stock/purchase_requests_by_id_status_patch.xs")
        self.assertNotIn('$input.novo_status == "concluida"', xs)
        self.assertNotIn('$input.novo_status == "recebimento_parcial"', xs)

    def test_exclusive_route_and_existing_roles(self):
        app = source("Meu_projeto/Meu_projeto.py")
        layout = source("Meu_projeto/components/layout.py")
        self.assertIn('route="/compras"', app)
        self.assertIn('route="/compras/[request_id]"', app)
        self.assertIn('AuthState.inventory_profile_code == "compras"', layout)
        self.assertIn('"Dashboard", "/dashboard"', layout)
        self.assertEqual(AuthState._home_route(SimpleNamespace(inventory_profile_code="compras")), "/compras")
        self.assertEqual(AuthState._home_route(SimpleNamespace(inventory_profile_code="stockkeeper")), "/dashboard")
        self.assertEqual(AuthState._home_route(SimpleNamespace(inventory_profile_code="administrator")), "/dashboard")

    def test_frontend_blocks_parallel_writes_and_uses_server_confirmation(self):
        xs = source("Meu_projeto/pages/compras.py")
        self.assertIn("if self.status_busy or self.cancel_busy or self.needs_reconciliation", xs)
        self.assertIn("result[\"solicitacao\"]", xs)
        self.assertIn("self.needs_reconciliation = True", xs)
        self.assertIn("Atualizar solicitação", xs)
        self.assertIn("_invalidate_reads(token)", xs)
        self.assertIn("auth_client.cancel_purchase_request", xs)
        self.assertNotIn("enviar_email", xs)


class PurchaseManagementClientTests(unittest.IsolatedAsyncioTestCase):
    def test_history_page_count_and_navigation_only_change_history(self):
        state = self._state()
        state.current_page = 3
        for total, expected in ((0, 1), (1, 1), (20, 1), (21, 2), (40, 2), (41, 3)):
            state.history_total = total
            self.assertEqual(state.history_page_total, expected)
        state.history_total = 20
        self.assertIsNone(state.next_history_page())
        self.assertIsNone(state.previous_history_page())
        state.history_total = 21
        self.assertIsNotNone(state.next_history_page())
        self.assertEqual(state.history_page, 2)
        self.assertIsNone(state.next_history_page())
        self.assertIsNotNone(state.previous_history_page())
        self.assertEqual(state.history_page, 1)
        self.assertEqual(state.current_page, 3)
        self.assertEqual(state.request_id, 8)

    async def test_detail_history_real_totals_and_exact_request_parameters(self):
        client = XanoAuthClient()
        for page, items, total in ((1, [{"id": 1, "evento": "criada"}], 3), (2, [{"id": 2, "evento": "status_alterado"}], 3), (1, [], 0)):
            data = {"solicitacao": {"id": 8, "status": "aberta"}, "produto": {"id": 3},
                    "historico": {"items": items, "itemsTotal": total, "curPage": page, "perPage": 1}}
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as request:
                result = await client.get_purchase_request_detail("mock-token", 8, history_page=page, history_per_page=1)
            self.assertEqual(result["historico"]["itemsTotal"], total)
            request.assert_awaited_once_with("GET", "/purchase_requests/by_id/8", "mock-token",
                params={"history_page": page, "history_per_page": 1}, group_url=client.stock_group_url)

    async def test_detail_invalid_history_names_section_and_field_without_payload(self):
        client = XanoAuthClient()
        for field in ("itemsTotal", "curPage", "perPage"):
            data = {"solicitacao": {"id": 8, "status": "aberta"}, "produto": {"id": 3},
                    "historico": {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 20}}
            del data["historico"][field]
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)):
                with self.assertRaises(XanoServerError) as caught:
                    await client.get_purchase_request_detail("mock-token", 8)
            error = caught.exception
            self.assertEqual(error.contract_section, "historico")
            self.assertEqual(error.contract_field, field)
            self.assertEqual(error.contract_found_type, "missing")
            with self.assertLogs("Meu_projeto.pages.compras", level="WARNING") as logs:
                _log_detail_failure(error)
            self.assertIn("Purchase detail read failed", str(logs.output))
            self.assertIn("contract_section=historico", str(logs.output))
            self.assertNotIn("mock-token", str(logs.output))

    async def test_detail_route_id_loading_and_contract_failure_without_retry(self):
        for path in ("/compras/8", "/compras/8/"):
            with self.subTest(path=path):
                session_read_cache.clear()
                state = self._state()
                state.detail_busy = False
                error = XanoServerError("private-error", status_code=200, payload={"secret": "private-value"})
                error.contract_section = "historico"
                error.contract_field = "itemsTotal"
                with (
                    patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("mock-token", None))),
                    patch.object(PurchaseManagementState, "router", new_callable=PropertyMock, return_value=SimpleNamespace(url=SimpleNamespace(path=path))),
                    patch("Meu_projeto.pages.compras.auth_client.get_purchase_request_detail", new=AsyncMock(side_effect=error)) as request,
                    self.assertLogs("Meu_projeto.pages.compras", level="WARNING") as logs,
                ):
                    _ = [event async for event in state.load_detail()]
                request.assert_awaited_once_with("mock-token", 8, history_page=1, history_per_page=20)
                self.assertEqual(state.detail_state, "error")
                self.assertFalse(state.detail_busy)
                self.assertIn("interpretar os detalhes", state.detail_error)
                for secret in ("mock-token", "private-value", "private-error"):
                    self.assertNotIn(secret, str(logs.output))
        session_read_cache.clear()

    async def test_paginated_list_uses_real_total_independent_of_current_page_size(self):
        client = XanoAuthClient()
        pages = (
            {"items": [{"id": n, "status": "aberta"} for n in range(1, 7)],
             "itemsTotal": 8, "curPage": 1, "perPage": 6},
            {"items": [{"id": 7, "status": "aberta"}, {"id": 8, "status": "aberta"}],
             "itemsTotal": 8, "curPage": 2, "perPage": 6},
            {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 6},
        )
        for data in pages:
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as get:
                result = await client.list_purchase_requests("mock-token", page=data["curPage"], per_page=6)
            self.assertEqual(result["itemsTotal"], data["itemsTotal"])
            self.assertEqual(len(result["items"]), len(data["items"]))
            get.assert_awaited_once()

    @staticmethod
    def _state() -> PurchaseManagementState:
        state = object.__new__(PurchaseManagementState)
        state._init_bookkeeping()
        for key, value in {
            "request_id": 8,
            "request_data": {"id": "8", "status": "aberta"},
            "status_busy": False,
            "cancel_busy": False,
            "status_error": "",
            "status_message": "",
            "status_choice": "",
            "needs_reconciliation": False,
            "justification": "",
            "justification_mode": "",
            "justification_open": False,
            "history_page": 1,
            "can_cancel_requests": True,
            "detail_state": "ready",
        }.items():
            setattr(state, key, value)
        return state

    async def test_list_failure_is_diagnosed_once_without_payload_or_retry(self):
        errors = (
            XanoServerError("private-provider-text", status_code=500, payload={"token": "private-token"}),
            XanoServerError("private-provider-text", status_code=200),
            XanoConnectionError("private-provider-text"),
            XanoPermissionError("private-provider-text", status_code=403),
            XanoRequestError("Unavailable", "NOT_FOUND", 404, {}),
            XanoRateLimitError(20),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__, status=error.status_code):
                session_read_cache.clear()
                state = self._state()
                state.current_page = 1
                state.status_filter = "todos"
                state.list_busy = False
                state.rows = []
                state.total = 0
                with (
                    patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("mock-token", None))),
                    patch("Meu_projeto.pages.compras.auth_client.list_purchase_requests", new=AsyncMock(side_effect=error)) as request,
                    self.assertLogs("Meu_projeto.pages.compras", level="WARNING") as logs,
                ):
                    _ = [event async for event in state.load_list()]
                request.assert_awaited_once_with("mock-token", page=1, per_page=20, status=None)
                self.assertNotIn(state.list_state, {"ready", "empty"})
                self.assertFalse(state.list_busy)
                self.assertEqual(len(logs.output), 1)
                for secret in ("private-provider-text", "private-token", "mock-token"):
                    self.assertNotIn(secret, str(logs.output))
                    self.assertNotIn(secret, state.list_error)
        session_read_cache.clear()

    async def test_auth_failure_logs_out_without_retry(self):
        session_read_cache.clear()
        state = self._state()
        state.list_busy = False
        auth = SimpleNamespace(logout=lambda: "logout-event")
        with (
            patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("mock-token", None))),
            patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)),
            patch("Meu_projeto.pages.compras.auth_client.list_purchase_requests", new=AsyncMock(side_effect=XanoAuthError("expired", status_code=401))) as request,
            self.assertLogs("Meu_projeto.pages.compras", level="WARNING"),
        ):
            events = [event async for event in state.load_list()]
        self.assertIn("logout-event", events)
        request.assert_awaited_once()

    def test_pagination_diagnostics_name_exact_field_without_values(self):
        valid = {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 20}
        self.assertEqual(XanoAuthClient._purchase_page(valid, page=1, per_page=20), valid)
        for field in ("itemsTotal", "curPage", "perPage"):
            for missing in (False, True):
                data = dict(valid)
                if missing:
                    data.pop(field)
                else:
                    data[field] = None
                with self.assertRaises(XanoServerError) as caught:
                    XanoAuthClient._purchase_page(data, page=1, per_page=20)
                error = caught.exception
                self.assertEqual(error.status_code, 200)
                self.assertEqual(error.contract_field, field)
                self.assertEqual(error.contract_found_type, "missing" if missing else "NoneType")
                with self.assertLogs("Meu_projeto.pages.compras", level="WARNING") as logs:
                    _log_list_failure(error)
                self.assertIn("origin=response_contract", str(logs.output))
                self.assertIn(f"contract_field={field}", str(logs.output))

    def test_total_is_only_rendered_after_successful_list_load(self):
        page = source("Meu_projeto/pages/compras.py")
        self.assertIn('rx.cond((PurchaseManagementState.list_state == "ready") | (PurchaseManagementState.list_state == "empty"), rx.hstack(', page)

    async def test_management_page_accepts_admin_and_effective_grants_not_profile_name(self):
        cases = (
            ("administrator", set(), True),
            ("compras", {"purchase_request.read", "purchase_request.manage"}, True),
            ("stockkeeper", {"purchase_request.read", "purchase_request.manage"}, True),
            ("read_only", {"purchase_request.read"}, True),
            ("stockkeeper", {"purchase_request.manage"}, False),
        )
        for profile, grants, allowed in cases:
            with self.subTest(profile=profile, grants=grants):
                state = self._state()
                auth = SimpleNamespace(
                    require_auth=AsyncMock(return_value=None), session_is_valid=True,
                    auth_token="mock-token", permission_codes=sorted(grants),
                    inventory_profile_code=profile,
                    has_permission=lambda code: profile == "administrator" or code in grants,
                )
                with patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)):
                    token, redirect = await state._authorized()
                self.assertIsNone(redirect)
                self.assertEqual(bool(token), allowed)
                if allowed:
                    self.assertEqual(state.can_update_status, profile == "administrator")

    async def test_detail_accepts_own_read_scope_without_global_manage(self):
        cases = (
            ("administrator", set(), True),
            ("read_only", {"purchase_request.read"}, True),
            ("stockkeeper", {"purchase_request.manage"}, False),
        )
        for profile, grants, allowed in cases:
            with self.subTest(profile=profile, grants=grants):
                state = self._state()
                auth = SimpleNamespace(
                    require_auth=AsyncMock(return_value=None), session_is_valid=True,
                    auth_token="mock-token", permission_codes=sorted(grants),
                    inventory_profile_code=profile,
                    has_permission=lambda code: profile == "administrator" or code in grants,
                )
                with patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)):
                    token, redirect = await state._authorized(detail=True)
                self.assertIsNone(redirect)
                self.assertEqual(bool(token), allowed)

    async def test_route_guard_allows_authorized_leader_and_preserves_exclusive_profile(self):
        cases = (
            ("administrator", [], "/compras", None),
            ("administrator", [], "/compras/8", None),
            ("stockkeeper", ["purchase_request.read", "purchase_request.manage"], "/compras", None),
            ("read_only", ["purchase_request.read"], "/compras", None),
            ("read_only", ["purchase_request.read"], "/compras/8", None),
            ("read_only", [], "/compras/8", "/dashboard"),
            ("compras", ["purchase_request.read", "purchase_request.manage"], "/compras", None),
            ("compras", ["purchase_request.read", "purchase_request.manage"], "/dashboard", "/compras"),
            ("compras", ["purchase_request.read", "purchase_request.manage"], "/reposicao", "/compras"),
            ("compras", ["purchase_request.read", "purchase_request.manage"], "/produtos/8/editar", "/compras"),
        )
        for profile, grants, path, destination in cases:
            with self.subTest(profile=profile, path=path):
                auth = object.__new__(AuthState)
                auth._init_bookkeeping()
                auth.auth_token = "mock-token"
                auth.inventory_profile_code = profile
                auth.permission_codes = grants
                auth.session_validation = "valid"
                auth.is_authenticated = True
                auth.must_change_password = False
                with (
                    patch.object(AuthState, "restore_session", new=AsyncMock(return_value=True)),
                    patch.object(AuthState, "router", new_callable=PropertyMock,
                                 return_value=SimpleNamespace(url=SimpleNamespace(path=path))),
                ):
                    event = await auth.require_auth()
                if destination is None:
                    self.assertIsNone(event)
                else:
                    self.assertIsNotNone(event)
                    self.assertIn(destination, str(event))

    async def test_list_uses_existing_group_and_pagination(self):
        client = XanoAuthClient()
        data = {"items": [{"id": 8, "status": "aberta"}], "itemsTotal": 7, "curPage": 1, "perPage": 1}
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as request:
            self.assertEqual((await client.list_purchase_requests("token", page=1, per_page=1))["itemsTotal"], 7)
            self.assertEqual(request.await_args.args[:3], ("GET", "/purchase_requests", "token"))

    async def test_malformed_list_is_rejected(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"items": [], "itemsTotal": None, "curPage": 1, "perPage": 20})):
            with self.assertRaises(XanoServerError):
                await client.list_purchase_requests("token")

    async def test_detail_requires_real_history_page(self):
        client = XanoAuthClient()
        data = {"solicitacao": {"id": 8, "status": "aberta"}, "produto": {"id": 3}, "historico": {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 20}}
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)):
            self.assertEqual((await client.get_purchase_request_detail("token", 8))["historico"]["itemsTotal"], 0)
        data["historico"]["itemsTotal"] = None
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)):
            with self.assertRaises(XanoServerError):
                await client.get_purchase_request_detail("token", 8)

    async def test_status_patch_sends_expected_state_once(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"solicitacao": {"id": 8, "status": "rejeitada"}})) as request:
            await client.update_purchase_request_status("token", 8, status_esperado="em_analise", novo_status="rejeitada", justificativa="  Motivo  ")
            request.assert_awaited_once()
            self.assertEqual(request.await_args.kwargs["json_payload"], {"status_esperado": "em_analise", "novo_status": "rejeitada", "justificativa": "Motivo"})

    async def test_status_patch_rejects_unconfirmed_response(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"solicitacao": {"id": 8, "status": "aberta"}})):
            with self.assertRaises(XanoServerError):
                await client.update_purchase_request_status("token", 8, status_esperado="aberta", novo_status="em_analise")

    async def test_status_conflict_keeps_last_confirmed_value(self):
        state = self._state()
        auth = SimpleNamespace(has_permission=lambda code: code == "purchase_request.status.update")
        error = XanoRequestError("Conflito", "PURCHASE_REQUEST_STATUS_CONFLICT", 409, {})
        with patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)), \
             patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("token", None))), \
             patch("Meu_projeto.pages.compras.auth_client.update_purchase_request_status", new=AsyncMock(side_effect=error)) as request:
            async for _ in state._write_status("em_analise", None):
                pass
            request.assert_awaited_once()
        self.assertEqual(state.request_data["status"], "aberta")
        self.assertTrue(state.needs_reconciliation)
        self.assertFalse(state.status_busy)

    async def test_busy_status_does_not_issue_second_patch(self):
        state = self._state()
        state.status_busy = True
        with patch("Meu_projeto.pages.compras.auth_client.update_purchase_request_status", new=AsyncMock()) as request:
            async for _ in state.select_status("em_analise"):
                pass
            request.assert_not_awaited()

    async def test_status_permission_denial_never_sends_patch(self):
        state = self._state()
        auth = SimpleNamespace(has_permission=lambda _code: False)
        with patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)), \
             patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("token", None))), \
             patch("Meu_projeto.pages.compras.auth_client.update_purchase_request_status", new=AsyncMock()) as request:
            async for _ in state._write_status("em_analise", None):
                pass
            request.assert_not_awaited()
        self.assertEqual(state.request_data["status"], "aberta")

    async def test_cancel_requires_reason_before_patch(self):
        state = self._state()
        state.justification_mode = "cancelamento"
        with patch("Meu_projeto.pages.compras.auth_client.cancel_purchase_request", new=AsyncMock()) as request:
            async for _ in state.confirm_justification():
                pass
            request.assert_not_awaited()
        self.assertEqual(state.status_error, "Informe uma justificativa.")

    async def test_confirmed_cancel_uses_existing_patch_once(self):
        state = self._state()
        state.justification_mode = "cancelamento"
        state.justification = "  Compra não necessária  "
        auth = SimpleNamespace(has_permission=lambda code: code == "purchase_request.manage")

        async def loaded(_self, _force):
            if False:
                yield None

        with patch.object(PurchaseManagementState, "get_state", new=AsyncMock(return_value=auth)), \
             patch.object(PurchaseManagementState, "_authorized", new=AsyncMock(return_value=("token", None))), \
             patch.object(PurchaseManagementState, "load_detail", new=loaded), \
             patch("Meu_projeto.pages.compras.auth_client.cancel_purchase_request", new=AsyncMock(return_value={"solicitacao": {"id": 8, "status": "cancelada"}})) as request:
            async for _ in state.confirm_justification():
                pass
            request.assert_awaited_once_with("token", 8, "Compra não necessária")
        self.assertEqual(state.status_message, "Solicitação cancelada com sucesso.")


if __name__ == "__main__":
    unittest.main()
