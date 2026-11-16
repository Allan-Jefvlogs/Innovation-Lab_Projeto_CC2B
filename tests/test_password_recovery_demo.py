from __future__ import annotations

import inspect
import unittest

from Meu_projeto import Meu_projeto as app_module
from Meu_projeto.pages.password_recovery_demo import (
    CONFIRMATION_MESSAGE,
    PasswordRecoveryDemoState,
    _recovery_confirmation_dialog,
    password_recovery_demo,
)


class PasswordRecoveryDemoTests(unittest.TestCase):
    @staticmethod
    def _state() -> PasswordRecoveryDemoState:
        state = object.__new__(PasswordRecoveryDemoState)
        state._init_bookkeeping()
        state.confirmation_open = False
        state.error_message = ""
        return state

    def test_valid_email_opens_confirmation_without_storing_email(self):
        state = self._state()

        state.submit_demo({"email": "person@example.test"})

        self.assertTrue(state.confirmation_open)
        self.assertEqual(state.error_message, "")
        self.assertNotIn("email", PasswordRecoveryDemoState.__annotations__)

    def test_empty_and_malformed_email_are_rejected(self):
        for value in ("", "not-an-email", "person@invalid"):
            with self.subTest(value=value):
                state = self._state()

                state.submit_demo({"email": value})

                self.assertFalse(state.confirmation_open)
                self.assertEqual(state.error_message, "Informe um e-mail válido.")

    def test_confirmation_waits_for_acknowledgement_then_returns_to_login(self):
        state = self._state()
        state.submit_demo({"email": "person@example.test"})

        self.assertTrue(state.confirmation_open)
        state.acknowledge_and_return()

        self.assertFalse(state.confirmation_open)
        self.assertEqual(state.error_message, "")
        self.assertIn("você receberá em breve", CONFIRMATION_MESSAGE)

        dialog_source = inspect.getsource(_recovery_confirmation_dialog)
        handler_source = inspect.getsource(PasswordRecoveryDemoState.acknowledge_and_return.fn)
        self.assertIn('"Solicitação recebida!"', dialog_source)
        self.assertIn('"Entendi"', dialog_source)
        self.assertNotIn("Demonstra", dialog_source)
        self.assertIn("PasswordRecoveryDemoState.acknowledge_and_return", dialog_source)
        self.assertIn('rx.redirect("/")', handler_source)

    def test_page_has_email_validation_and_returns_to_login(self):
        source = inspect.getsource(password_recovery_demo)
        self.assertIn('type="email"', source)
        self.assertIn('name="email"', source)
        self.assertIn("required=True", source)
        self.assertIn('"Solicitar recuperação"', source)
        self.assertIn('"Voltar ao login"', source)
        self.assertIn('href="/"', source)
        self.assertIn("Informe seu e-mail para receber as instru", source)
        self.assertIn('margin_top="16px"', source)
        self.assertIn("PasswordRecoveryDemoState.submit_demo", source)

    def test_recovery_route_is_public_and_has_no_backend_integration(self):
        source = inspect.getsource(password_recovery_demo)
        state_source = inspect.getsource(PasswordRecoveryDemoState)
        route_source = inspect.getsource(app_module)
        self.assertIn('route="/recuperar-senha"', route_source)
        self.assertNotIn("auth_client", source + state_source)
        self.assertNotIn("httpx", source + state_source)
        self.assertNotIn("token", source + state_source)


if __name__ == "__main__":
    unittest.main()
