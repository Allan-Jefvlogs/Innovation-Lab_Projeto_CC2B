"""Local-only tests for the Replenishment interface; no Xano calls are made."""

from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from Meu_projeto.Meu_projeto import app
from Meu_projeto.pages import reposicao as replenishment_module
from Meu_projeto.pages.dashboard import DashboardState
from Meu_projeto.pages.reposicao import (
    ReplenishmentState,
    URGENCY_OPTIONS,
    _request_form,
    reposicao,
    suggested_purchase_quantity,
)
from Meu_projeto.services.session_read_cache import CACHE_MISS, session_read_cache
from Meu_projeto.services.xano_client import (
    XanoAuthClient,
    XanoAuthError,
    XanoConnectionError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestError,
    XanoRequestCoordinator,
    XanoServerError,
)


def _state() -> ReplenishmentState:
    state = object.__new__(ReplenishmentState)
    state._init_bookkeeping()
    for name, value in {
        "requestable_status": "loading",
        "requested_status": "loading",
        "error_message": "",
        "active_tab": "to_request",
        "data_stale": False,
        "retry_available": False,
        "retry_after_epoch": 0.0,
        "load_attempted": False,
        "is_loading": False,
        "requestable_products": [],
        "requested_products": [],
        "requestable_page": 1,
        "requested_page": 1,
        "page_size": 10,
        "requestable_total": 0,
        "requested_total": 0,
        "can_create_request": False,
        "can_cancel_requests": False,
        "integration_available": False,
        "request_form_open": False,
        "request_product_id": "",
        "request_product_code": "",
        "request_product_name": "",
        "request_product_unit": "",
        "request_quantity": "",
        "request_urgency": "Normal",
        "request_recipient_email": "",
        "request_email_contract_enabled": False,
        "request_create_error": "",
        "request_success_message": "",
        "request_submission_in_progress": False,
        "request_attempt_key": "",
        "request_attempt_signature": "",
        "request_attempt_ambiguous": False,
        "request_retry_after_epoch": 0.0,
        "cancel_form_open": False,
        "cancel_request_id": "",
        "cancel_product_label": "",
        "cancel_justification": "",
        "cancel_error_message": "",
        "cancel_success_message": "",
        "cancel_submission_in_progress": False,
        "cancel_attempt_ambiguous": False,
        "cancel_retry_after_epoch": 0.0,
        "session_fingerprint_cache": "",
    }.items():
        setattr(state, name, value)
    return state


def _auth_state(grants: set[str]):
    return SimpleNamespace(
        auth_token="local-test-session",
        session_is_valid=True,
        require_auth=AsyncMock(return_value=None),
        has_permission=lambda code: code in grants,
    )


async def _drain(event):
    return [item async for item in event]


def _response(requestable=None, requested=None, *, request_page=1, requested_page=1):
    return {
        "a_solicitar": {
            "items": requestable or [], "curPage": request_page, "perPage": 20,
            "itemsTotal": len(requestable or []),
        },
        "compra_ja_solicitada": {
            "items": requested or [], "curPage": requested_page, "perPage": 20,
            "itemsTotal": len(requested or []),
        },
    }


def _requestable_item(**overrides):
    return {
        "produto_id": 41,
        "codigo": "P-41",
        "nome": "Produto fracionável",
        "unidade_medida": "KG",
        "quantidade_disponivel": "1.25",
        "estoque_minimo": "2.5",
        "situacao_estoque": "abaixo_minimo",
        **overrides,
    }


def _requested_item(**overrides):
    return {
        **_requestable_item(),
        "solicitacao_id": 81,
        "quantidade_solicitada": "3.75",
        "urgencia": "Alta",
        "solicitacao_status": "aberta",
        "data_criacao_solicitacao": 1792411200000,
        **overrides,
    }


class ReplenishmentPageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()

    def tearDown(self):
        session_read_cache.clear()

    def test_route_and_two_tabs_are_registered(self):
        page = app._unevaluated_pages["reposicao"]
        self.assertEqual(page.route, "reposicao")
        self.assertIs(page.component, reposicao)
        source = inspect.getsource(replenishment_module.reposicao)
        self.assertIn('"A solicitar"', source)
        self.assertIn('"Compra já solicitada"', source)
        self.assertIn('"Reposição de Estoque"', source)
        self.assertIn(
            "Gerencie produtos com estoque insuficiente e acompanhe solicitações de compras.",
            source,
        )

    async def test_xano_client_sends_both_independent_pages_and_validates_metadata(self):
        client = XanoAuthClient()
        data = _response([_requestable_item()], [_requested_item()])
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=data) as request:
            result = await client.list_stock_replenishment(
                "token-placeholder", page=2, per_page=20, requested_page=3, requested_per_page=10
            )
        self.assertEqual(result, data)
        request.assert_awaited_once()
        args, kwargs = request.await_args
        self.assertEqual(args[:3], ("GET", "/stock/replenishment", "token-placeholder"))
        self.assertEqual(kwargs["params"], {
            "page": 2, "per_page": 20, "requested_page": 3, "requested_per_page": 10
        })

        invalid = _response()
        del invalid["a_solicitar"]["curPage"]
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=invalid):
            with self.assertRaises(XanoServerError) as caught:
                await client.list_stock_replenishment("token-placeholder")
        self.assertEqual(caught.exception.status_code, 200)
        self.assertEqual(caught.exception.contract_section, "a_solicitar")
        self.assertEqual(caught.exception.contract_field, "curPage")
        self.assertEqual(caught.exception.contract_expected, "integer")
        self.assertEqual(caught.exception.contract_found_type, "missing")

    async def test_replenishment_contract_diagnostics_identify_shape_without_values(self):
        client = XanoAuthClient()
        malformed_responses = (
            ({"data": _response()}, "a_solicitar", "$", "missing"),
            ({**_response(), "compra_ja_solicitada": None}, "compra_ja_solicitada", "$", "NoneType"),
            ({**_response(), "a_solicitar": {**_response()["a_solicitar"], "items": None}}, "a_solicitar", "items", "NoneType"),
            ({**_response(), "a_solicitar": {**_response()["a_solicitar"], "perPage": "20"}}, "a_solicitar", "perPage", "str"),
            ({**_response(), "a_solicitar": {**_response()["a_solicitar"], "items": ["private-row"]}}, "a_solicitar", "items[]", "str"),
        )
        for payload, expected_section, expected_field, found_type in malformed_responses:
            with self.subTest(section=expected_section, field=expected_field):
                with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=payload):
                    with self.assertRaises(XanoServerError) as caught:
                        await client.list_stock_replenishment("token-placeholder")
                error = caught.exception
                self.assertEqual(error.contract_section, expected_section)
                self.assertEqual(error.contract_field, expected_field)
                self.assertEqual(error.contract_found_type, found_type)
                self.assertNotIn("private-row", str(error))
                with self.assertLogs(replenishment_module.logger, level="WARNING") as logs:
                    replenishment_module._log_read_failure(error)
                self.assertIn(f"contract_section={expected_section}", logs.output[0])
                self.assertIn(f"contract_field={expected_field}", logs.output[0])
                self.assertNotIn("private-row", logs.output[0])

    async def test_replenishment_client_uses_stock_group_bearer_and_expected_paging(self):
        client = XanoAuthClient(base_url="https://workspace.example")
        response = httpx.Response(200, json=_response([_requestable_item()], []))
        with patch.object(client, "_send_request", new_callable=AsyncMock, return_value=response) as send:
            await client.list_stock_replenishment(
                "session-token-placeholder", page=2, per_page=10, requested_page=3, requested_per_page=5
            )

        args, kwargs = send.await_args
        self.assertEqual(args[:2], ("GET", "https://workspace.example/api:estoque/stock/replenishment"))
        self.assertEqual(kwargs["headers"], {"Authorization": "Bearer session-token-placeholder"})
        self.assertEqual(kwargs["auth_token"], "session-token-placeholder")
        self.assertEqual(kwargs["params"], {
            "page": 2, "per_page": 10, "requested_page": 3, "requested_per_page": 5
        })

    def test_lists_have_the_requested_columns_and_distinct_empty_states(self):
        source = inspect.getsource(replenishment_module)
        for column in (
            "Código",
            "Produto",
            "Estoque atual",
            "Estoque mínimo",
            "Situação",
            "Ação",
            "Quantidade solicitada",
            "Urgência",
            "Status da solicitação",
            "Data da solicitação",
        ):
            self.assertIn(column, source)
        self.assertIn('status == "unavailable"', source)
        self.assertIn('status == "empty"', source)
        self.assertIn('status == "error"', source)
        self.assertIn('status == "loading"', source)
        self.assertIn("Nenhum produto precisa de reposição.", source)
        self.assertIn('status == "unavailable"', source)

    def test_read_client_and_write_handlers_use_published_contracts(self):
        source = inspect.getsource(replenishment_module)
        self.assertIn("auth_client.list_stock_replenishment", source)
        self.assertIn("/stock/replenishment", source)
        self.assertIn("auth_client.create_purchase_request", source)
        self.assertIn("auth_client.cancel_purchase_request", source)

    async def test_page_load_maps_both_lists_and_independent_pagination_from_one_get(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        payload = _response(
            [_requestable_item()],
            [_requested_item()],
            request_page=1,
            requested_page=1,
        )
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=payload) as get_data,
            patch.object(replenishment_module, "_retry_delay_seconds", return_value=0),
        ):
            await _drain(state.load_page())

        auth.require_auth.assert_awaited_once()
        get_data.assert_awaited_once_with(
            "local-test-session", page=1, per_page=10, requested_page=1, requested_per_page=10
        )
        self.assertEqual(state.requestable_status, "ready")
        self.assertEqual(state.requested_status, "ready")
        self.assertTrue(state.can_create_request)
        self.assertTrue(state.integration_available)
        self.assertEqual(state.requestable_total, 1)
        self.assertEqual(state.requested_total, 1)
        self.assertEqual(state.requestable_products[0]["situacao_label"], "Abaixo do mínimo")
        self.assertEqual(state.requestable_products[0]["unidade"], "KG")
        self.assertEqual(state.requested_products[0]["quantidade_solicitada"], "3,75")
        self.assertEqual(state.requested_products[0]["urgencia"], "Alta")
        self.assertEqual(state.requested_products[0]["status"], "aberta")
        self.assertNotEqual(state.requested_products[0]["data_solicitacao"], "—")

    async def test_six_real_requestable_rows_and_empty_requested_page_use_one_get(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        products = [
            _requestable_item(produto_id=index, codigo=f"P-{index}")
            for index in range(1, 7)
        ]
        products[0].pop("unidade_medida")  # The view model treats unit as optional.
        payload = _response(products, [])
        # Total is global, not inferred from the six rows in this page.
        payload["a_solicitar"]["itemsTotal"] = 23
        payload["a_solicitar"]["perPage"] = 10
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                return_value=payload,
            ) as get_data,
        ):
            await _drain(state.load_page())

        get_data.assert_awaited_once_with(
            "local-test-session", page=1, per_page=10, requested_page=1, requested_per_page=10
        )
        self.assertEqual(state.requestable_total, 23)
        self.assertEqual(len(state.requestable_products), 6)
        self.assertEqual(state.requestable_page_total, 3)
        self.assertEqual(state.requestable_products[0]["unidade"], "")
        self.assertEqual(state.requested_total, 0)
        self.assertEqual(state.requested_status, "empty")

    async def test_tab_switch_is_local_and_does_not_repeat_get(self):
        session_read_cache.clear()
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=_response()) as get_data,
        ):
            await _drain(state.load_page())
            state.select_tab("requested")
            state.select_tab("to_request")
        self.assertEqual(get_data.await_count, 1)
        self.assertEqual(state.requestable_status, "empty")
        self.assertFalse(state.can_create_request)

    async def test_cache_isolated_by_session_and_revoked_grant_blocks_cached_data(self):
        payload = _response([_requestable_item()])
        first = _state()
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=payload) as get_data,
        ):
            await _drain(first.load_page())
            second = _state()
            other_user = _auth_state({"stock.read", "purchase_request.read"})
            other_user.auth_token = "different-local-test-session"
            with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=other_user):
                await _drain(second.load_page())
            self.assertEqual(get_data.await_count, 2)

            revoked = _state()
            no_purchase_read = _auth_state({"stock.read"})
            no_purchase_read.auth_token = "local-test-session"
            with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=no_purchase_read):
                await _drain(revoked.load_page())
            self.assertEqual(revoked.requestable_products, [])
            self.assertEqual(revoked.requestable_status, "access_denied")
            self.assertEqual(get_data.await_count, 2)

    async def test_403_clears_private_rows_and_does_not_show_empty_success(self):
        state = _state()
        state.requestable_products = [replenishment_module._map_item(_requestable_item(), requested=False)]
        state.requestable_total = 1
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, side_effect=XanoPermissionError("forbidden", status_code=403)),
        ):
            await _drain(state.load_page())
        self.assertEqual(state.requestable_status, "access_denied")
        self.assertEqual(state.requestable_products, [])
        self.assertFalse(state.retry_available)

    async def test_401_clears_rows_and_invalidates_the_session(self):
        state = _state()
        state.requestable_products = [replenishment_module._map_item(_requestable_item(), requested=False)]
        auth = _auth_state({"stock.read", "purchase_request.read"})
        auth.logout = lambda: "login-redirect"
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, side_effect=XanoAuthError("expired", status_code=401)),
        ):
            events = await _drain(state.load_page())
        self.assertEqual(state.requestable_products, [])
        self.assertEqual(state.requestable_status, "error")
        self.assertIn("login-redirect", events)

    async def test_second_load_uses_session_cache_and_missing_grant_makes_no_get(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=_response([_requestable_item()])) as get_data,
        ):
            await _drain(state.load_page())
            await _drain(state._load_data())
        self.assertEqual(get_data.await_count, 1)

        denied = _state()
        auth = _auth_state({"stock.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock) as denied_get,
        ):
            events = await _drain(denied.load_page())
        denied_get.assert_not_awaited()
        self.assertEqual(denied.requestable_status, "access_denied")
        self.assertTrue(any("dashboard" in repr(event) for event in events))

    async def test_empty_lists_are_distinct_from_api_errors(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=_response()),
        ):
            await _drain(state.load_page())
        self.assertEqual(state.requestable_status, "empty")
        self.assertEqual(state.requested_status, "empty")
        self.assertEqual(state.requestable_products, [])

        session_read_cache.clear()
        error_state = _state()
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, side_effect=XanoServerError("server error", status_code=500)),
        ):
            await _drain(error_state.load_page())
        self.assertEqual(error_state.requestable_status, "error")
        self.assertNotEqual(error_state.requestable_status, "empty")
        self.assertEqual(error_state.requestable_products, [])
        self.assertTrue(error_state.retry_available)

    async def test_429_keeps_only_same_session_cached_data_and_manual_retry_recovers(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        payload = _response([_requestable_item(situacao_estoque="sem_estoque")])
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=payload) as get_data,
        ):
            await _drain(state.load_page())
            session_read_cache.set(state._cache_key("local-test-session"), payload, 0.001)
            with patch.object(replenishment_module, "REPLENISHMENT_CACHE_TTL", 0.001):
                get_data.side_effect = XanoRateLimitError(5)
                await _drain(state.retry_session_or_data())
        self.assertEqual(get_data.await_count, 2)
        self.assertTrue(state.data_stale)
        self.assertTrue(state.can_create_request)
        self.assertEqual(state.requestable_status, "ready")
        self.assertTrue(state.data_stale)
        # A stale response can remain visible, but it cannot open a purchase draft.
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.open_request_form("41")
        self.assertFalse(state.request_form_open)

        session_read_cache.clear()
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, return_value=_response([_requestable_item(situacao_estoque="sem_estoque")])) as get_data,
        ):
            await _drain(state.load_page())
            await _drain(state.retry_session_or_data())
        self.assertEqual(get_data.await_count, 2)
        self.assertFalse(state.data_stale)
        self.assertEqual(state.requestable_status, "ready")
        self.assertEqual(state.requestable_products[0]["situacao_label"], "Sem estoque")

    async def test_reopening_after_429_does_not_retry_automatically(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                side_effect=XanoRateLimitError(5),
            ) as get_data,
        ):
            await _drain(state.load_page())
            await _drain(state.load_page())

        get_data.assert_awaited_once()
        self.assertEqual(state.requestable_status, "error")
        self.assertTrue(state.retry_available)
        self.assertFalse(state.data_stale)

    async def test_local_coordinator_429_is_distinguished_and_blocks_retry_until_cooldown(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                side_effect=XanoRateLimitError(5),
            ) as get_data,
            patch.object(replenishment_module.time, "time", return_value=100.0),
        ):
            await _drain(state.load_page())
            self.assertIn("Limite local", state.error_message)
            await _drain(state.retry_session_or_data())

        get_data.assert_awaited_once()
        self.assertEqual(state.retry_after_epoch, 105.0)
        self.assertIn("Aguarde", state.error_message)
        self.assertEqual(replenishment_module._read_error_origin(XanoRateLimitError(1)), "local_coordinator")

    async def test_invalid_success_payload_is_contract_error_not_empty_state(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        malformed = _response([_requestable_item()])
        del malformed["compra_ja_solicitada"]
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                return_value=malformed,
            ) as get_data,
        ):
            await _drain(state.load_page())

        get_data.assert_awaited_once()
        self.assertEqual(state.requestable_status, "error")
        self.assertEqual(state.requested_status, "error")
        self.assertIn("formato recebido é inesperado", state.error_message)
        self.assertTrue(state.retry_available)
        self.assertNotEqual(state.requestable_status, "empty")

    async def test_404_reports_endpoint_unavailable_and_keeps_manual_recovery(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                side_effect=XanoRequestError("not found", "NOT_FOUND", 404, {}),
            ),
        ):
            await _drain(state.load_page())

        self.assertEqual(state.requestable_status, "unavailable")
        self.assertTrue(state.retry_available)
        self.assertIn("não está disponível", state.error_message)

    def test_retry_control_is_small_and_only_shown_when_retry_is_available(self):
        retry_source = inspect.getsource(replenishment_module._retry_action)
        self.assertIn("ReplenishmentState.retry_available", retry_source)
        self.assertIn('size="1"', retry_source)
        self.assertIn('variant="ghost"', retry_source)
        self.assertNotIn('variant="soft"', retry_source)
        self.assertEqual(retry_source.count("Tentar novamente"), 1)

    async def test_manual_retry_obeys_remote_retry_after_then_recovers(self):
        state = _state()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        clock = {"now": 100.0}
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client,
                "list_stock_replenishment",
                new_callable=AsyncMock,
                side_effect=[
                    XanoRequestError("rate limited", "TOO_MANY_REQUESTS", 429, {}, retry_after="8"),
                    _response([_requestable_item()]),
                ],
            ) as get_data,
            patch.object(replenishment_module.time, "time", side_effect=lambda: clock["now"]),
        ):
            await _drain(state.load_page())
            self.assertEqual(state.retry_after_epoch, 108.0)
            await _drain(state.retry_session_or_data())
            get_data.assert_awaited_once()
            self.assertIn("8 segundo(s)", state.error_message)
            clock["now"] = 108.0
            await _drain(state.retry_session_or_data())

        self.assertEqual(get_data.await_count, 2)
        self.assertEqual(state.requestable_status, "ready")
        self.assertFalse(state.data_stale)

    async def test_pagination_changes_query_metadata_without_tab_get(self):
        state = _state()
        state.page_size = 1
        auth = _auth_state({"stock.read", "purchase_request.read"})
        first = _response([_requestable_item()], [_requested_item()], request_page=1, requested_page=1)
        first["a_solicitar"]["itemsTotal"] = 2
        first["compra_ja_solicitada"]["itemsTotal"] = 3
        first["a_solicitar"]["perPage"] = 1
        first["compra_ja_solicitada"]["perPage"] = 1
        second = _response([_requestable_item(produto_id=42)], [_requested_item(produto_id=82)], request_page=2, requested_page=1)
        second["a_solicitar"]["itemsTotal"] = 2
        second["compra_ja_solicitada"]["itemsTotal"] = 3
        second["a_solicitar"]["perPage"] = 1
        second["compra_ja_solicitada"]["perPage"] = 1
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "list_stock_replenishment", new_callable=AsyncMock, side_effect=[first, second]) as get_data,
        ):
            await _drain(state.load_page())
            state.select_tab("requested")
            await _drain(state.load_requestable_page(2))
        self.assertEqual(get_data.await_count, 2)
        get_data.assert_awaited_with(
            "local-test-session", page=2, per_page=1, requested_page=1, requested_per_page=1
        )
        self.assertEqual(state.requestable_page, 2)
        self.assertEqual(state.requestable_total, 2)
        self.assertEqual(state.requested_total, 3)

    async def test_missing_either_read_grant_blocks_page(self):
        for grants in (
            {"stock.read"},
            {"purchase_request.read"},
            set(),
        ):
            with self.subTest(grants=grants):
                state = _state()
                auth = _auth_state(grants)
                with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
                    events = await _drain(state.load_page())
                self.assertEqual(state.requestable_status, "access_denied")
                self.assertEqual(state.requested_status, "access_denied")
                self.assertFalse(state.can_create_request)
                self.assertTrue(any("dashboard" in repr(event) for event in events))

    def test_quantity_suggestion_supports_decimals_and_zero_minimum(self):
        self.assertEqual(suggested_purchase_quantity("1.25", "2.5"), "1.25")
        self.assertEqual(suggested_purchase_quantity("0", "0"), "1")
        self.assertEqual(suggested_purchase_quantity("4", "4"), "")
        self.assertEqual(suggested_purchase_quantity("-1", "2"), "")

    async def test_form_opens_only_with_authorized_backend_result_and_cancel_discards_draft(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.can_create_request = True
        state.requestable_products = [replenishment_module._map_item(_requestable_item(), requested=False)]
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.open_request_form(
                "41", "TEST-41", "Produto fracionável", "1.25", "2.5", "KG", "true", "true"
            )

        self.assertTrue(state.request_form_open)
        self.assertEqual(state.request_product_id, "41")
        self.assertEqual(state.request_quantity, "1.25")
        self.assertEqual(state.request_product_unit, "KG")
        self.assertEqual(state.request_urgency, "Normal")

        state.change_request_quantity("0.125")
        state.change_request_urgency("Crítica")
        state.cancel_request_form()
        self.assertFalse(state.request_form_open)
        self.assertEqual(state.request_product_id, "")
        self.assertEqual(state.request_quantity, "")
        self.assertEqual(state.request_urgency, "Normal")

    async def test_form_rejects_direct_invocation_without_grants_or_current_backend_data(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.open_request_form("41", "P-41", "Produto", "0", "0", "UN", "true", "true")
        self.assertFalse(state.request_form_open)

    async def test_form_rejects_inactive_product_missing_balance_and_sufficient_stock(self):
        cases = (
            ("0", "0", "false", "true"),
            ("0", "0", "true", "false"),
            ("3", "2", "true", "true"),
        )
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            for current, minimum, active, has_stock in cases:
                with self.subTest(current=current, minimum=minimum, active=active, has_stock=has_stock):
                    state = _state()
                    state.integration_available = True
                    state.requestable_status = "ready"
                    state.can_create_request = True
                    await state.open_request_form(
                        "41", "P-41", "Produto", current, minimum, "UN", active, has_stock
                    )
                    self.assertFalse(state.request_form_open)

        state = _state()
        state.integration_available = False
        state.requestable_status = "ready"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.open_request_form("41", "P-41", "Produto", "0", "0", "UN", "true", "true")
        self.assertFalse(state.request_form_open)

    def test_form_fields_connect_to_write_handlers_and_cancel_confirmation(self):
        source = inspect.getsource(_request_form)
        self.assertIn("read_only=True", source)
        self.assertIn('min="0.0000000001"', source)
        self.assertIn('step="any"', source)
        self.assertEqual(URGENCY_OPTIONS, ["Baixa", "Normal", "Alta", "Crítica"])
        self.assertIn("ReplenishmentState.submit_purchase_request", source)
        self.assertIn("request_submission_in_progress", source)
        self.assertIn("request_attempt_ambiguous", source)
        self.assertIn("cancel_request_form", source)
        self.assertIn("def _cancel_form", inspect.getsource(replenishment_module))
        self.assertIn("ReplenishmentState.confirm_cancel_request", inspect.getsource(replenishment_module))
        self.assertIn("Ação", inspect.getsource(replenishment_module._requested_content))

    async def test_write_client_uses_exact_published_post_and_patch_contracts(self):
        client = XanoAuthClient()
        created = {
            "solicitacao": {
                "id": 901,
                "produto_id": 41,
                "status": "aberta",
                "email_status": "pendente",
            },
            "repeticao_idempotente": False,
            "email_status": "pendente",
            "email_enviado": False,
        }
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=created) as request:
            result = await client.create_purchase_request(
                "token", produto_id=41, quantidade_solicitada="1.25",
                urgencia="critica", chave_idempotencia="attempt-key",
            )
        self.assertEqual(result, created)
        args, kwargs = request.await_args
        self.assertEqual(args[:3], ("POST", "/purchase_requests", "token"))
        self.assertEqual(kwargs["json_payload"], {
            "produto_id": 41,
            "quantidade_solicitada": 1.25,
            "urgencia": "critica",
            "chave_idempotencia": "attempt-key",
        })
        self.assertEqual(kwargs["group_url"], client.stock_group_url)

        cancelled = {"solicitacao": {"id": 901, "status": "cancelada"}, "justificativa": "Pedido duplicado"}
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=cancelled) as request:
            result = await client.cancel_purchase_request("token", 901, "  Pedido duplicado  ")
        args, kwargs = request.await_args
        self.assertEqual(result, cancelled)
        self.assertEqual(args[:3], ("PATCH", "/purchase_requests/by_id/901/cancel", "token"))
        self.assertEqual(kwargs["json_payload"], {"justificativa": "Pedido duplicado"})
        self.assertEqual(kwargs["group_url"], client.stock_group_url)

    async def test_write_client_rejects_unconfirmed_response_contracts(self):
        client = XanoAuthClient()
        malformed = {
            "solicitacao": {"id": 901, "produto_id": 41, "status": "aberta"},
            "repeticao_idempotente": False,
        }
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value=malformed):
            with self.assertRaises(XanoServerError):
                await client.create_purchase_request(
                    "token", produto_id=41, quantidade_solicitada="1", urgencia="normal",
                    chave_idempotencia="attempt-key",
                )

        with patch.object(
            client, "_inventory_request", new_callable=AsyncMock,
            return_value={"solicitacao": {"id": 901, "status": "aberta"}},
        ):
            with self.assertRaises(XanoServerError):
                await client.cancel_purchase_request("token", 901, "Motivo")

    async def test_write_http_domain_errors_keep_status_and_retry_after_without_retry(self):
        for status, code, headers in (
            (404, "PRODUCT_NOT_FOUND", {}),
            (409, "PURCHASE_REQUEST_ALREADY_ACTIVE", {}),
            (422, "INVALID_QUANTITY", {}),
            (429, "TOO_MANY_REQUESTS", {"Retry-After": "7"}),
        ):
            with self.subTest(status=status):
                client = XanoAuthClient(
                    "https://workspace.example",
                    coordinator=XanoRequestCoordinator(limit=7, window_seconds=20),
                )
                response = httpx.Response(status, json={"code": code, "message": "domain error"}, headers=headers)
                with (
                    patch.object(client, "_send_request", new_callable=AsyncMock, return_value=response) as send,
                    self.assertRaises(XanoRequestError) as caught,
                ):
                    await client.create_purchase_request(
                        "token", produto_id=41, quantidade_solicitada="1", urgencia="normal",
                        chave_idempotencia="attempt",
                    )
                self.assertEqual(caught.exception.status_code, status)
                self.assertEqual(caught.exception.error_code, code)
                self.assertEqual(caught.exception.retry_after, headers.get("Retry-After"))
                send.assert_awaited_once()

    async def test_create_validates_grant_quantity_and_urgency_before_post(self):
        for grants, quantity, urgency in (
            ({"stock.read", "purchase_request.read"}, "2", "normal"),
            ({"stock.read", "purchase_request.read", "purchase_request.create"}, "0", "normal"),
            ({"stock.read", "purchase_request.read", "purchase_request.create"}, "2", "unexpected"),
        ):
            with self.subTest(grants=grants, quantity=quantity, urgency=urgency):
                state = _state()
                state.integration_available = True
                state.requestable_status = "ready"
                state.request_product_id = "41"
                state.request_quantity = quantity
                state.request_urgency = urgency
                state.can_create_request = True
                auth = _auth_state(grants)
                with (
                    patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
                    patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock) as post,
                ):
                    await _drain(state.submit_purchase_request())
                post.assert_not_awaited()
                self.assertNotEqual(state.request_create_error, "")

    async def test_create_success_invalidates_purchase_reads_and_refreshes_both_lists(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_product_name = "Produto fracionável"
        state.request_quantity = "1,25"
        state.request_urgency = "Crítica"
        state.request_form_open = True
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        token = "local-test-session"
        endpoints = (
            replenishment_module.REPLENISHMENT_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_LIST_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_SUMMARY_ENDPOINT,
        )
        keys = [session_read_cache.key("scope", endpoint, token, {}) for endpoint in endpoints]
        for key in keys:
            session_read_cache.set(key, {"cached": True}, 60)

        async def refresh(force=False):
            state.requestable_products = [_map for _map in []]
            state.requested_products = [{"solicitacao_id": "901", "status": "aberta"}]
            if False:
                yield

        result = {
            "solicitacao": {"id": 901, "produto_id": 41, "status": "aberta", "email_status": "pendente"},
            "repeticao_idempotente": False,
            "email_status": "pendente",
            "email_enviado": False,
        }
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock, return_value=result) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=refresh) as reload,
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="attempt-1") as keygen,
        ):
            await _drain(state.submit_purchase_request())

        post.assert_awaited_once_with(
            token, produto_id=41, quantidade_solicitada="1.25", urgencia="critica",
            chave_idempotencia="attempt-1",
        )
        keygen.assert_called_once_with(32)
        reload.assert_called_once_with(True)
        self.assertEqual(state.requestable_products, [])
        self.assertEqual(state.requested_products[0]["solicitacao_id"], "901")
        self.assertFalse(state.request_form_open)
        self.assertIn("E-mail pendente", state.request_success_message)
        self.assertEqual(state.requestable_page, 1)
        self.assertEqual(state.requested_page, 1)
        for key in keys:
            self.assertIs(session_read_cache.get(key, 60)[0], CACHE_MISS)

    async def test_failed_create_does_not_invalidate_cache_or_refresh_lists(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "1"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        key = session_read_cache.key(
            "scope", replenishment_module.REPLENISHMENT_ENDPOINT, "local-test-session", {}
        )
        session_read_cache.set(key, {"cached": "valid"}, 60)
        async def no_refresh(force=False):
            if False:
                yield
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock,
                side_effect=XanoRequestError("already active", "PURCHASE_REQUEST_ALREADY_ACTIVE", 409, {}),
            ) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh) as reload,
        ):
            await _drain(state.submit_purchase_request())
        post.assert_awaited_once()
        reload.assert_not_called()
        self.assertEqual(session_read_cache.get(key, 60)[0], {"cached": "valid"})
        self.assertFalse(state.request_attempt_ambiguous)
        self.assertEqual(state.request_create_error, "already active")

    async def test_ambiguous_create_keeps_same_key_and_never_retries_automatically(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "2"
        state.request_urgency = "Normal"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        result = {
            "solicitacao": {"id": 902, "produto_id": 41, "status": "aberta", "email_status": "pendente"},
            "repeticao_idempotente": True,
            "email_status": "pendente",
            "email_enviado": False,
        }
        async def no_refresh(force=False):
            if False:
                yield

        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock,
                side_effect=[XanoConnectionError("timeout"), result],
            ) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="same-attempt"),
        ):
            await _drain(state.submit_purchase_request())
            self.assertTrue(state.request_attempt_ambiguous)
            self.assertEqual(post.await_count, 1)
            await _drain(state.submit_purchase_request())

        self.assertEqual(post.await_count, 2)
        self.assertEqual(post.await_args_list[0].kwargs["chave_idempotencia"], "same-attempt")
        self.assertEqual(post.await_args_list[1].kwargs["chave_idempotencia"], "same-attempt")
        self.assertFalse(state.request_attempt_ambiguous)

    async def test_remote_429_obeys_retry_after_and_reuses_the_attempt_key(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "2"
        state.request_urgency = "Normal"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        clock = {"now": 100.0}
        result = {
            "solicitacao": {"id": 904, "produto_id": 41, "status": "aberta", "email_status": "pendente"},
            "repeticao_idempotente": True,
            "email_status": "pendente",
            "email_enviado": False,
        }
        async def no_refresh(force=False):
            if False:
                yield
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock,
                side_effect=[
                    XanoRequestError("rate limited", "TOO_MANY_REQUESTS", 429, {}, retry_after="9"),
                    result,
                ],
            ) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module, "_retry_delay_seconds", return_value=9),
            patch.object(replenishment_module.time, "time", side_effect=lambda: clock["now"]),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="retry-key"),
        ):
            await _drain(state.submit_purchase_request())
            self.assertEqual(state.request_retry_after_epoch, 109.0)
            self.assertTrue(state.request_attempt_ambiguous)
            await _drain(state.submit_purchase_request())
            self.assertEqual(post.await_count, 1)
            clock["now"] = 109.0
            await _drain(state.submit_purchase_request())
        self.assertEqual(post.await_count, 2)
        self.assertEqual(post.await_args_list[0].kwargs["chave_idempotencia"], "retry-key")
        self.assertEqual(post.await_args_list[1].kwargs["chave_idempotencia"], "retry-key")

    async def test_write_401_logs_out_and_403_stays_scoped_to_request(self):
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        auth.logout = lambda: "login-redirect"
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "1"
        state.can_create_request = True
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock,
                side_effect=XanoAuthError("expired", status_code=401),
            ),
        ):
            events = await _drain(state.submit_purchase_request())
        self.assertIn("login-redirect", events)
        self.assertFalse(state.request_attempt_ambiguous)

        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "1"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                replenishment_module.auth_client, "create_purchase_request", new_callable=AsyncMock,
                side_effect=XanoPermissionError("forbidden", status_code=403),
            ) as post,
        ):
            await _drain(state.submit_purchase_request())
        post.assert_awaited_once()
        self.assertFalse(state.request_attempt_ambiguous)
        self.assertIn("permiss", state.request_create_error.lower())

    async def test_double_click_during_post_is_ignored(self):
        state = _state()
        state.integration_available = True
        state.requestable_status = "ready"
        state.request_product_id = "41"
        state.request_quantity = "2"
        state.request_urgency = "Normal"
        state.can_create_request = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.create"})
        started = __import__("asyncio").Event()
        release = __import__("asyncio").Event()
        result = {
            "solicitacao": {"id": 903, "produto_id": 41, "status": "aberta", "email_status": "pendente"},
            "repeticao_idempotente": False,
            "email_status": "pendente",
            "email_enviado": False,
        }
        async def slow_post(*args, **kwargs):
            started.set()
            await release.wait()
            return result
        async def no_refresh(force=False):
            if False:
                yield

        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "create_purchase_request", side_effect=slow_post) as post,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh),
            patch.object(replenishment_module.secrets, "token_urlsafe", return_value="one-key"),
        ):
            first = __import__("asyncio").create_task(_drain(state.submit_purchase_request()))
            await started.wait()
            await _drain(state.submit_purchase_request())
            self.assertEqual(post.await_count, 1)
            release.set()
            await first
        self.assertEqual(post.await_count, 1)

    async def test_cancel_requires_grant_reason_and_confirms_before_patch(self):
        state = _state()
        state.requested_products = [replenishment_module._map_item(
            _requested_item(solicitacao_id=81, solicitacao_status="aberta"), requested=True
        )]
        state.can_cancel_requests = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.cancel"})
        async def no_refresh(force=False):
            if False:
                yield
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "cancel_purchase_request", new_callable=AsyncMock) as patch_request,
            patch.object(ReplenishmentState, "_load_data", side_effect=no_refresh) as reload,
        ):
            await state.open_cancel_request_form("81")
            self.assertTrue(state.cancel_form_open)
            await _drain(state.confirm_cancel_request())
            patch_request.assert_not_awaited()
            self.assertIn("justificativa", state.cancel_error_message.lower())
            state.change_cancel_justification("Pedido não é mais necessário")
            await _drain(state.confirm_cancel_request())
            patch_request.assert_awaited_once_with(
                "local-test-session", 81, "Pedido não é mais necessário"
            )
            reload.assert_called_once_with(True)
        self.assertIn("cancelada", state.cancel_success_message)

    async def test_cancel_success_invalidates_reads_and_refreshes_without_stock_write(self):
        state = _state()
        state.requested_products = [replenishment_module._map_item(
            _requested_item(solicitacao_id=81, solicitacao_status="aberta"), requested=True
        )]
        state.can_cancel_requests = True
        state.cancel_request_id = "81"
        state.cancel_justification = "Pedido não é mais necessário"
        state.cancel_form_open = True
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.manage"})
        token = "local-test-session"
        endpoints = (
            replenishment_module.REPLENISHMENT_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_LIST_ENDPOINT,
            replenishment_module.PURCHASE_REQUEST_SUMMARY_ENDPOINT,
        )
        keys = [session_read_cache.key("scope", endpoint, token, {}) for endpoint in endpoints]
        for key in keys:
            session_read_cache.set(key, {"cached": True}, 60)
        async def refresh(force=False):
            state.requestable_products = [{"id": "41"}]
            state.requested_products = []
            if False:
                yield
        response = {"solicitacao": {"id": 81, "status": "cancelada"}}
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "cancel_purchase_request", new_callable=AsyncMock, return_value=response) as patch_request,
            patch.object(ReplenishmentState, "_load_data", side_effect=refresh) as reload,
        ):
            await _drain(state.confirm_cancel_request())
        patch_request.assert_awaited_once_with(token, 81, "Pedido não é mais necessário")
        reload.assert_called_once_with(True)
        self.assertEqual(state.requestable_products, [{"id": "41"}])
        self.assertEqual(state.requested_products, [])
        self.assertFalse(state.cancel_form_open)
        self.assertIn("estoque não foi alterado", state.cancel_success_message)
        for key in keys:
            self.assertIs(session_read_cache.get(key, 60)[0], CACHE_MISS)

    async def test_cancel_permission_denial_never_calls_patch(self):
        state = _state()
        state.requested_products = [replenishment_module._map_item(
            _requested_item(solicitacao_id=81, solicitacao_status="aberta"), requested=True
        )]
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with (
            patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(replenishment_module.auth_client, "cancel_purchase_request", new_callable=AsyncMock) as patch_request,
        ):
            await state.open_cancel_request_form("81")
            await _drain(state.confirm_cancel_request())
        patch_request.assert_not_awaited()
        self.assertFalse(state.cancel_form_open)

    async def test_cancel_only_offered_for_open_or_under_review(self):
        state = _state()
        state.requested_products = [
            replenishment_module._map_item(_requested_item(solicitacao_id=81, solicitacao_status="aberta"), requested=True),
            replenishment_module._map_item(_requested_item(solicitacao_id=82, solicitacao_status="em_compra"), requested=True),
        ]
        auth = _auth_state({"stock.read", "purchase_request.read", "purchase_request.cancel"})
        with patch.object(ReplenishmentState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.open_cancel_request_form("82")
        self.assertFalse(state.cancel_form_open)
        self.assertIn("status atual", state.cancel_error_message)


class DashboardReplenishmentNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_session_exposes_replenishment_only_with_both_read_grants(self):
        state = object.__new__(DashboardState)
        state._init_bookkeeping()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with patch.object(DashboardState, "get_state", new_callable=AsyncMock, return_value=auth):
            _token, grants = await state._session()
        self.assertTrue(grants["replenishment"])

        auth = _auth_state({"stock.read"})
        with patch.object(DashboardState, "get_state", new_callable=AsyncMock, return_value=auth):
            _token, grants = await state._session()
        self.assertFalse(grants["replenishment"])

    async def test_dashboard_requires_both_read_grants_for_navigation(self):
        state = object.__new__(DashboardState)
        state._init_bookkeeping()
        auth = _auth_state({"stock.read", "purchase_request.read"})
        with patch.object(DashboardState, "get_state", new_callable=AsyncMock, return_value=auth):
            result = await state.open_replenishment()
        self.assertIn("/reposicao", repr(result))

        auth = _auth_state({"stock.read"})
        with patch.object(DashboardState, "get_state", new_callable=AsyncMock, return_value=auth):
            result = await state.open_replenishment()
        self.assertIn("/dashboard", repr(result))

    def test_dashboard_card_keeps_stock_indicator_and_only_adds_guarded_navigation(self):
        dashboard_source = inspect.getsource(__import__("Meu_projeto.pages.dashboard", fromlist=["dashboard"]).dashboard)
        card_source = inspect.getsource(__import__("Meu_projeto.pages.dashboard", fromlist=["dashboard"])._metric_card)
        self.assertIn('"Abaixo do mínimo"', dashboard_source)
        self.assertIn("DashboardState.stock_value", dashboard_source)
        self.assertIn("DashboardState.stock_detail", dashboard_source)
        self.assertIn("DashboardState.open_replenishment", dashboard_source)
        self.assertIn("DashboardState.replenishment_accessible", dashboard_source)
        self.assertIn('"cursor": rx.cond(actionable, "pointer", "default")', card_source)
        self.assertIn('"on_click": on_click', card_source)
