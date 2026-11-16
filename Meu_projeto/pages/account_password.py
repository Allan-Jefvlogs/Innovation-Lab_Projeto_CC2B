"""Troca voluntária de senha, sempre validada pelo backend Xano."""

import os
import time
from typing import Any
import reflex as rx

from ..components.layout import page, session_validation_panel
from ..components.theme import ERROR_TEXT, TEXT_MUTED
from ..services.xano_client import XanoAuthError, XanoError, XanoRequestError, auth_client
from ..state import AuthState

ACCOUNT_PASSWORD_ENABLED = os.getenv("NEXSTOCK_ACCOUNT_PASSWORD_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


class AccountPasswordState(rx.State):
    enabled: bool = ACCOUNT_PASSWORD_ENABLED
    error: str = ""
    saving: bool = False
    show_current: bool = False
    show_new: bool = False
    show_confirmation: bool = False
    retry_after_epoch: float = 0.0

    def toggle_visibility(self, field: str):
        if self.saving:
            return
        if field in {"show_current", "show_new", "show_confirmation"}:
            setattr(self, field, not getattr(self, field))

    def reset_form(self):
        self.error = ""
        self.show_current = self.show_new = self.show_confirmation = False

    async def cancel(self):
        if self.saving:
            return
        self.reset_form()
        yield rx.call_script("document.getElementById('account-password-form')?.reset()")
        auth = await self.get_state(AuthState)
        yield rx.redirect(auth._home_route() if auth.session_is_valid else "/")

    async def submit(self, form_data: dict[str, Any]):
        current = str(form_data.get("current_password") or "")
        new = str(form_data.get("password") or "")
        confirm = str(form_data.get("confirm_password") or "")
        form_data.clear()
        try:
            if self.saving or not self.enabled or self.retry_after_epoch > time.time():
                return
            self.error = ""
            valid_policy = len(new) >= 8 and any(c.isascii() and c.isalpha() for c in new) and any(c.isascii() and c.isdigit() for c in new)
            if not current:
                self.error = "Informe sua senha atual."
                return
            if not valid_policy:
                self.error = "A nova senha deve ter ao menos 8 caracteres, uma letra e um número."
                return
            if new != confirm:
                self.error = "A confirmação da senha não confere."
                return
            if new == current:
                self.error = "A nova senha deve ser diferente da senha atual."
                return
            auth = await self.get_state(AuthState)
            if not auth.session_is_valid:
                self.error = "A sessão precisa ser validada novamente."
                return
            if auth.must_change_password:
                yield rx.redirect("/alterar-senha")
                return
            if self.saving:
                return
            token = str(auth.auth_token or "").strip()
            self.saving = True
            yield
            try:
                await auth_client.change_password(token, current, new, confirm)
                latest = await self.get_state(AuthState)
                if str(latest.auth_token or "").strip() != token:
                    self.error = "A sessão mudou durante a operação. Entre novamente com a nova senha."
                    return
                # Clears this browser session only; other Xano JWTs are not revoked.
                yield AuthState.complete_password_change
            except XanoAuthError:
                latest = await self.get_state(AuthState)
                if str(latest.auth_token or "").strip() == token:
                    yield AuthState.logout
                else:
                    self.error = "A sessão mudou durante a operação."
            except XanoRequestError as exc:
                messages = {
                    "CURRENT_PASSWORD_INVALID": "A senha atual está incorreta.",
                    "NEW_PASSWORD_MUST_DIFFER": "A nova senha deve ser diferente da senha atual.",
                    "PASSWORD_MISMATCH": "A confirmação da senha não confere.",
                    "PASSWORD_POLICY_INVALID": "A nova senha deve ter ao menos 8 caracteres, uma letra e um número.",
                    "INITIAL_PASSWORD_FLOW_REQUIRED": "Conclua primeiro a alteração obrigatória da senha inicial.",
                }
                self.error = messages.get(exc.error_code, "Não foi possível confirmar a alteração da senha. Tente entrar com a nova senha antes de repetir.")
                if exc.status_code == 429:
                    delay = auth_client.coordinator._retry_delay(exc.retry_after, auth_client.coordinator.window_seconds, time.time())
                    self.retry_after_epoch = time.time() + delay
                    self.error = "Aguarde o intervalo de recuperação antes de tentar novamente."
            except XanoError as exc:
                self.error = "Não foi possível confirmar a alteração da senha. Tente entrar com a nova senha antes de repetir."
                if getattr(exc, "status_code", None) == 429:
                    self.retry_after_epoch = time.time() + float(getattr(exc, "retry_after_seconds", 20))
                    self.error = "Aguarde o intervalo de recuperação antes de tentar novamente."
            except Exception:
                # Never format/log arbitrary exceptions from a password operation.
                self.error = "Não foi possível confirmar a alteração da senha. Tente entrar com a nova senha antes de repetir."
            finally:
                self.saving = False
        finally:
            current = new = confirm = ""
            self.show_current = self.show_new = self.show_confirmation = False


def _password_field(label: str, name: str, visible: Any, field: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, weight="medium", font_size="14px"),
        rx.hstack(
            rx.input(name=name, aria_label=label, type=rx.cond(visible, "text", "password"), auto_complete=False,
                     required=True, disabled=AccountPasswordState.saving | ~AccountPasswordState.enabled, width="100%"),
            rx.button(rx.cond(visible, rx.icon("eye_off", size=17), rx.icon("eye", size=17)),
                      type="button", variant="ghost", aria_label="Mostrar ou ocultar " + label.lower(),
                      aria_pressed=visible, on_click=AccountPasswordState.toggle_visibility(field),
                      disabled=AccountPasswordState.saving | ~AccountPasswordState.enabled),
            width="100%", align="center",
        ),
        width="100%", align="stretch", spacing="2",
    )


def alterar_senha_conta() -> rx.Component:
    protected = rx.vstack(
        rx.heading("Alterar senha", size="6"),
        rx.text("Informe sua senha atual e escolha uma nova senha.", color=TEXT_MUTED),
        rx.cond(
            ~AccountPasswordState.enabled,
            rx.text("A alteração será habilitada após a publicação do contrato no Xano.", color=TEXT_MUTED, role="status"),
            rx.fragment(),
        ),
        rx.form(
            rx.vstack(
                _password_field("Senha atual", "current_password", AccountPasswordState.show_current, "show_current"),
                _password_field("Nova senha", "password", AccountPasswordState.show_new, "show_new"),
                _password_field("Confirmar nova senha", "confirm_password", AccountPasswordState.show_confirmation, "show_confirmation"),
                rx.text("A senha deve ter ao menos 8 caracteres, uma letra e um número.", color=TEXT_MUTED, font_size="12px"),
                rx.cond(AccountPasswordState.error != "", rx.text(AccountPasswordState.error, color=ERROR_TEXT, role="alert"), rx.fragment()),
                rx.button("Alterar senha", type="submit", loading=AccountPasswordState.saving, disabled=AccountPasswordState.saving | ~AccountPasswordState.enabled),
                rx.button("Cancelar", type="button", variant="soft", on_click=AccountPasswordState.cancel, disabled=AccountPasswordState.saving),
                spacing="4", align="stretch", width="100%",
            ),
            on_submit=AccountPasswordState.submit,
            id="account-password-form", reset_on_submit=True, on_mount=AccountPasswordState.reset_form,
        ),
        max_width="520px", width="100%", padding="24px", background="white", border_radius="17px", align="stretch", spacing="4",
    )
    return rx.cond(AuthState.session_is_valid & ~AuthState.must_change_password, page("Alterar senha", protected), session_validation_panel())
