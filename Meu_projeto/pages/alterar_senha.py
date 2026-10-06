"""Troca obrigatória da senha inicial pelo próprio usuário."""

import logging
from typing import Any

import reflex as rx

from ..services.xano_client import XanoAuthError, XanoError, XanoRequestError, auth_client
from ..state import AuthState


logger = logging.getLogger(__name__)


class InitialPasswordState(rx.State):
    show_password: bool = False
    show_confirmation: bool = False
    is_saving: bool = False
    error_message: str = ""

    def toggle_password(self):
        self.show_password = not self.show_password

    def toggle_confirmation(self):
        self.show_confirmation = not self.show_confirmation

    async def submit(self, form_data: dict[str, Any]):
        if self.is_saving:
            return
        password = str(form_data.get("password") or "")
        confirmation = str(form_data.get("confirm_password") or "")
        self.error_message = ""
        if not password:
            self.error_message = "Informe a nova senha."
            return
        if password != confirmation:
            self.error_message = "A confirmação da senha não confere."
            return
        if len(password) < 8 or not any(c.isascii() and c.isalpha() for c in password) or not any(c.isascii() and c.isdigit() for c in password):
            self.error_message = "A senha deve ter ao menos 8 caracteres, uma letra e um número."
            return
        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        if not token:
            yield rx.redirect("/")
            return
        self.is_saving = True
        yield
        try:
            await auth_client.change_initial_password(token, password, confirmation)
            yield AuthState.complete_password_change
        except XanoAuthError:
            yield rx.redirect("/")
        except XanoRequestError as exc:
            self.error_message = (
                "Não há troca de senha pendente para esta conta."
                if exc.error_code == "PASSWORD_CHANGE_NOT_REQUIRED"
                else "Não foi possível alterar a senha. Confira os requisitos e tente novamente."
            )
        except XanoError:
            self.error_message = "Não foi possível alterar a senha. Tente novamente."
        except Exception:
            logger.exception("Initial password change failed")
            self.error_message = "Não foi possível alterar a senha. Tente novamente."
        finally:
            self.is_saving = False


def _password_field(label: str, name: str, visible: Any, toggle: Any) -> rx.Component:
    return rx.vstack(
        rx.text(label, weight="medium"),
        rx.hstack(
            rx.input(name=name, type=rx.cond(visible, "text", "password"), auto_complete=False, disabled=InitialPasswordState.is_saving, width="100%"),
            rx.button(
                rx.cond(visible, rx.icon("eye_off"), rx.icon("eye")),
                type="button", variant="ghost", on_click=toggle,
                aria_label="Mostrar ou ocultar senha", disabled=InitialPasswordState.is_saving,
            ),
            width="100%", align="center",
        ),
        width="100%", align="stretch", spacing="2",
    )


def alterar_senha() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("NexStock", size="7", color="#2563EB"),
            rx.heading("Alteração de senha", size="6"),
            rx.text("Por segurança, você precisa definir uma nova senha antes de continuar.", color="#64748b"),
            rx.form(
                rx.vstack(
                    _password_field("Nova senha", "password", InitialPasswordState.show_password, InitialPasswordState.toggle_password),
                    _password_field("Confirmar nova senha", "confirm_password", InitialPasswordState.show_confirmation, InitialPasswordState.toggle_confirmation),
                    rx.cond(InitialPasswordState.error_message != "", rx.text(InitialPasswordState.error_message, color="#b91c1c")),
                    rx.button("Alterar senha", type="submit", width="100%", disabled=InitialPasswordState.is_saving, loading=InitialPasswordState.is_saving),
                    width="100%", align="stretch", spacing="4",
                ),
                on_submit=InitialPasswordState.submit, width="100%",
            ),
            rx.button("Sair", on_click=AuthState.logout, variant="ghost"),
            width="100%", max_width="28rem", padding="2rem", background="white",
            border="1px solid #e2e8f0", border_radius="1rem", align="stretch", spacing="5",
        ),
        width="100%", min_height="100vh", padding="1rem", background="#f8fafc",
    )
