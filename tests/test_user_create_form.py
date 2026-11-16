from __future__ import annotations

import unittest
import inspect

from Meu_projeto.pages.usuarios import UserState, _password_input, _user_modal


def _user_state() -> UserState:
    state = object.__new__(UserState)
    state._init_bookkeeping()
    state.profiles = [{"id": "1", "name": "Administrador"}]
    state.profile_error = ""
    state.modal_open = False
    state.editing_user_id = ""
    state.form_name = ""
    state.form_email = ""
    state.form_profile_id = ""
    state.form_error = ""
    state.is_self_edit = False
    state.editing_is_active = True
    state.show_create_password = False
    state.success_message = ""
    return state


class NewUserFormTests(unittest.TestCase):
    def _assert_create_fields_empty(self, state: UserState) -> None:
        self.assertEqual(state.form_name, "")
        self.assertEqual(state.form_email, "")
        self.assertEqual(state.form_profile_id, "")

    def test_first_open_starts_with_empty_fields_and_existing_password_behavior(self):
        state = _user_state()

        state.open_create_modal()

        self.assertTrue(state.modal_open)
        self._assert_create_fields_empty(state)
        self.assertFalse(state.show_create_password)

    def test_cancel_and_reopen_clears_name_email_and_profile(self):
        state = _user_state()
        state.open_create_modal()
        state.form_name = "Pessoa anterior"
        state.form_email = "previous@example.test"
        state.form_profile_id = "1"

        state.close_modal()
        state.open_create_modal()

        self.assertTrue(state.modal_open)
        self._assert_create_fields_empty(state)

    def test_opening_create_after_edit_clears_the_edited_user_values(self):
        state = _user_state()
        state.editing_user_id = "42"
        state.form_name = "Usuário editado"
        state.form_email = "edited@example.test"
        state.form_profile_id = "1"
        state.modal_open = True

        state.close_modal()
        state.open_create_modal()

        self.assertTrue(state.modal_open)
        self._assert_create_fields_empty(state)
        self.assertEqual(state.editing_user_id, "")

    def test_browser_autofill_is_disabled_for_name_and_email_only(self):
        modal_source = inspect.getsource(_user_modal)
        password_source = inspect.getsource(_password_input)

        self.assertEqual(modal_source.count('auto_complete="off"'), 2)
        self.assertIn("auto_complete=False", password_source)
        self.assertNotIn("auto_complete=\"off\"", password_source)


if __name__ == "__main__":
    unittest.main()
