"""Own-password contracts and mocked requests. Never changes a real password."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from Meu_projeto.pages.account_password import AccountPasswordState, alterar_senha_conta
from Meu_projeto.services.xano_client import XanoAuthClient, XanoAuthError, XanoConnectionError, XanoRequestError, XanoServerError, auth_client
from Meu_projeto.state.auth import AuthState
from tests.test_dashboard_periods_notifications import state


ROOT = Path(__file__).resolve().parents[1]
XS = (ROOT / "xano/api/authentication/auth/change_password_PATCH.xs").read_text(encoding="utf-8")


def form(**changes):
    return {"current_password": "MockPrevious123", "password": "MockFollowing456", "confirm_password": "MockFollowing456", **changes}


def user(profile="administrator", valid=True):
    return SimpleNamespace(session_is_valid=valid, must_change_password=False,
                           auth_token="mock-session", inventory_profile_code=profile,
                           _home_route=lambda: "/compras" if profile == "compras" else "/dashboard")


async def collect(generator):
    return [event async for event in generator if event is not None]


class AccountPasswordBackendContractTests(unittest.TestCase):
    def test_only_authenticated_identity_can_be_read_or_updated(self):
        self.assertIn('auth = "user"', XS)
        inputs = XS.split("input {", 1)[1].split("stack {", 1)[0]
        self.assertNotIn("user_id", inputs)
        self.assertEqual(inputs.count("sensitive = true"), 3)
        self.assertEqual(XS.count("field_value = $auth.id"), 2)
        self.assertNotIn("$input.user_id", XS)
        self.assertNotIn("authorize_permission", XS)

    def test_checks_and_policy_precede_single_native_password_update(self):
        self.assertIn("$input.password == $input.confirm_password", XS)
        self.assertIn('(?=.*[A-Za-z])(?=.*[0-9]).{8,}', XS)
        self.assertIn("$user.is_active !== false", XS)
        self.assertIn("$user.password !== null", XS)
        self.assertEqual(XS.count("security.check_password"), 2)
        write = XS.index("db.edit user")
        for code in ("PASSWORD_MISMATCH", "PASSWORD_POLICY_INVALID", "CURRENT_PASSWORD_INVALID", "NEW_PASSWORD_MUST_DIFFER"):
            self.assertLess(XS.index(code), write)
        self.assertIn("text_password = $input.current_password", XS)
        self.assertIn("text_password = $input.password", XS)
        self.assertIn("hash_password = $user.password", XS)
        self.assertEqual(XS.count("db.edit"), 1)
        self.assertIn("data = {password: $input.password}", XS)
        self.assertIn('output = ["id"]', XS)
        schema = (ROOT / "xano/table/user.xs").read_text(encoding="utf-8")
        self.assertIn("password? password filters=min:8|minAlpha:1|minDigit:1", schema)

    def test_no_secrets_in_public_response_or_log_writers(self):
        self.assertEqual(XS.split("response =", 1)[1].strip(), "{senha_atualizada: true}\n}")
        for forbidden in ("debug.log", "inventory_audit_log", "purchase_request", "event_log", "api.request", "security.create_auth_token"):
            self.assertNotIn(forbidden, XS)
        login = (ROOT / "xano/api/authentication/auth/login_POST.xs").read_text(encoding="utf-8")
        self.assertIn("expiration = 86400", login)
        self.assertNotIn("revoke", XS)


class AccountPasswordStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.obj = state(AccountPasswordState)
        self.obj.enabled = True

    async def test_all_existing_profiles_use_same_own_password_flow(self):
        for profile in ("administrator", "stockkeeper", "read_only", "compras"):
            with self.subTest(profile=profile):
                obj = state(AccountPasswordState)
                obj.enabled = True
                data = form(user_id=9999)
                with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user(profile))), \
                     patch.object(auth_client, "change_password", new=AsyncMock(return_value={"senha_atualizada": True})) as change:
                    output = await collect(obj.submit(data))
                self.assertIn(AuthState.complete_password_change, output)
                self.assertEqual(data, {})
                change.assert_awaited_once_with("mock-session", "MockPrevious123", "MockFollowing456", "MockFollowing456")
                self.assertFalse(obj.saving)

    async def test_empty_mismatch_same_and_policy_errors_do_not_send(self):
        cases = [form(current_password=""), form(password="", confirm_password=""),
                 form(confirm_password="mismatch"), form(password="short1", confirm_password="short1"),
                 form(password="abcdefgh", confirm_password="abcdefgh"), form(password="12345678", confirm_password="12345678"),
                 form(password="MockPrevious123", confirm_password="MockPrevious123")]
        for data in cases:
            with patch.object(auth_client, "change_password", new=AsyncMock()) as change:
                await collect(self.obj.submit(data))
            change.assert_not_awaited()
            self.assertTrue(self.obj.error)
            self.assertEqual(data, {})

    async def test_unauthenticated_disabled_and_initial_flow_do_not_write(self):
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user(valid=False))), \
             patch.object(auth_client, "change_password", new=AsyncMock()) as change:
            await collect(self.obj.submit(form()))
        change.assert_not_awaited()
        self.obj.enabled = False
        with patch.object(auth_client, "change_password", new=AsyncMock()) as change:
            await collect(self.obj.submit(form()))
        change.assert_not_awaited()
        self.obj.enabled = True
        initial = user()
        initial.must_change_password = True
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=initial)), \
             patch.object(auth_client, "change_password", new=AsyncMock()) as change:
            self.assertIn("/alterar-senha", str(await collect(self.obj.submit(form()))))
        change.assert_not_awaited()

    async def test_double_submit_is_blocked_during_request(self):
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user())), \
             patch.object(auth_client, "change_password", new=AsyncMock(return_value={"senha_atualizada": True})) as change:
            pending = self.obj.submit(form())
            await anext(pending)
            self.assertTrue(self.obj.saving)
            await collect(self.obj.submit(form()))
            await collect(pending)
        change.assert_awaited_once()

    async def test_wrong_current_password_and_failures_are_sanitized(self):
        errors = [XanoRequestError("DO_NOT_DISPLAY_SECRET", "CURRENT_PASSWORD_INVALID", 400, {}),
                  XanoServerError("DO_NOT_DISPLAY_SECRET", status_code=500),
                  XanoConnectionError("DO_NOT_DISPLAY_SECRET"), RuntimeError("DO_NOT_DISPLAY_SECRET")]
        for error in errors:
            with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user())), \
                 patch.object(auth_client, "change_password", new=AsyncMock(side_effect=error)) as change:
                output = await collect(self.obj.submit(form()))
            self.assertNotIn(AuthState.complete_password_change, output)
            self.assertNotIn("DO_NOT_DISPLAY_SECRET", self.obj.error)
            self.assertTrue(self.obj.error)
            change.assert_awaited_once()

    async def test_rate_limit_is_not_retried_automatically(self):
        error = XanoRequestError("safe", "TOO_MANY_REQUESTS", 429, {}, retry_after="20")
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user())), \
             patch.object(auth_client, "change_password", new=AsyncMock(side_effect=error)) as change:
            await collect(self.obj.submit(form()))
            await collect(self.obj.submit(form()))
        change.assert_awaited_once()

    async def test_401_logs_out_and_session_change_does_not_log_out_new_session(self):
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user())), \
             patch.object(auth_client, "change_password", new=AsyncMock(side_effect=XanoAuthError("safe", status_code=401))):
            self.assertIn(AuthState.logout, await collect(self.obj.submit(form())))
        other = user()
        other.auth_token = "different-session"
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(side_effect=[user(), other])), \
             patch.object(auth_client, "change_password", new=AsyncMock(return_value={"senha_atualizada": True})):
            self.assertNotIn(AuthState.complete_password_change, await collect(self.obj.submit(form())))
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(side_effect=[user(), other])), \
             patch.object(auth_client, "change_password", new=AsyncMock(side_effect=XanoAuthError("safe", status_code=401))):
            self.assertNotIn(AuthState.logout, await collect(self.obj.submit(form())))

    async def test_cancel_clears_form_visibility_and_returns_to_profile_home(self):
        self.obj.show_current = self.obj.show_new = self.obj.show_confirmation = True
        self.obj.error = "old"
        with patch.object(AccountPasswordState, "get_state", new=AsyncMock(return_value=user("compras"))):
            output = await collect(self.obj.cancel())
        self.assertIn("reset()", str(output))
        self.assertIn("/compras", str(output))
        self.assertFalse(self.obj.show_current or self.obj.show_new or self.obj.show_confirmation)
        self.assertEqual(self.obj.error, "")
        self.assertNotIn("current_password", AccountPasswordState.__annotations__)

    def test_form_is_uncontrolled_masked_and_cleared_on_submit(self):
        rendered = str(alterar_senha_conta())
        for expected in ("account-password-form", "Cancelar", "Confirmar nova senha", "aria-pressed", "password"):
            self.assertIn(expected, rendered)
        source = (ROOT / "Meu_projeto/pages/account_password.py").read_text(encoding="utf-8")
        self.assertIn("auto_complete=False", source)
        self.assertIn("reset_on_submit=True", source)
        self.assertNotIn("value=current", source)


class AccountPasswordHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_contract_identity_and_no_secret_payload_in_success(self):
        client = XanoAuthClient()
        with patch.object(client, "_send_request", new=AsyncMock(return_value=httpx.Response(200, json={"senha_atualizada": True, "password": "DO_NOT_RETURN"}))) as send:
            result = await client.change_password("mock-token", "MockPrevious123", "MockFollowing456", "MockFollowing456")
        self.assertEqual(result, {"senha_atualizada": True})
        self.assertEqual(send.await_args.args[0], "PATCH")
        self.assertTrue(send.await_args.args[1].endswith("/auth/change-password"))
        self.assertEqual(set(send.await_args.kwargs["json_payload"]), {"current_password", "password", "confirm_password"})

    async def test_all_known_password_errors_and_echoed_secrets_are_not_logged(self):
        client = XanoAuthClient()
        for code in ("CURRENT_PASSWORD_INVALID", "PASSWORD_MISMATCH", "PASSWORD_POLICY_INVALID", "NEW_PASSWORD_MUST_DIFFER"):
            response = httpx.Response(400, json={"code": "ERROR_CODE_INPUT_ERROR", "message": code, "payload": "MockPrevious123 MockFollowing456 mock-token"})
            with patch.object(client, "_send_request", new=AsyncMock(return_value=response)), \
                 self.assertLogs("Meu_projeto.services.xano_client", level="INFO") as logs:
                with self.assertRaises(XanoRequestError) as caught:
                    await client.change_password("mock-token", "MockPrevious123", "MockFollowing456", "MockFollowing456")
            self.assertEqual(caught.exception.error_code, code)
            self.assertEqual(caught.exception.payload, {})
            for secret in ("MockPrevious123", "MockFollowing456", "mock-token"):
                self.assertNotIn(secret, " ".join(logs.output))
                self.assertNotIn(secret, str(caught.exception))

    async def test_internal_errors_invalid_json_and_false_confirmation_fail_closed(self):
        client = XanoAuthClient()
        responses = [httpx.Response(500, json={"message": "MockPrevious123", "payload": "MockFollowing456"}),
                     httpx.Response(200, text="MockFollowing456"), httpx.Response(200, json={"senha_atualizada": False}),
                     httpx.Response(200, json={"senha_atualizada": "true"})]
        for response in responses:
            with patch.object(client, "_send_request", new=AsyncMock(return_value=response)) as send, \
                 self.assertLogs("Meu_projeto.services.xano_client", level="INFO") as logs:
                with self.assertRaises(XanoServerError) as caught:
                    await client.change_password("mock-token", "MockPrevious123", "MockFollowing456", "MockFollowing456")
            send.assert_awaited_once()
            self.assertEqual(caught.exception.payload, {})
            self.assertNotIn("MockPrevious123", " ".join(logs.output))
            self.assertNotIn("MockFollowing456", " ".join(logs.output))

    async def test_http_401_and_timeout_never_echo_secret_details_or_retry(self):
        client = XanoAuthClient()
        cases = ((httpx.Response(401, json={"message": "MockPrevious123", "payload": "MockFollowing456"}), None, XanoAuthError),
                 (None, httpx.ReadTimeout("MockPrevious123 MockFollowing456"), XanoConnectionError))
        for response, failure, expected in cases:
            with patch.object(client, "_send_request", new=AsyncMock(return_value=response, side_effect=failure)) as send, \
                 self.assertLogs("Meu_projeto.services.xano_client", level="INFO") as logs:
                with self.assertRaises(expected) as caught:
                    await client.change_password("mock-token", "MockPrevious123", "MockFollowing456", "MockFollowing456")
            send.assert_awaited_once()
            for secret in ("MockPrevious123", "MockFollowing456", "mock-token"):
                self.assertNotIn(secret, " ".join(logs.output))
                self.assertNotIn(secret, str(caught.exception))
            self.assertEqual(caught.exception.payload, {})

    def test_success_clears_only_local_session_and_requires_login(self):
        auth = state(AuthState)
        auth.auth_token = "mock-token"
        auth.user_name = "Demonstration"
        result = auth.complete_password_change()
        self.assertEqual(auth.auth_token, "")
        self.assertEqual(auth.user_name, "")
        self.assertIn("Senha alterada", auth.password_change_notice)
        self.assertIn('"/"', str(result))
