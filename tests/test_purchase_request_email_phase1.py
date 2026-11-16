"""Local contract tests for the purchase-request recipient-email phase."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages import reposicao as replenishment_module
from Meu_projeto.pages.reposicao import ReplenishmentState
from Meu_projeto.services.session_read_cache import CACHE_MISS, session_read_cache
from Meu_projeto.services.xano_client import (
    XanoAuthClient,
    XanoConnectionError,
    normalize_purchase_request_email,
)


def _state(*, contract_enabled: bool, email: str = "") -> ReplenishmentState:
    state = object.__new__(ReplenishmentState)
    values = {
        "request_submission_in_progress": False,
        "session_fingerprint_cache": "",
        "data_stale": False,
        "integration_available": True,
        "can_create_request": True,
        "request_product_id": "41",
        "request_product_code": "P41",
        "request_product_name": "Parafuso",
        "request_product_unit": "un",
        "request_quantity": "2.5",
        "request_urgency": "Alta",
        "request_recipient_email": email,
        "request_email_contract_enabled": contract_enabled,
        "request_attempt_key": "",
        "request_attempt_signature": "",
        "request_attempt_ambiguous": False,
        "request_retry_after_epoch": 0.0,
        "request_create_error": "",
        "request_success_message": "",
        "request_form_open": True,
        "requestable_page": 1,
        "requested_page": 1,
    }
    state._init_bookkeeping()
    for name, value in values.items():
        setattr(state, name, value)
    return state


def _auth():
    class Auth:
        auth_token = "test-session"
        session_is_valid = True

        async def require_auth(self):
            return None

        def has_permission(self, code: str) -> bool:
            return code == "purchase_request.create"

    return Auth()


async def _drain(event):
    return [item async for item in event]


class RecipientEmailValidationTests(unittest.TestCase):
    def test_email_is_trimmed_and_keeps_case(self):
        self.assertEqual(
            normalize_purchase_request_email("  Compras@Empresa.com.br  ", required=True),
            "Compras@Empresa.com.br",
        )

    def test_required_empty_and_invalid_addresses_are_rejected(self):
        for value in (
            None, "", "   ", "not-an-email", "a@b", "a@@empresa.com",
            "a@empresa..com", "a..b@empresa.com", "a@-empresa.com",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_purchase_request_email(value, required=True)

    def test_optional_empty_supports_legacy_contract_but_nonempty_invalid_fails(self):
        self.assertIsNone(normalize_purchase_request_email(None, required=False))
        self.assertIsNone(normalize_purchase_request_email("  ", required=False))
        with self.assertRaises(ValueError):
            normalize_purchase_request_email("broken", required=False)

    def test_address_length_limits_are_enforced(self):
        too_long = f"{'a' * 65}@example.com"
        with self.assertRaises(ValueError):
            normalize_purchase_request_email(too_long, required=True)
        with self.assertRaises(ValueError):
            normalize_purchase_request_email(f"{'a' * 246}@x.com", required=True)


class RecipientEmailClientTests(unittest.IsolatedAsyncioTestCase):
    def _response(self):
        return {
            "solicitacao": {
                "id": 55,
                "produto_id": 41,
                "status": "aberta",
                "email_status": "pendente",
            },
            "repeticao_idempotente": False,
            "email_status": "pendente",
            "email_enviado": False,
        }

    async def test_legacy_payload_omits_recipient_field(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=self._response()) as request:
            await client.create_purchase_request(
                "token", produto_id=41, quantidade_solicitada="2.5", urgencia="alta",
                chave_idempotencia="legacy-key",
            )
        payload = request.await_args.kwargs["json_payload"]
        self.assertNotIn("email_destinatario", payload)

    async def test_new_payload_trims_recipient_and_rejects_invalid_before_http(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=self._response()) as request:
            await client.create_purchase_request(
                "token", produto_id=41, quantidade_solicitada="2.5", urgencia="alta",
                chave_idempotencia="new-key", email_destinatario=" compras@empresa.com.br ",
            )
            self.assertEqual(request.await_args.kwargs["json_payload"]["email_destinatario"], "compras@empresa.com.br")
            with self.assertRaises(ValueError):
                await client.create_purchase_request(
                    "token", produto_id=41, quantidade_solicitada="2.5", urgencia="alta",
                    chave_idempotencia="bad-key", email_destinatario="invalido",
                )
        self.assertEqual(request.await_count, 1)


class RecipientEmailUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_mode_keeps_old_post_shape_and_emails_filled_recipient(self):
        state = _state(contract_enabled=False)
        auth = _auth()
        async def no_refresh(force=False):
            if False:
                yield
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock, return_value=self._response()) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="legacy-key"),
            patch.object(replenishment_module, "enviar_email_solicitacao_compra", new_callable=AsyncMock, return_value=True) as send,
        ):
            await _drain(state.submit_purchase_request())
            post.assert_awaited_once_with(
                "test-session", produto_id=41, quantidade_solicitada="2.5",
                urgencia="alta", chave_idempotencia="legacy-key",
            )
            send.assert_not_awaited()

            state2 = _state(contract_enabled=False, email=" compras@empresa.com.br ")
            await _drain(state2.submit_purchase_request())
            self.assertEqual(post.await_count, 2)
            self.assertNotIn("email_destinatario", post.await_args.kwargs)
            self.assertEqual(state2.request_create_error, "")
            send.assert_awaited_once()
            self.assertEqual(send.await_args.kwargs["destinatario"], "compras@empresa.com.br")
            self.assertEqual(send.await_args.kwargs["solicitacao_id"], 55)
            self.assertIn("E-mail enviado para compras@empresa.com.br", state2.request_success_message)

    async def test_enabled_contract_requires_email_and_sends_normalized_value(self):
        auth = _auth()
        missing = _state(contract_enabled=True)
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock) as post,
        ):
            await _drain(missing.submit_purchase_request())
            self.assertIn("e-mail", missing.request_create_error)
            post.assert_not_awaited()

        state = _state(contract_enabled=True, email="  compras@empresa.com.br ")
        async def no_refresh(force=False):
            if False:
                yield
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock, side_effect=XanoConnectionError("offline")) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="email-attempt"),
        ):
            await _drain(state.submit_purchase_request())
        self.assertEqual(post.await_args.kwargs["email_destinatario"], "compras@empresa.com.br")
        self.assertIn("|compras@empresa.com.br", state.request_attempt_signature)
        self.assertTrue(state.request_attempt_ambiguous)

    async def test_enabled_contract_success_invalidates_reads_and_does_not_claim_failed_email_was_sent(self):
        state = _state(contract_enabled=True, email="compras@empresa.com.br")
        auth = _auth()
        endpoints = (
            replenishment_module.REPLENISHMENT_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_LIST_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_SUMMARY_ENDPOINT,
        )
        keys = [session_read_cache.key("test-scope", endpoint, "test-session", {}) for endpoint in endpoints]
        for key in keys:
            session_read_cache.set(key, {"cached": True}, 60)

        async def no_refresh(force=False):
            if False:
                yield

        result = self._response()
        result["solicitacao"]["email_status"] = "falhou"
        result["email_status"] = "falhou"
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock, return_value=result) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="email-success-key"),
            patch.object(replenishment_module, "enviar_email_solicitacao_compra", new_callable=AsyncMock, return_value=False),
        ):
            await _drain(state.submit_purchase_request())

        self.assertEqual(post.await_args.kwargs["email_destinatario"], "compras@empresa.com.br")
        self.assertIn("Não foi possível enviar o e-mail", state.request_success_message)
        self.assertNotIn("E-mail enviado", state.request_success_message)
        for key in keys:
            self.assertIs(session_read_cache.get(key, 60)[0], CACHE_MISS)

    def test_modal_has_recipient_field_and_explains_staged_delivery(self):
        source = inspect.getsource(replenishment_module._request_form)
        self.assertIn('"E-mail do destinatário"', source)
        self.assertIn('placeholder="exemplo@empresa.com.br"', source)
        self.assertIn('type="email"', source)
        self.assertIn("a solicitação será enviada por e-mail ao endereço informado", source)
        self.assertNotIn("Nenhum e-mail é enviado nesta fase", source)

    async def test_successful_cancel_emails_fixed_recipient_only_once(self):
        def cancel_state():
            state = object.__new__(ReplenishmentState)
            state._init_bookkeeping()
            for name, value in {
                "session_fingerprint_cache": "",
                "cancel_submission_in_progress": False,
                "cancel_request_id": "6",
                "cancel_justification": " Pedido duplicado ",
                "cancel_product_label": "P41 — Parafuso",
                "cancel_retry_after_epoch": 0.0,
                "cancel_attempt_ambiguous": False,
                "cancel_error_message": "",
                "cancel_success_message": "",
                "cancel_form_open": True,
                "requestable_page": 1,
                "requested_page": 1,
            }.items():
                setattr(state, name, value)
            return state

        auth = _auth()
        auth.has_permission = lambda code: code == "purchase_request.cancel"

        async def no_refresh(force=False):
            if False:
                yield

        state = cancel_state()
        cancelled = {"solicitacao": {"id": 6, "status": "cancelada"}}
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "cancel_purchase_request", new_callable=AsyncMock, return_value=cancelled),
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module, "enviar_email_cancelamento_compra", new_callable=AsyncMock, return_value=True) as send,
        ):
            await _drain(state.confirm_cancel_request())

        send.assert_awaited_once()
        self.assertEqual(send.await_args.kwargs["solicitacao_id"], 6)
        self.assertEqual(send.await_args.kwargs["justificativa"], "Pedido duplicado")
        self.assertIn("Aviso enviado para mateus.dotta@aluno.impacta.edu.br", state.cancel_success_message)

        already = cancel_state()
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "cancel_purchase_request", new_callable=AsyncMock,
                side_effect=replenishment_module.XanoRequestError(
                    "já cancelada", "PURCHASE_REQUEST_ALREADY_CANCELLED", 400, {}
                ),
            ),
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module, "enviar_email_cancelamento_compra", new_callable=AsyncMock) as send_again,
        ):
            await _drain(already.confirm_cancel_request())
        send_again.assert_not_awaited()
        self.assertIn("já estava cancelada", already.cancel_success_message)

    def _response(self):
        return {
            "solicitacao": {"id": 55, "produto_id": 41, "status": "aberta", "email_status": "pendente"},
            "repeticao_idempotente": False,
            "email_status": "pendente",
            "email_enviado": False,
        }


class RecipientEmailXanoContractTests(unittest.TestCase):
    def test_nullable_schema_and_post_contract_save_and_compare_recipient(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        schema = (root / "xano/table/purchase_request.xs").read_text(encoding="utf-8")
        post = (root / "xano/api/inventory_stock/purchase_requests_post.xs").read_text(encoding="utf-8")
        self.assertIn("text? email_destinatario?", schema)
        self.assertIn("email? email_destinatario? filters=trim", post)
        self.assertIn('$input.email_destinatario == null ||', post)
        self.assertIn('$input.email_destinatario != ""', post)
        self.assertIn('($input.email_destinatario|strlen) <= 254', post)
        self.assertIn("INVALID_RECIPIENT_EMAIL", post)
        self.assertIn("email_destinatario: $input.email_destinatario", post)
        self.assertEqual(post.count("$existing_idempotency.email_destinatario == $input.email_destinatario"), 1)
        self.assertEqual(post.count("$idempotency_in_transaction.email_destinatario == $input.email_destinatario"), 1)
        self.assertEqual(post.count("$idempotency_after_conflict.email_destinatario == $input.email_destinatario"), 1)
        self.assertIn('var $initial_email_status { value = "pendente" }', post)
        self.assertIn('email_status: $initial_email_status', post)
        self.assertIn("email_enviado: false", post)
        self.assertNotIn('db.add inventory_stock', post)
        self.assertNotIn('db.add inventory_movement', post)

    def test_transitional_post_accepts_omitted_or_null_and_keeps_null_in_idempotency(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        post = (root / "xano/api/inventory_stock/purchase_requests_post.xs").read_text(encoding="utf-8")
        input_block = post.split("input {", 1)[1].split("  }", 1)[0]
        self.assertIn("email? email_destinatario? filters=trim", input_block)
        self.assertNotIn("$input.email_destinatario != null", input_block)
        self.assertEqual(post.count("email_destinatario == $input.email_destinatario"), 3)
        self.assertIn("email_destinatario: $input.email_destinatario", post)

    def test_cancel_keeps_destination_untouched_and_reads_do_not_expose_it(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        cancel = (root / "xano/api/inventory_stock/purchase_requests_by_id_cancel_patch.xs").read_text(encoding="utf-8")
        reads = [
            root / "xano/api/inventory_stock/purchase_requests_get.xs",
            root / "xano/api/inventory_stock/purchase_requests_by_id_get.xs",
            root / "xano/api/inventory_stock/stock_replenishment_get.xs",
        ]
        self.assertIn("$request_in_transaction.email_destinatario", cancel)
        self.assertNotIn("email_destinatario:", cancel)
        cancellation_response = cancel.split("response = {", 1)[1]
        self.assertNotIn("email_destinatario", cancellation_response)
        for path in reads:
            with self.subTest(path=path.name):
                self.assertNotIn("email_destinatario", path.read_text(encoding="utf-8"))
