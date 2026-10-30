"""Local HTTP integration coverage for AuthState session validation.

All requests use httpx.MockTransport and a non-resolving sentinel host. No
network connection to Xano is possible from these tests.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from Meu_projeto.services.xano_client import (
    AUTH_CANONICAL_GROUP,
    XanoAuthClient,
    XanoAuthError,
    XanoConnectionError,
    XanoRequestCoordinator,
    XanoServerError,
)
from Meu_projeto.pages.estoque import StockState
from Meu_projeto.state.auth import AuthState


MOCK_BASE_URL = "https://nexstock-test.invalid"
MOCK_TOKEN = "integration-test-token-not-real"


def _state() -> AuthState:
    """Build an isolated Reflex state without app or browser initialization."""
    state = object.__new__(AuthState)
    object.__setattr__(state, "dirty_vars", set())
    for name, value in {
        "auth_token": MOCK_TOKEN,
        "user_id": 7,
        "user_name": "Cached user",
        "user_email": "cached@example.invalid",
        "user_role": "stockkeeper",
        "inventory_profile_id": 2,
        "inventory_profile_code": "stockkeeper",
        "permission_codes": ["stock.exit"],
        "profile_name": "Almoxarife",
        "must_change_password": False,
        "password_change_notice": "",
        "is_authenticated": True,
        "is_loading": False,
        "error_message": "",
        "session_validation": "valid",
        "session_retry_after_epoch": 0.0,
    }.items():
        setattr(state, name, value)
    return state


def _user_payload(permission_codes: list[str]) -> dict[str, object]:
    return {
        "id": 7,
        "name": "Fresh test user",
        "email": "fresh@example.invalid",
        "role": "stockkeeper",
        "inventory_profile_id": 2,
        "inventory_profile_code": "stockkeeper",
        "permission_codes": permission_codes,
    }


def _transport_for(*outcomes):
    """Return a MockTransport and safe request metadata (never auth headers)."""
    observed: list[tuple[str, str, str, int | str]] = []
    remaining = list(outcomes)

    def handle(request: httpx.Request) -> httpx.Response:
        if not remaining:
            raise AssertionError("Unexpected extra HTTP request")

        outcome = remaining.pop(0)
        if callable(outcome):
            outcome = outcome(request)
        # Only non-sensitive routing and result metadata is retained.
        record: tuple[str, str, str, int | str] = (
            request.method,
            request.url.host,
            request.url.path,
            "pending",
        )
        observed.append(record)

        if isinstance(outcome, BaseException):
            observed[-1] = (*record[:3], type(outcome).__name__)
            raise outcome

        observed[-1] = (*record[:3], outcome.status_code)
        return httpx.Response(
            outcome.status_code,
            headers=outcome.headers,
            content=outcome.content,
            request=request,
        )

    return httpx.MockTransport(handle), observed


class XanoAuthClientTransportIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def _install_transport(self, transport: httpx.MockTransport):
        real_async_client = httpx.AsyncClient

        def make_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        return patch(
            "Meu_projeto.services.xano_client.httpx.AsyncClient",
            side_effect=make_client,
        )

    def _client(self, coordinator=None) -> XanoAuthClient:
        return XanoAuthClient(
            base_url=MOCK_BASE_URL,
            timeout=0.1,
            coordinator=coordinator or XanoRequestCoordinator(5, 20),
        )

    def _assert_only_mock_auth_me(self, observed, expected_statuses) -> None:
        expected_path = f"/{AUTH_CANONICAL_GROUP}/auth/me"
        self.assertEqual([entry[0] for entry in observed], ["GET"] * len(expected_statuses))
        self.assertEqual([entry[1] for entry in observed], ["nexstock-test.invalid"] * len(expected_statuses))
        self.assertEqual([entry[2] for entry in observed], [expected_path] * len(expected_statuses))
        self.assertEqual([entry[3] for entry in observed], expected_statuses)

    async def test_http_429_is_classified_and_retry_after_is_preserved(self) -> None:
        mock_response = httpx.Response(
            429,
            headers={"Retry-After": "5", "Content-Type": "application/json"},
            json={"code": "RATE_LIMITED", "message": "Too Many Requests"},
        )
        transport, observed = _transport_for(mock_response)
        client = self._client()

        with self._install_transport(transport):
            with self.assertRaises(XanoServerError) as caught:
                await client.get_current_user(MOCK_TOKEN)

        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.retry_after, "5")
        self.assertEqual(observed, [("GET", "nexstock-test.invalid", f"/{AUTH_CANONICAL_GROUP}/auth/me", 429)])

    async def test_429_blocks_redirects_and_auto_retries_then_recovers_manually(self) -> None:
        limited = httpx.Response(
            429,
            headers={"Retry-After": "5", "Content-Type": "application/json"},
            json={"code": "RATE_LIMITED", "message": "Too Many Requests"},
        )
        recovered = httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json=_user_payload(["stock.read", "supplier.read"]),
        )
        transport, observed = _transport_for(limited, recovered)
        mono = [1000.0]
        client = self._client(
            XanoRequestCoordinator(
                5, 20, clock=lambda: mono[0], wall_clock=lambda: mono[0]
            )
        )
        state = _state()
        fake_clock = SimpleNamespace(time=lambda: mono[0])
        # A persisted browser token is present, but this server-side State has
        # not yet revalidated it after restoration/reconnection.
        state.session_validation = "invalid"

        with (
            patch("Meu_projeto.state.auth.auth_client", client),
            patch("Meu_projeto.state.auth.time", fake_clock),
            self._install_transport(transport),
        ):
            # First protected-route guard makes one real client request, handled
            # exclusively by MockTransport, and receives the synthetic 429.
            guard_result = await state.require_auth()
            self.assertIsNone(guard_result)
            self.assertEqual(state.auth_token, MOCK_TOKEN)
            self.assertEqual(state.session_validation, "temporarily_unavailable")
            self.assertEqual(
                state.error_message,
                "O servidor limitou temporariamente as solicitações. "
                "Aguarde e tente validar a sessão novamente.",
            )
            self.assertFalse(state.is_authenticated)
            self.assertEqual(state.permission_codes, [])
            self.assertFalse(state.has_permission("stock.exit"))

            stock_state = object.__new__(StockState)
            object.__setattr__(stock_state, "dirty_vars", set())
            object.__setattr__(stock_state, "get_state", AsyncMock(return_value=state))
            self.assertEqual(await StockState._session_token(stock_state), "")
            self.assertEqual(len(observed), 1)

            # Neither the login guard nor another protected-route guard causes
            # a redirect or another /auth/me request during the outage.
            self.assertIsNone(await state.check_already_logged_in())
            self.assertIsNone(await state.require_auth())
            self.assertEqual(len(observed), 1)

            # An explicit retry before Retry-After expires is rejected locally.
            self.assertIsNone(await state.retry_session_validation())
            self.assertIn("Aguarde", state.error_message)
            self.assertEqual(len(observed), 1)

            # After five seconds, the user action performs one fresh validation.
            mono[0] = 1005.0
            retry_result = await state.retry_session_validation()

        self.assertIsNotNone(
            retry_result,
            f"validation={state.session_validation}, requests={observed}, "
            f"retry_after_epoch={state.session_retry_after_epoch}",
        )
        self.assertEqual(state.auth_token, MOCK_TOKEN)
        self.assertEqual(state.session_validation, "valid")
        self.assertTrue(state.is_authenticated)
        self.assertEqual(state.permission_codes, ["stock.read", "supplier.read"])
        self.assertFalse(state.has_permission("stock.exit"))
        self.assertTrue(state.has_permission("stock.read"))
        self._assert_only_mock_auth_me(observed, [429, 200])

    async def test_http_401_invalidates_session_without_grants(self) -> None:
        unauthorized = httpx.Response(
            401,
            headers={"Content-Type": "application/json"},
            json={"code": "UNAUTHORIZED"},
        )
        transport, observed = _transport_for(unauthorized)
        client = self._client()
        state = _state()

        with (
            patch("Meu_projeto.state.auth.auth_client", client),
            self._install_transport(transport),
        ):
            result = await state.restore_session(force=True)

        self.assertFalse(result)
        self.assertEqual(state.auth_token, "")
        self.assertEqual(state.session_validation, "invalid")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.permission_codes, [])
        self.assertFalse(state.has_permission("stock.exit"))
        self._assert_only_mock_auth_me(observed, [401])

    async def test_timeout_is_temporary_and_preserves_token_without_retry(self) -> None:
        transport, observed = _transport_for(
            lambda request: httpx.ReadTimeout("simulated timeout", request=request)
        )
        client = self._client()
        state = _state()

        with (
            patch("Meu_projeto.state.auth.auth_client", client),
            self._install_transport(transport),
        ):
            result = await state.restore_session(force=True)
            second_result = await state.require_auth()

        self.assertFalse(result)
        self.assertIsNone(second_result)
        self.assertEqual(state.auth_token, MOCK_TOKEN)
        self.assertEqual(state.session_validation, "temporarily_unavailable")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.permission_codes, [])
        self.assertFalse(state.has_permission("stock.exit"))
        self._assert_only_mock_auth_me(observed, ["ReadTimeout"])


if __name__ == "__main__":
    unittest.main()
