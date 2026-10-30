"""Mocked session validation state-machine coverage; no Xano calls."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from Meu_projeto.pages.movimentacoes import EntryState, ExitState, MovementHistoryState
from Meu_projeto.pages.relatorios import ReportState
from Meu_projeto.pages.estoque import StockState
from Meu_projeto.services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoAuthClient,
    XanoServerError,
    XanoRequestCoordinator,
)
from Meu_projeto.state.auth import AuthState, _retry_after_epoch


def _auth_state(**overrides) -> AuthState:
    state = object.__new__(AuthState)
    object.__setattr__(state, "dirty_vars", set())
    defaults = {
        "auth_token": "persisted-test-token",
        "user_id": 23,
        "user_name": "Old cached user",
        "user_email": "old@example.invalid",
        "user_role": "stockkeeper",
        "inventory_profile_id": 2,
        "inventory_profile_code": "stockkeeper",
        "permission_codes": ["stock.read", "stock.exit"],
        "profile_name": "Almoxarife",
        "must_change_password": False,
        "password_change_notice": "",
        "is_authenticated": True,
        "is_loading": False,
        "error_message": "",
        "session_validation": "valid",
        "session_retry_after_epoch": 0.0,
    }
    for name, value in {**defaults, **overrides}.items():
        setattr(state, name, value)
    return state


def _user_data(*, permission_codes: list[str] | None = None, profile_code: str = "stockkeeper"):
    return {
        "id": 23,
        "name": "Fresh user",
        "email": "fresh@example.invalid",
        "role": "stockkeeper",
        "inventory_profile_id": 2,
        "inventory_profile_code": profile_code,
        "permission_codes": permission_codes or [],
    }


class RetryAfterParsingTests(unittest.TestCase):
    def test_retry_after_seconds_and_invalid_value(self):
        self.assertEqual(_retry_after_epoch("30", now=100), 130)
        self.assertEqual(_retry_after_epoch("invalid", now=100), 0)


class _RateLimitedClient:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None):
        self.response = httpx.Response(
            status_code,
            headers=headers or {},
            json={"code": "RATE_LIMITED", "message": "Too Many Requests"},
            request=httpx.Request("GET", "https://example.invalid/auth/me"),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        return self.response


class SessionValidationStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_xano_auth_client_preserves_retry_after_for_429(self):
        fake_client = _RateLimitedClient(429, {"Retry-After": "45"})
        with patch(
            "Meu_projeto.services.xano_client.httpx.AsyncClient",
            return_value=fake_client,
        ):
            client = XanoAuthClient(
                base_url="https://example.invalid",
                coordinator=XanoRequestCoordinator(5, 20),
            )
            with self.assertRaises(XanoServerError) as caught:
                await client.get_current_user("mock-token")

        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.retry_after, "45")

    async def test_login_429_honors_retry_after_without_automatic_retry(self):
        state = _auth_state(
            auth_token="",
            is_authenticated=False,
            permission_codes=[],
            session_validation="invalid",
        )
        with (
            patch("Meu_projeto.state.auth.time.time", side_effect=[1000, 1001, 1002, 1031]),
            patch(
                "Meu_projeto.state.auth.auth_client.login",
                new_callable=AsyncMock,
                side_effect=[
                    XanoServerError("limited", status_code=429, retry_after="30"),
                    {"authToken": "new-token"},
                ],
            ) as login,
            patch(
                "Meu_projeto.state.auth.auth_client.get_current_user",
                new_callable=AsyncMock,
                return_value=_user_data(permission_codes=["stock.read"]),
            ),
        ):
            await state.login("user@example.invalid", "password")
            self.assertEqual(state.session_retry_after_epoch, 1031)
            await state.login("user@example.invalid", "password")
            self.assertIn("Aguarde", state.error_message)
            self.assertEqual(login.await_count, 1)
            await state.login("user@example.invalid", "password")

        self.assertEqual(login.await_count, 2)
        self.assertEqual(state.session_validation, "valid")
        self.assertTrue(state.has_permission("stock.read"))

    async def test_temporary_failures_preserve_token_and_block_all_grants(self):
        failures = (
            XanoServerError("rate limited", status_code=429, retry_after="60"),
            XanoServerError("server error", status_code=500),
            XanoServerError("unavailable", status_code=503),
            XanoConnectionError("timeout"),
        )
        for failure in failures:
            with self.subTest(error=type(failure).__name__, status=failure.status_code):
                state = _auth_state()
                with patch(
                    "Meu_projeto.state.auth.auth_client.get_current_user",
                    new_callable=AsyncMock,
                    side_effect=failure,
                ) as get_user:
                    self.assertFalse(await state.restore_session(force=True))

                get_user.assert_awaited_once_with("persisted-test-token")
                self.assertEqual(state.auth_token, "persisted-test-token")
                self.assertEqual(state.session_validation, "temporarily_unavailable")
                self.assertFalse(state.is_authenticated)
                self.assertEqual(state.permission_codes, [])
                self.assertFalse(state.has_permission("stock.exit"))
                self.assertFalse(state.is_administrator)

    async def test_temporary_failure_does_not_redirect_or_repeat_auth_me(self):
        state = _auth_state(session_validation="invalid", is_authenticated=False)
        with patch(
            "Meu_projeto.state.auth.auth_client.get_current_user",
            new_callable=AsyncMock,
            side_effect=XanoServerError("limited", status_code=429),
        ) as get_user:
            guard_result = await state.require_auth()
            login_result = await state.check_already_logged_in()
            second_guard_result = await state.require_auth()

        self.assertIsNone(guard_result)
        self.assertIsNone(login_result)
        self.assertIsNone(second_guard_result)
        get_user.assert_awaited_once_with("persisted-test-token")
        self.assertEqual(state.auth_token, "persisted-test-token")
        self.assertEqual(state.session_validation, "temporarily_unavailable")

    async def test_401_invalidates_and_clears_the_session(self):
        state = _auth_state()
        with patch(
            "Meu_projeto.state.auth.auth_client.get_current_user",
            new_callable=AsyncMock,
            side_effect=XanoAuthError("expired", status_code=401),
        ):
            self.assertFalse(await state.restore_session(force=True))

        self.assertEqual(state.auth_token, "")
        self.assertEqual(state.session_validation, "invalid")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.permission_codes, [])
        self.assertFalse(state.has_permission("stock.exit"))

    async def test_403_blocks_access_without_assuming_token_is_invalid(self):
        state = _auth_state()
        with patch(
            "Meu_projeto.state.auth.auth_client.get_current_user",
            new_callable=AsyncMock,
            side_effect=XanoAuthError("forbidden", status_code=403),
        ):
            self.assertFalse(await state.restore_session(force=True))

        self.assertEqual(state.auth_token, "persisted-test-token")
        self.assertEqual(state.session_validation, "forbidden")
        self.assertFalse(state.is_authenticated)
        self.assertEqual(state.permission_codes, [])
        self.assertFalse(state.has_permission("stock.exit"))

    async def test_retry_after_blocks_early_retry_then_refreshes_grants(self):
        state = _auth_state()
        with (
            patch("Meu_projeto.state.auth.time.time", side_effect=[1000, 1000, 1091]),
            patch(
                "Meu_projeto.state.auth.auth_client.get_current_user",
                new_callable=AsyncMock,
                side_effect=[
                    XanoServerError("limited", status_code=429, retry_after="90"),
                    _user_data(permission_codes=["stock.read"]),
                ],
            ) as get_user,
        ):
            self.assertFalse(await state.restore_session(force=True))
            self.assertEqual(state.session_retry_after_epoch, 1090)
            early_result = await state.retry_session_validation()
            self.assertIsNone(early_result)
            self.assertIn("Aguarde", state.error_message)
            self.assertEqual(get_user.await_count, 1)

            success_result = await state.retry_session_validation()

        self.assertIsNotNone(success_result)
        self.assertEqual(get_user.await_count, 2)
        self.assertEqual(state.session_validation, "valid")
        self.assertTrue(state.is_authenticated)
        self.assertEqual(state.permission_codes, ["stock.read"])
        self.assertFalse(state.has_permission("stock.exit"))
        self.assertTrue(state.has_permission("stock.read"))

    async def test_protected_loader_does_not_call_xano_without_current_grant(self):
        auth_state = _auth_state(permission_codes=[], session_validation="valid")
        stock_state = object.__new__(StockState)
        object.__setattr__(stock_state, "dirty_vars", set())
        object.__setattr__(stock_state, "get_state", AsyncMock(return_value=auth_state))

        token = await StockState._session_token(stock_state)

        self.assertEqual(token, "")
        self.assertFalse(auth_state.has_permission("stock.read"))

    async def test_operation_and_report_loaders_reject_temporarily_unvalidated_session(self):
        auth_state = _auth_state(
            is_authenticated=False,
            permission_codes=[],
            session_validation="temporarily_unavailable",
        )
        for state_class in (EntryState, ExitState, MovementHistoryState, ReportState):
            with self.subTest(state=state_class.__name__):
                page_state = object.__new__(state_class)
                object.__setattr__(page_state, "dirty_vars", set())
                object.__setattr__(page_state, "get_state", AsyncMock(return_value=auth_state))
                token = await state_class._session_token(page_state)
                self.assertEqual(token, "")

    async def test_entry_and_exit_handlers_do_not_write_during_temporary_validation_failure(self):
        auth_state = _auth_state(
            is_authenticated=False,
            permission_codes=[],
            session_validation="temporarily_unavailable",
        )
        entry = object.__new__(EntryState)
        object.__setattr__(entry, "dirty_vars", set())
        for name, value in {
            "is_submitting": False,
            "error_message": "",
            "success_message": "",
            "product_id": "5",
            "quantidade": "1",
            "motivo": "test reason",
            "supplier_id": "none",
        }.items():
            setattr(entry, name, value)
        object.__setattr__(entry, "get_state", AsyncMock(return_value=auth_state))

        exit_state = object.__new__(ExitState)
        object.__setattr__(exit_state, "dirty_vars", set())
        for name, value in {
            "is_submitting": False,
            "error_message": "",
            "success_message": "",
            "product_id": "5",
            "quantidade": "1",
            "motivo": "test reason",
            "saldo_disponivel": "5",
            "stock_balance_found": True,
            "has_available_stock": True,
        }.items():
            setattr(exit_state, name, value)
        object.__setattr__(exit_state, "get_state", AsyncMock(return_value=auth_state))

        with (
            patch("Meu_projeto.pages.movimentacoes.auth_client.create_stock_entry", new_callable=AsyncMock) as create_entry,
            patch("Meu_projeto.pages.movimentacoes.auth_client.create_stock_exit", new_callable=AsyncMock) as create_exit,
        ):
            async for _event in entry.register_entry():
                pass
            async for _event in exit_state.register_exit():
                pass

        create_entry.assert_not_awaited()
        create_exit.assert_not_awaited()
        self.assertIn("temporariamente", entry.error_message)
        self.assertIn("temporariamente", exit_state.error_message)

    async def test_validated_session_uses_fresh_operational_and_admin_rules(self):
        state = _auth_state(session_validation="invalid", is_authenticated=False)
        with patch(
            "Meu_projeto.state.auth.auth_client.get_current_user",
            new_callable=AsyncMock,
            return_value=_user_data(permission_codes=["stock.entry", "stock.exit"]),
        ):
            self.assertTrue(await state.restore_session())

        self.assertTrue(state.session_is_valid)
        self.assertTrue(state.has_permission("stock.entry"))
        self.assertTrue(state.has_permission("stock.exit"))
        self.assertFalse(state.is_administrator)


if __name__ == "__main__":
    unittest.main()
