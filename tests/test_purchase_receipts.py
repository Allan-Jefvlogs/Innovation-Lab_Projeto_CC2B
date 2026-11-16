"""Tests locais e simulações sequenciais: não executam XanoScript ou banco remoto."""

import copy
import inspect
import unittest
import httpx
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages.movimentacoes import EntryState
from Meu_projeto.services.purchase_receipts import receipt_preview
from Meu_projeto.services.session_read_cache import CACHE_MISS, session_read_cache
from Meu_projeto.services.xano_client import XanoAuthClient, XanoConnectionError, XanoRequestError, XanoServerError

ROOT = Path(__file__).resolve().parents[1]


def order(**changes):
    return {"id": 8, "produto_id": 3, "quantidade_solicitada": 15,
            "quantidade_recebida": 0, "status": "aguardando_recebimento",
            "unidade_medida_solicitada": "KG", **changes}


class ReceiptPreviewTests(unittest.TestCase):
    def test_zero_received_is_valid_but_null_is_not_a_receipt_balance(self):
        for received in (0, Decimal("0")):
            with self.subTest(received=received):
                result = receipt_preview(order(quantidade_solicitada=10, quantidade_recebida=received), 3, 4)
                self.assertEqual(result["acumulado"], "4")
                self.assertEqual(result["status"], "recebimento_parcial")
        with self.assertRaises(ValueError):
            receipt_preview(order(quantidade_solicitada=10, quantidade_recebida=None), 3, 4)

    def test_partial_total_successive_fractional(self):
        data = order(quantidade_solicitada="1.5")
        for quantity, accumulated, status in (("0.2", "0.2", "recebimento_parcial"),
                                             ("0.3", "0.5", "recebimento_parcial"),
                                             ("1", "1.5", "concluida")):
            result = receipt_preview(data, 3, quantity)
            self.assertEqual(Decimal(result["acumulado"]), Decimal(accumulated))
            self.assertEqual(result["status"], status)
            data.update(quantidade_recebida=result["acumulado"], status=status)

    def test_excess_invalid_values_wrong_product_terminal_and_legacy(self):
        cases = [(order(), 3, 16), (order(), 4, 1), (order(), 3, 0),
                 (order(), 3, -1), (order(), 3, "NaN"), (order(), 3, "Infinity"),
                 (order(unidade_medida_solicitada=None), 3, 1),
                 (order(quantidade_recebida=None), 3, 1)]
        cases += [(order(status=s), 3, 1) for s in ("aberta", "aprovada", "concluida", "cancelada", "rejeitada")]
        for data, product, quantity in cases:
            with self.subTest(data=data, product=product, quantity=quantity):
                with self.assertRaises(ValueError):
                    receipt_preview(data, product, quantity)


class ReceiptScriptStructureTests(unittest.TestCase):
    def test_receipt_balance_uses_strict_null_check_and_keeps_numeric_limits(self):
        # Contract assertion only: this does not execute the Xano expression.
        xs = (ROOT / "xano/api/inventory_stock/entries_post.xs").read_text(encoding="utf-8")
        guard = "precondition ($request.quantidade_recebida !== null && $request.quantidade_recebida >= 0 && $request.quantidade_solicitada > 0 && $request.quantidade_recebida < $request.quantidade_solicitada)"
        self.assertIn(guard, xs)
        self.assertLess(xs.index(guard), xs.index("db.edit inventory_stock"))
        self.assertIn("precondition ($accumulated <= $request.quantidade_solicitada)", xs)

    def test_additive_nullable_schema_and_final_unique_protection(self):
        movement = (ROOT / "xano/table/inventory_movement.xs").read_text(encoding="utf-8")
        request = (ROOT / "xano/table/purchase_request.xs").read_text(encoding="utf-8")
        self.assertIn('int? purchase_request_id?', movement)
        self.assertIn('table = "purchase_request"', movement)
        self.assertIn('text? unidade_medida?', movement)
        self.assertIn('text? chave_recebimento?', movement)
        self.assertIn('{type: "btree|unique", field: [{name: "chave_recebimento"}]}', movement)
        self.assertIn('text? unidade_medida_solicitada?', request)
        self.assertIn('{type: "btree|unique", field: [{name: "active_product_id"}]}', request)
        self.assertIn('decimal quantidade_recebida? filters=min:0', request)
        self.assertIn('text? email_destinatario? filters=trim {\n      visibility = "internal"', request)

    def test_native_transaction_order_and_no_partial_commit_catch(self):
        xs = (ROOT / "xano/api/inventory_stock/entries_post.xs").read_text(encoding="utf-8")
        txn = xs.split("db.transaction {", 1)[1].split("var $receipt_response", 1)[0]
        writes = ("db.edit inventory_stock", "db.add inventory_movement", "db.edit purchase_request", "db.add purchase_request_history")
        positions = [txn.index(value) for value in writes]
        self.assertEqual(positions, sorted(positions))
        for forbidden in ("catch", "throw", "db.direct_query", "api.request", "inventory_audit_log", "dispatch_purchase_request_email"):
            self.assertNotIn(forbidden, xs)
        self.assertIn('permission_code: "stock.entry"', xs)
        self.assertIn('permission_code: "purchase_request.read"', xs)
        self.assertIn("$global_access || $request.solicitante_usuario_id == $auth.id", txn)
        self.assertIn('$request.status == "aguardando_recebimento" || $request.status == "recebimento_parcial"', txn)
        self.assertIn("$request.produto_id == $input.product_id", txn)
        self.assertIn("$product.unidade_medida == $input.unidade_medida", txn)
        self.assertLess(txn.index("RECEIPT_UNIT_UNCONFIRMED"), positions[0])
        self.assertLess(txn.index("RECEIPT_EXCEEDS_REMAINING"), positions[0])
        self.assertIn('evento: "recebimento_registrado"', txn)
        self.assertIn("movement_id: $movement.id", txn)
        self.assertIn('var.update $active_product_id { value = null }', txn)

    def test_missing_stock_update_cannot_reach_movement_or_report_success(self):
        xs = (ROOT / "xano/api/inventory_stock/entries_post.xs").read_text(encoding="utf-8")
        edit = xs.index("db.edit inventory_stock")
        missing = xs.index("if ($updated_stock == null)", edit)
        failure_flag = xs.index("var.update $stock_update_missing { value = true }", missing)
        successful_branch = xs.index("else {", failure_flag)
        movement = xs.index("db.add inventory_movement", successful_branch)
        post_transaction_guard = xs.index("precondition (!$stock_update_missing)", movement)
        self.assertLess(edit, missing)
        self.assertLess(failure_flag, successful_branch)
        self.assertLess(successful_branch, movement)
        self.assertLess(movement, post_transaction_guard)
        self.assertIn('error = "STOCK_BALANCE_NOT_FOUND"', xs[post_transaction_guard:])
        self.assertLess(post_transaction_guard, xs.index("response = {"))

    def test_replay_precedes_terminal_status_and_does_not_write(self):
        xs = (ROOT / "xano/api/inventory_stock/entries_post.xs").read_text(encoding="utf-8")
        replay = xs.split("if ($existing_movement != null)", 1)[1].split("else {", 1)[0]
        self.assertNotIn("db.edit", replay)
        self.assertNotIn("db.add", replay)
        for field in ("purchase_request_id", "product_id", "user_id", "quantidade", "unidade_medida", "supplier_id", "motivo", "observacao", "data_hora"):
            self.assertIn(f"$existing_movement.{field}", replay)
        self.assertLess(xs.index("RECEIPT_IDEMPOTENCY_CONFLICT"), xs.index("RECEIPT_STATUS_INVALID"))
        self.assertIn('var $saldo_anterior { value = null }', xs)
        self.assertIn('var $saldo_atual { value = null }', xs)

    def test_new_orders_snapshot_unit_and_gets_expose_it_without_backfill(self):
        post = (ROOT / "xano/api/inventory_stock/purchase_requests_post.xs").read_text(encoding="utf-8")
        self.assertIn("unidade_medida_solicitada: $product.unidade_medida", post)
        self.assertNotIn("db.edit purchase_request {", post)
        for name in ("purchase_requests_get.xs", "purchase_requests_by_id_get.xs"):
            self.assertIn("unidade_medida_solicitada", (ROOT / "xano/api/inventory_stock" / name).read_text(encoding="utf-8"))


class SequentialXanoFake:
    """Double de contrato, não prova transação, unicidade ou rollback do Xano."""

    def __init__(self):
        self.request = order()
        self.stock = Decimal("0")
        self.movements = {}
        self.history = []
        self.fail_history = False

    async def __call__(self, method, path, token, **kwargs):
        assert (method, path) == ("POST", "/entries")
        data = kwargs["json_payload"]
        key = data.get("chave_recebimento")
        if key in self.movements:
            prior, result = self.movements[key]
            if prior != data:
                raise XanoRequestError("conflict", "RECEIPT_IDEMPOTENCY_CONFLICT", 400, {})
            return {**result, "repeticao": True, "saldo_atual": None, "saldo_anterior": None,
                    "recebimento": copy.deepcopy(self.request)}
        snapshot = copy.deepcopy((self.request, self.stock, self.movements, self.history))
        try:
            preview = receipt_preview(self.request, data["product_id"], data["quantidade"]) if key else None
            self.stock += Decimal(str(data["quantidade"]))
            if preview:
                self.request.update(quantidade_recebida=preview["acumulado"], status=preview["status"])
                if self.fail_history:
                    raise XanoServerError("simulated history failure", status_code=500)
                self.history.append({"evento": "recebimento_registrado"})
            result = {"movement_id": len(self.movements) + 1, "purchase_request_id": data.get("purchase_request_id"),
                      "repeticao": False, "saldo_atual": str(self.stock),
                      "recebimento": copy.deepcopy(self.request) if key else None}
            self.movements[key or str(result["movement_id"])] = (copy.deepcopy(data), result)
            return result
        except Exception:
            self.request, self.stock, self.movements, self.history = snapshot
            raise


class ReceiptClientAndStateTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        session_read_cache.clear()

    async def test_mocked_partial_total_successive_and_duplicate_do_not_double_count(self):
        client, fake = XanoAuthClient(), SequentialXanoFake()
        with patch.object(client, "_inventory_request", side_effect=fake.__call__):
            for quantity, key, expected in ((5, "a", "recebimento_parcial"), (4, "b", "recebimento_parcial"), (6, "c", "concluida")):
                args = dict(product_id=3, quantidade=quantity, motivo="Compra", purchase_request_id=8,
                            chave_recebimento=key, unidade_medida="KG")
                result = await client.create_stock_entry("test-token", **args)
                self.assertEqual(result["recebimento"]["status"], expected)
                repeated = await client.create_stock_entry("test-token", **args)
                self.assertTrue(repeated["repeticao"])
            self.assertEqual(fake.stock, Decimal("15"))
            self.assertEqual(len(fake.movements), 3)
            self.assertEqual(len(fake.history), 3)
            recovered = await client.create_stock_entry("test-token", product_id=3, quantidade=5, motivo="Compra",
                                                         purchase_request_id=8, chave_recebimento="a", unidade_medida="KG")
            self.assertEqual(recovered["recebimento"]["status"], "concluida")
            self.assertIsNone(recovered["saldo_atual"])
            self.assertEqual(fake.stock, Decimal("15"))
            with self.assertRaises(XanoRequestError):
                await client.create_stock_entry("test-token", **{**args, "quantidade": 7})

    async def test_mocked_excess_history_failure_and_unlinked_compatibility(self):
        client, fake = XanoAuthClient(), SequentialXanoFake()
        with patch.object(client, "_inventory_request", side_effect=fake.__call__):
            args = dict(product_id=3, quantidade=16, motivo="Compra", purchase_request_id=8, chave_recebimento="a", unidade_medida="KG")
            with self.assertRaises(ValueError):
                await client.create_stock_entry("test-token", **args)
            self.assertEqual(fake.stock, 0)
            fake.fail_history = True
            with self.assertRaises(XanoServerError):
                await client.create_stock_entry("test-token", **{**args, "quantidade": 1})
            self.assertEqual(fake.stock, 0)
            self.assertFalse(fake.movements)
            await client.create_stock_entry("test-token", product_id=3, quantidade=20, motivo="Avulsa")
            self.assertEqual(fake.stock, 20)
            self.assertEqual(fake.request["quantidade_recebida"], 0)
            self.assertFalse(fake.history)

    async def test_client_does_not_add_link_fields_to_legacy_entries(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"movement_id": 1})) as send:
            await client.create_stock_entry("test-token", product_id=3, quantidade=1, motivo=" Compra ")
        self.assertEqual(send.await_args.kwargs["json_payload"], {"product_id": 3, "quantidade": 1, "motivo": "Compra"})

    async def test_client_rejects_ambiguous_linked_response_instead_of_confirming_success(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"movement_id": 1})) as send:
            with self.assertRaises(XanoServerError):
                await client.create_stock_entry("test-token", product_id=3, quantidade=1, motivo="Compra",
                                                purchase_request_id=8, chave_recebimento="a", unidade_medida="KG")
        send.assert_awaited_once()

    async def test_client_rejects_orphan_key_without_http(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock()) as send:
            with self.assertRaises(ValueError):
                await client.create_stock_entry("test-token", product_id=3, quantidade=1, motivo="Avulsa", chave_recebimento="a")
        send.assert_not_awaited()

    def state(self):
        state = object.__new__(EntryState)
        state._init_bookkeeping()
        state.receipts_enabled = True
        state.product_id = "3"
        state.quantidade = "5"
        state.motivo = "Compra"
        state.receipt_order_id = "8"
        state._receipt_orders_raw = [order()]
        return state

    def auth(self):
        return SimpleNamespace(auth_token="test-token", session_is_valid=True, is_authenticated=True,
                               has_permission=lambda code: code in {"stock.entry", "purchase_request.read"})

    async def test_ambiguous_response_keeps_same_key_payload_no_automatic_retry(self):
        state = self.state()
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new=AsyncMock(side_effect=XanoConnectionError("timeout"))
        ) as send:
            _ = [event async for event in state.register_entry()]
            self.assertEqual(send.await_count, 1)
            key = state._receipt_key
            payload = dict(state._receipt_payload)
            self.assertTrue(state.receipt_needs_recovery)
            self.assertTrue(key)
            _ = [event async for event in state.register_entry()]
            self.assertEqual(send.await_count, 1)
            _ = [event async for event in state.recover_receipt()]
            self.assertEqual(send.await_count, 2)
            self.assertEqual(send.await_args.kwargs, payload)
            self.assertEqual(state._receipt_key, key)

    async def test_first_http_400_balance_error_is_definitive_and_never_retries(self):
        state = self.state()
        response = httpx.Response(400, json={"code": "ERROR_CODE_INPUT_ERROR", "message": "RECEIPT_BALANCE_INVALID", "payload": ""})
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client._send_request", new=AsyncMock(return_value=response)
        ) as send:
            _ = [event async for event in state.register_entry()]
        send.assert_awaited_once()
        self.assertIn("quantidades inconsistentes", state.error_message)
        self.assertFalse(state.receipt_needs_recovery)
        self.assertFalse(state._receipt_key)
        self.assertFalse(state._receipt_payload)

    async def test_balance_error_during_recovery_preserves_previous_ambiguous_attempt(self):
        state = self.state()
        response = httpx.Response(400, json={"code": "ERROR_CODE_INPUT_ERROR", "message": "RECEIPT_BALANCE_INVALID", "payload": ""})
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client._send_request",
            new=AsyncMock(side_effect=[httpx.ConnectTimeout("timeout"), response]),
        ) as send:
            _ = [event async for event in state.register_entry()]
            key = state._receipt_key
            payload = dict(state._receipt_payload)
            self.assertTrue(state.receipt_needs_recovery)
            _ = [event async for event in state.recover_receipt()]
            self.assertTrue(state.receipt_requires_reconciliation)
            self.assertEqual(state._receipt_key, key)
            self.assertEqual(state._receipt_payload, payload)
            _ = [event async for event in state.recover_receipt()]
        self.assertEqual(send.await_count, 2)

    async def test_success_invalidates_reads_and_clear_attempt_only_after_confirmation(self):
        state = self.state()
        token = "test-token"
        key = session_read_cache.key("test", "GET /purchase_requests/summary", token, {})
        session_read_cache.set(key, {"solicitacoes_abertas": 1}, 20)
        result = {"movement_id": 9, "saldo_atual": 5, "recebimento": {"status": "recebimento_parcial"}}
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new=AsyncMock(return_value=result)
        ) as send:
            _ = [event async for event in state.register_entry()]
        send.assert_awaited_once()
        self.assertFalse(state._receipt_key)
        self.assertFalse(state.receipt_needs_recovery)
        self.assertIs(session_read_cache.get(key, 20)[0], CACHE_MISS)

    async def test_legacy_order_or_missing_read_permission_never_sends_entry_as_linked(self):
        for legacy in (True, False):
            state = self.state()
            if legacy:
                state._receipt_orders_raw = [order(unidade_medida_solicitada=None)]
            auth = self.auth()
            if not legacy:
                auth.has_permission = lambda code: code == "stock.entry"
            with patch.object(EntryState, "get_state", new=AsyncMock(return_value=auth)), patch(
                "Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new=AsyncMock()
            ) as send:
                _ = [event async for event in state.register_entry()]
            send.assert_not_awaited()

    async def test_no_query_on_mount_or_when_feature_disabled_and_no_polling(self):
        state = self.state()
        state.receipts_enabled = False
        with patch("Meu_projeto.pages.movimentacoes.auth_client.list_purchase_requests", new=AsyncMock()) as get:
            _ = [event async for event in state.load_receipt_orders()]
        get.assert_not_awaited()
        self.assertNotIn("list_purchase_requests", inspect.getsource(EntryState.load_entry_data.fn))

    async def test_order_query_is_explicit_paged_cached_and_does_not_select_automatically(self):
        session_read_cache.clear()
        state = self.state()
        state.receipt_order_id = "none"
        data = {"items": [order(), order(id=9, status="cancelada")], "itemsTotal": 22, "curPage": 1, "perPage": 20}
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client.list_purchase_requests", new=AsyncMock(return_value=data)
        ) as get:
            _ = [event async for event in state.load_receipt_orders()]
            _ = [event async for event in state.load_receipt_orders()]
        get.assert_awaited_once_with("test-token", produto_id=3, page=1, per_page=20)
        self.assertEqual([r["id"] for r in state.receipt_orders], ["8"])
        self.assertEqual(state.receipt_order_id, "none")
        self.assertTrue(state.receipt_has_more)
        state.select_receipt_order("8")
        self.assertIn("Restante: 15 KG", state.receipt_info)
        state.change_barcode("OUTRO")
        self.assertEqual(state.receipt_order_id, "none")

    async def test_recovery_does_not_reuse_attempt_in_another_session(self):
        state = self.state()
        state.receipt_needs_recovery = True
        state._receipt_payload = {"product_id": 3}
        state._receipt_owner = session_read_cache.session_fingerprint("different-session")
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new=AsyncMock()
        ) as send:
            _ = [event async for event in state.recover_receipt()]
        send.assert_not_awaited()

    async def test_busy_entry_does_not_issue_another_post(self):
        state = self.state()
        state.is_submitting = True
        with patch("Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new=AsyncMock()) as send:
            _ = [event async for event in state.register_entry()]
        send.assert_not_awaited()

    async def test_unknown_success_contract_requires_read_reconciliation_not_another_post(self):
        state = self.state()
        with patch.object(EntryState, "get_state", new=AsyncMock(return_value=self.auth())), patch(
            "Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry",
            new=AsyncMock(side_effect=XanoServerError("invalid receipt contract", status_code=200)),
        ) as send:
            _ = [event async for event in state.register_entry()]
            key = state._receipt_key
            self.assertTrue(state.receipt_requires_reconciliation)
            _ = [event async for event in state.recover_receipt()]
        send.assert_awaited_once()
        self.assertEqual(key, state._receipt_key)


if __name__ == "__main__":
    unittest.main()
