"""Isolated coverage for authentication transport failures and recovery."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, call, patch

import httpx

from Meu_projeto.pages.login import login as login_page
from Meu_projeto.services.xano_client import (
    XanoAuthClient,
    XanoConnectionError,
)
from Meu_projeto.state.auth import AuthState


CONNECTION_MESSAGE = (
    "Não foi possível conectar ao servidor. "
    "Verifique sua conexão e tente novamente."
)


def _auth_state() -> AuthState:
    """Create an isolated Reflex State shell without starting the app."""
    state = object.__new__(AuthState)
    object.__setattr__(state, "dirty_vars", set())
    defaults = {
        "auth_token": "",
        "user_id": 0,
        "user_name": "",
        "user_email": "",
        "user_role": "",
        "inventory_profile_id": None,
        "inventory_profile_code": "",
        "permission_codes": [],
        "profile_name": "",
        "must_change_password": False,
        "password_change_notice": "",
        "is_authenticated": False,
        "is_loading": False,
        "error_message": "",
    }
    for name, value in defaults.items():
        setattr(state, name, value)
    return state


class _FailingAsyncClient:
    """AsyncClient fake that raises during POST without network access."""

    def __init__(self, exception: Exception):
        self.exception = exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        raise self.exception


class AuthConnectionFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_xano_client_maps_timeout_and_connect_error(self) -> None:
        request = httpx.Request("POST", "https://example.invalid/auth/login")
        failures = (
            httpx.ReadTimeout("simulated timeout", request=request),
            httpx.ConnectError("simulated connection failure", request=request),
        )

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                fake_client = _FailingAsyncClient(failure)
                with patch(
                    "Meu_projeto.services.xano_client.httpx.AsyncClient",
                    return_value=fake_client,
                ):
                    client = XanoAuthClient(base_url="https://example.invalid")
                    with self.assertRaises(XanoConnectionError) as caught:
                        await client.login("test@example.invalid", "not-a-real-password")

                self.assertEqual(str(caught.exception), CONNECTION_MESSAGE)

    async def test_auth_state_stays_logged_out_and_allows_retry(self) -> None:
        state = _auth_state()
        user_data = {
            "id": 17,
            "name": "Usuário de teste",
            "email": "test@example.invalid",
            "role": "stockkeeper",
            "inventory_profile_id": 2,
            "inventory_profile_code": "stockkeeper",
            "permission_codes": [],
        }
        login_mock = AsyncMock(
            side_effect=[
                XanoConnectionError(CONNECTION_MESSAGE),
                XanoConnectionError(CONNECTION_MESSAGE),
                {"authToken": "fake-test-token", "user_id": 17},
            ]
        )

        with (
            patch("Meu_projeto.state.auth.auth_client.login", login_mock),
            patch(
                "Meu_projeto.state.auth.auth_client.get_current_user",
                new_callable=AsyncMock,
                return_value=user_data,
            ) as get_user,
        ):
            await state.login("test@example.invalid", "test-password")
            self.assertEqual(state.error_message, CONNECTION_MESSAGE)
            self.assertFalse(state.is_authenticated)
            self.assertFalse(state.is_loading)
            self.assertEqual(state.auth_token, "")

            await state.login("test@example.invalid", "test-password")
            self.assertEqual(state.error_message, CONNECTION_MESSAGE)
            self.assertFalse(state.is_authenticated)
            self.assertFalse(state.is_loading)
            self.assertEqual(state.auth_token, "")

            result = await state.login("test@example.invalid", "test-password")

        self.assertIsNotNone(result)
        self.assertTrue(state.is_authenticated)
        self.assertFalse(state.is_loading)
        self.assertEqual(state.auth_token, "fake-test-token")
        self.assertEqual(state.error_message, "")
        login_mock.assert_has_awaits(
            [
                call("test@example.invalid", "test-password"),
                call("test@example.invalid", "test-password"),
                call("test@example.invalid", "test-password"),
            ]
        )
        get_user.assert_awaited_once_with("fake-test-token")

    def test_login_page_exposes_auth_errors_as_an_alert(self) -> None:
        rendered = str(login_page())
        self.assertIn("error_message", rendered)
        self.assertIn('role:"alert"', rendered)
        self.assertIn("triangle_alert", rendered)


if __name__ == "__main__":
    unittest.main()
