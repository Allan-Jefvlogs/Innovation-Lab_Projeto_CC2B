"""Structural checks for local purchase-request XanoScript contracts.

These tests inspect source only. They do not execute XanoScript or prove
database, authorization, transaction, index, or concurrency behavior.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "xano" / "api" / "inventory_stock"


def source(name: str) -> str:
    return (API / name).read_text(encoding="utf-8")


def output_block(text: str, start: str) -> str:
    match = re.search(start + r"\s*=\s*\[(.*?)\]", text, flags=re.S)
    if not match:
        raise AssertionError(f"output allowlist not found for {start}")
    return match.group(1)


def braced_block_after(text: str, marker: str) -> str:
    """Return a source block using brace depth; this remains a static check."""
    marker_at = text.index(marker)
    opening = text.index("{", marker_at)
    depth = 0
    for position in range(opening, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : position]
    raise AssertionError(f"unclosed source block after {marker}")


class PurchaseRequestReadContractTests(unittest.TestCase):
    def test_list_has_required_page_filters_and_explicit_safe_projection(self):
        text = source("purchase_requests_get.xs")
        self.assertIn("int page?=1 filters=min:1", text)
        self.assertIn("int per_page?=20 filters=min:1|max:100", text)
        self.assertIn("$db.purchase_request.status ==? $input.status", text)
        self.assertIn("$db.purchase_request.produto_id ==? $input.produto_id", text)
        self.assertIn('"items.solicitante_usuario_id"', text)
        projected = output_block(text, "output")
        self.assertNotIn("chave_idempotencia", projected)
        self.assertNotIn("active_product_id", projected)

    def test_detail_and_history_use_allowlisted_response_fields(self):
        text = source("purchase_requests_by_id_get.xs")
        self.assertIn("history_page?=1", text)
        self.assertIn("history_per_page?=20 filters=min:1|max:100", text)
        self.assertIn("items.actor_user_id", output_block(text, "output"))
        self.assertIn("solicitante_usuario_id: $request.solicitante_usuario_id", text)
        self.assertNotIn("solicitacao: $request", text)
        self.assertNotIn("chave_idempotencia", text)
        self.assertNotIn("active_product_id", text)

    def test_summary_counts_only_active_business_statuses(self):
        text = source("purchase_requests_summary_get.xs")
        for status in (
            "aberta", "em_analise", "aprovada", "em_compra",
            "aguardando_recebimento", "recebimento_parcial",
        ):
            self.assertIn(f'== "{status}"', text)
        self.assertIn("response = {solicitacoes_abertas: $open_requests_count}", text)
        self.assertNotIn("email_status", text)

    def test_replenishment_requires_both_grants_and_separates_pages(self):
        text = source("stock_replenishment_get.xs")
        self.assertIn('permission_code: "stock.read"', text)
        self.assertIn('permission_code: "purchase_request.read"', text)
        self.assertIn("requested_page?=1", text)
        self.assertIn("requested_per_page?=20", text)
        self.assertIn("a_solicitar:", text)
        self.assertIn("compra_ja_solicitada:", text)

    def test_replenishment_response_explicitly_preserves_independent_paging_metadata(self):
        text = source("stock_replenishment_get.xs")
        response = text.split("  response = {", 1)[1]
        for section, page, per_page, total_source in (
            ("a_solicitar", "$input.page", "$input.per_page", "$eligible_page.itemsTotal"),
            (
                "compra_ja_solicitada",
                "$input.requested_page",
                "$input.requested_per_page",
                "$requested_page.itemsTotal",
            ),
        ):
            with self.subTest(section=section):
                section_text = response.split(f"{section}: {{", 1)[1].split("    },", 1)[0]
                self.assertIn("items:", section_text)
                self.assertIn(f"curPage: {page}", section_text)
                self.assertIn(f"perPage: {per_page}", section_text)
                self.assertIn(f"itemsTotal: {total_source}", section_text)
        self.assertNotIn('|set:"items"', response)
        # The totals come from the separately filtered, paginated DB queries.
        self.assertEqual(text.count("totals: true"), 2)
        self.assertEqual(text.count("db.query inventory_stock"), 2)
        for alias in ("eligible_page", "requested_page"):
            with self.subTest(query=alias):
                query = text.split(f"}} as ${alias}", 1)[0].rsplit(
                    "db.query inventory_stock", 1
                )[1]
                projection_match = re.search(r"output\s*=\s*\[(.*?)\]", query, re.S)
                self.assertIsNotNone(projection_match)
                self.assertIn('"itemsTotal"', projection_match.group(1))
                self.assertIn("totals: true", query)

    def test_replenishment_includes_zero_and_below_minimum_and_errors_on_missing_balance(self):
        text = source("stock_replenishment_get.xs")
        self.assertIn("$db.inventory_stock.quantidade_disponivel == 0", text)
        self.assertIn("$db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo", text)
        self.assertIn("$db.product.status == \"ativo\"", text)
        self.assertIn("$db.inventory_stock.id == null", text)
        self.assertIn('error = "STOCK_BALANCE_NOT_FOUND"', text)


    def test_replenishment_projects_active_request_fields_without_internal_controls(self):
        text = source("stock_replenishment_get.xs")
        requested_query = text.split("} as $requested_page", 1)[0].rsplit(
            "db.query inventory_stock", 1
        )[1]
        projection_match = re.search(r"output\s*=\s*\[(.*?)\]", requested_query, re.S)
        self.assertIsNotNone(projection_match)
        projection = projection_match.group(1)

        for field in (
            "items.product_id",
            "items.codigo",
            "items.nome",
            "items.quantidade_disponivel",
            "items.estoque_minimo",
            "items.solicitacao_id",
            "items.quantidade_solicitada",
            "items.urgencia_solicitacao",
            "items.solicitacao_status",
            "items.data_criacao_solicitacao",
        ):
            self.assertIn(f'"{field}"', projection)

        self.assertIn("solicitacao_id: $db.active_request.id", requested_query)
        self.assertIn(
            "quantidade_solicitada: $db.active_request.quantidade_solicitada",
            requested_query,
        )
        self.assertIn("urgencia_solicitacao: $db.active_request.urgencia", requested_query)
        self.assertIn("solicitacao_status: $db.active_request.status", requested_query)
        self.assertIn(
            "data_criacao_solicitacao: $db.active_request.data_criacao",
            requested_query,
        )
        self.assertNotIn("active_product_id", projection)
        self.assertNotIn("chave_idempotencia", projection)

    def test_replenishment_classifies_both_lists_and_keeps_reads_paged(self):
        text = source("stock_replenishment_get.xs")
        eligible_condition = '($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo))'
        self.assertEqual(text.count(eligible_condition), 2)
        self.assertEqual(text.count('value = "sem_estoque"'), 2)
        self.assertEqual(text.count('value = "abaixo_minimo"'), 2)
        self.assertEqual(text.count("return = {type: \"list\", paging:"), 2)
        self.assertEqual(text.count("db.query inventory_stock"), 2)
        self.assertEqual(text.count("db.query product"), 1)
        self.assertEqual(text.count('$db.product.status == "ativo" &&'), 3)
        self.assertIn("page: $input.page, per_page: $input.per_page", text)
        self.assertIn("page: $input.requested_page, per_page: $input.requested_per_page", text)
        self.assertIn("solicitacao_id: $item.solicitacao_id", text)
        self.assertEqual(text.count("situacao_estoque: $situacao_estoque"), 2)

    def test_requested_products_join_active_request_by_unique_candidate_key(self):
        text = source("stock_replenishment_get.xs")
        schema = (ROOT / "xano" / "table" / "purchase_request.xs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "where: $db.inventory_stock.product_id == $db.active_request.active_product_id",
            text,
        )
        for status in (
            "aberta", "em_analise", "aprovada", "em_compra",
            "aguardando_recebimento", "recebimento_parcial",
        ):
            self.assertEqual(text.count(f'$db.active_request.status == "{status}"'), 2)
        self.assertIn(
            '{type: "btree|unique", field: [{name: "active_product_id"}]}',
            schema,
        )


class PurchaseRequestCreateContractTests(unittest.TestCase):
    def test_create_uses_backend_authorization_and_validates_payload(self):
        text = source("purchase_requests_post.xs")
        self.assertIn('permission_code: "purchase_request.create"', text)
        self.assertIn("$input.quantidade_solicitada > 0", text)
        for urgency in ("baixa", "normal", "alta", "critica"):
            self.assertIn(f'$input.urgencia == "{urgency}"', text)
        self.assertIn('$product.status != "ativo"', text)
        for error_code in ("PRODUCT_NOT_FOUND", "PRODUCT_INACTIVE"):
            self.assertIn(f'value = "{error_code}"', text)
            self.assertIn(f'error = "{error_code}"', text)
        self.assertIn("$stock.quantidade_disponivel == 0", text)
        self.assertIn("$stock.quantidade_disponivel < $product.estoque_minimo", text)
        self.assertIn('value = "PRODUCT_STOCK_NOT_INSUFFICIENT"', text)
        self.assertIn('error = "PRODUCT_STOCK_NOT_INSUFFICIENT"', text)

    def test_idempotency_compares_actor_and_full_create_payload_without_returning_key(self):
        text = source("purchase_requests_post.xs")
        comparison = "$existing_idempotency.solicitante_usuario_id == $auth.id"
        for field in ("produto_id", "quantidade_solicitada", "urgencia"):
            comparison += f" && $existing_idempotency.{field} == $input.{field}"
        self.assertIn(comparison, text)
        self.assertIn('error = "IDEMPOTENCY_KEY_REUSED"', text)
        self.assertIn("value = $idempotency_after_conflict", text)
        self.assertIn('value = "PURCHASE_REQUEST_ALREADY_ACTIVE"', text)
        self.assertIn('error = "PURCHASE_REQUEST_ALREADY_ACTIVE"', text)
        self.assertIn("$active_after_conflict != null", text)
        self.assertNotIn("chave_idempotencia:", text.split("response =", 1)[-1])
        self.assertNotIn("active_product_id:", text.split("response =", 1)[-1])

    def test_schema_declares_candidate_unique_indexes(self):
        schema = (ROOT / "xano" / "table" / "purchase_request.xs").read_text(encoding="utf-8")
        self.assertIn("text chave_idempotencia", schema)
        self.assertIn("int? active_product_id?", schema)
        self.assertIn('{type: "btree|unique", field: [{name: "chave_idempotencia"}]}', schema)
        self.assertIn('{type: "btree|unique", field: [{name: "active_product_id"}]}', schema)

    def test_request_and_audit_event_share_transaction_and_stock_is_not_written(self):
        text = source("purchase_requests_post.xs")
        transaction = braced_block_after(text, "db.transaction")
        self.assertIn("db.add purchase_request", transaction)
        self.assertIn("db.add purchase_request_history", transaction)
        self.assertIn('evento: "criada"', transaction)
        self.assertIn('status: "aberta"', transaction)
        self.assertIn('var $initial_email_status { value = "pendente" }', transaction)
        self.assertIn('email_status: $initial_email_status', transaction)
        self.assertIn("solicitante_usuario_id: $auth.id", transaction)
        self.assertNotRegex(text, r"db\.(?:add|edit|patch) inventory_stock")
        self.assertNotIn("db.add inventory_movement", text)

    def test_all_mutable_eligibility_reads_are_inside_transaction_before_writes(self):
        text = source("purchase_requests_post.xs")
        transaction = braced_block_after(text, "db.transaction")
        first_write = transaction.index("db.add purchase_request {")
        for operation in (
            'field_name = "chave_idempotencia"',
            'db.get product {',
            'db.get inventory_stock {',
            'field_name = "active_product_id"',
        ):
            self.assertIn(operation, transaction[:first_write])
        self.assertGreater(
            transaction.index("db.add purchase_request_history"), first_write
        )
        self.assertLess(
            text.index("db.transaction {"),
            text.index("db.get product {"),
            "product eligibility must be re-read within the transaction",
        )

    def test_input_codes_and_backend_identity_are_explicit(self):
        text = source("purchase_requests_post.xs")
        input_block = braced_block_after(text, "input")
        self.assertIn("int produto_id", input_block)
        self.assertIn("decimal quantidade_solicitada", input_block)
        self.assertIn('text urgencia?="normal"', input_block)
        self.assertIn("text chave_idempotencia filters=trim", input_block)
        self.assertNotIn("solicitante_usuario_id", input_block)
        self.assertIn('input = {user_id: $auth.id, permission_code: "purchase_request.create"}', text)
        for code in (
            "INVALID_INPUT",
            "INVALID_QUANTITY",
            "INVALID_URGENCY",
            "PRODUCT_NOT_FOUND",
            "PRODUCT_INACTIVE",
            "STOCK_BALANCE_NOT_FOUND",
            "STOCK_BALANCE_INVALID",
            "PRODUCT_STOCK_NOT_INSUFFICIENT",
            "PURCHASE_REQUEST_ALREADY_ACTIVE",
            "IDEMPOTENCY_KEY_REUSED",
            "PURCHASE_REQUEST_CREATE_FAILED",
        ):
            with self.subTest(code=code):
                self.assertIn(f'"{code}"', text)
        self.assertIn("solicitante_usuario_id: $auth.id", text)
        self.assertIn("actor_user_id: $auth.id", text)

    def test_idempotency_is_checked_inside_transaction_and_collision_is_re_read(self):
        text = source("purchase_requests_post.xs")
        transaction = braced_block_after(text, "db.transaction")
        self.assertIn("idempotency_in_transaction", transaction)
        for payload_field in (
            "solicitante_usuario_id",
            "produto_id",
            "quantidade_solicitada",
            "urgencia",
        ):
            self.assertIn(f"$idempotency_in_transaction.{payload_field}", transaction)
        self.assertIn("idempotency_after_conflict", text)
        self.assertIn("active_after_conflict", text)
        self.assertIn("value = true", text)
        self.assertNotIn("$error.message", text)

    def test_duplicate_barriers_remain_candidate_indexes_and_runtime_is_unclaimed(self):
        text = source("purchase_requests_post.xs")
        schema = (ROOT / "xano" / "table" / "purchase_request.xs").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '{type: "btree|unique", field: [{name: "chave_idempotencia"}]}',
            schema,
        )
        self.assertIn(
            '{type: "btree|unique", field: [{name: "active_product_id"}]}',
            schema,
        )
        # Source checks only show the intended final barriers and recovery path.
        # They do not establish that the indexes exist or serialize races remotely.
        self.assertIn("db.add purchase_request", text)
        self.assertIn("PURCHASE_REQUEST_ALREADY_ACTIVE", text)
        self.assertNotRegex(text, r"db\.transaction\s*\{\s*isolation\s*=")

    def test_history_failure_path_is_atomic_by_structure_only(self):
        text = source("purchase_requests_post.xs")
        transaction = braced_block_after(text, "db.transaction")
        try_catch = braced_block_after(text, "try_catch")
        try_body = braced_block_after(try_catch, "try")
        catch_body = braced_block_after(try_catch, "catch")
        self.assertLess(
            transaction.index("db.add purchase_request {"),
            transaction.index("db.add purchase_request_history {"),
        )
        self.assertNotIn("throw {", transaction)
        self.assertIn("db.transaction {", try_body)
        self.assertNotIn("catch {", transaction)
        self.assertIn('value = "PURCHASE_REQUEST_CREATE_FAILED"', catch_body)
        self.assertLess(try_body.index("db.transaction {"), len(try_body))
        self.assertNotIn("db.add purchase_request_history", catch_body)
        # Structural checks cannot inject a database failure or prove remote rollback.
        self.assertIn('"PURCHASE_REQUEST_CREATE_FAILED"', text)

    def test_post_uses_preconditions_instead_of_throw_name_assignments(self):
        text = source("purchase_requests_post.xs")
        self.assertNotIn("throw {", text)
        self.assertNotRegex(text, r"(?m)^\s*name\s*=")
        for error_code in (
            "PRODUCT_NOT_FOUND", "PRODUCT_INACTIVE", "STOCK_BALANCE_NOT_FOUND",
            "STOCK_BALANCE_INVALID", "PRODUCT_STOCK_NOT_INSUFFICIENT",
            "PURCHASE_REQUEST_ALREADY_ACTIVE", "IDEMPOTENCY_KEY_REUSED",
            "PURCHASE_REQUEST_CREATE_FAILED",
        ):
            with self.subTest(code=error_code):
                self.assertIn(f'error = "{error_code}"', text)


class PurchaseRequestCancelContractTests(unittest.TestCase):
    def test_cancel_authenticates_uses_dynamic_grants_and_server_identity(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        transaction = braced_block_after(text, "db.transaction")
        self.assertIn('query "purchase_requests/by_id/{request_id}/cancel" verb=PATCH', text)
        self.assertIn('auth = "user"', text)
        self.assertIn('permission_code: "purchase_request.cancel"', text)
        self.assertIn('alternate_permission_code: "purchase_request.manage"', text)
        self.assertIn('permission_code: "purchase_request.manage"', text)
        self.assertIn("$request_for_authorization.solicitante_usuario_id != $auth.id", text)
        self.assertNotIn("solicitante_usuario_id != $auth.id", transaction)
        self.assertIn("actor_user_id: $auth.id", text)
        self.assertNotIn("actor_user_id: $input", text)

    def test_cancel_validates_reason_and_only_allows_open_states(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        transaction = braced_block_after(text, "db.transaction")
        self.assertIn("text justificativa filters=trim", text)
        self.assertIn('$input.justificativa != ""', text)
        self.assertIn('error = "INVALID_JUSTIFICATION"', text)
        self.assertIn('$request_in_transaction.status == "cancelada"', transaction)
        for status in ("aberta", "em_analise"):
            self.assertIn(f'$request_in_transaction.status != "{status}"', transaction)
        for status in (
            "aprovada", "em_compra", "aguardando_recebimento",
            "recebimento_parcial", "concluida", "rejeitada",
        ):
            self.assertNotIn(f'$request_in_transaction.status != "{status}"', transaction)
        self.assertIn('error = "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE"', text)
        self.assertIn('error = "PURCHASE_REQUEST_ALREADY_CANCELLED"', text)

    def test_cancel_rechecks_request_in_transaction_and_records_release_and_audit(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        transaction = braced_block_after(text, "db.transaction")
        reread = transaction.index("as $request_in_transaction")
        status_guard = transaction.index('$request_in_transaction.status != "aberta"')
        update = transaction.index("db.edit purchase_request {")
        history = transaction.index("db.add purchase_request_history {")
        self.assertLess(reread, status_guard)
        self.assertLess(status_guard, update)
        self.assertLess(update, history)
        self.assertIn('status: "cancelada"', transaction)
        self.assertIn("active_product_id: null", transaction)
        self.assertIn("data_encerramento: now", transaction)
        self.assertIn("data_atualizacao: now", transaction)
        self.assertIn('evento: "cancelada"', transaction)
        self.assertIn("justificativa: $input.justificativa", transaction)
        self.assertIn("actor_user_id: $auth.id", transaction)
        self.assertIn("status_anterior: $request_in_transaction.status", transaction)
        self.assertIn('status_novo: "cancelada"', transaction)
        self.assertNotRegex(text, r"db\.(?:add|edit|patch) inventory_stock")
        self.assertNotIn("db.add inventory_movement", text)

    def test_cancel_errors_and_response_omit_internal_fields(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        for error_code in (
            "INVALID_REQUEST_ID",
            "INVALID_JUSTIFICATION",
            "PURCHASE_REQUEST_NOT_FOUND",
            "PURCHASE_REQUEST_ALREADY_CANCELLED",
            "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE",
            "PURCHASE_REQUEST_CANCEL_CONFLICT",
            "PURCHASE_REQUEST_CANCEL_FAILED",
        ):
            with self.subTest(code=error_code):
                self.assertIn(f'"{error_code}"', text)
        response = text.split("response =", 1)[-1]
        self.assertNotIn("active_product_id:", response)
        self.assertNotIn("chave_idempotencia:", response)

    def test_single_row_edit_and_transaction_do_not_prove_concurrent_safety(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        transaction = braced_block_after(text, "db.transaction")
        self.assertIn('field_name = "id"', transaction)
        self.assertIn("db.edit purchase_request", transaction)
        self.assertNotRegex(transaction, r"(?m)^\s*db\.bulk\.update\b")
        self.assertNotIn('isolation = "serializable"', transaction)
        self.assertLess(
            transaction.index("db.edit purchase_request"),
            transaction.index("db.add purchase_request_history"),
        )

    def test_cancel_uses_import_compatible_preconditions_not_throw_name_assignment(self):
        text = source("purchase_requests_by_id_cancel_patch.xs")
        self.assertNotIn("throw {", text)
        self.assertNotRegex(text, r"(?m)^\s*name\s*=")
        for error_code in (
            "PURCHASE_REQUEST_NOT_FOUND",
            "PURCHASE_REQUEST_ALREADY_CANCELLED",
            "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE",
            "PURCHASE_REQUEST_CANCEL_CONFLICT",
            "PURCHASE_REQUEST_CANCEL_FAILED",
        ):
            with self.subTest(code=error_code):
                self.assertIn(f'error = "{error_code}"', text)


if __name__ == "__main__":
    unittest.main()
