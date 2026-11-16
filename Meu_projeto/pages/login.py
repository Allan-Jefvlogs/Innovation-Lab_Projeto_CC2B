"""Página de Login integrada com autenticação real do Xano."""

import reflex as rx

from ..components.theme import BORDER_SOFT, MINT_SOFT, SAGE, SAGE_DARK, SURFACE, SURFACE_ALT, TEXT_MUTED, TEXT_PRIMARY
from ..components.brand import brand_mark, brand_wordmark
from ..state.auth import AuthState


class LoginState(rx.State):
    """Estado local efêmero para os campos do formulário de login."""

    email: str = ""
    password: str = ""
    password_visible: bool = False

    def set_email(self, value: str):
        """Atualiza o e-mail digitado e limpa erros anteriores."""
        self.email = value
        return AuthState.clear_error

    def set_password(self, value: str):
        """Atualiza a senha digitada e limpa erros anteriores."""
        self.password = value
        return AuthState.clear_error

    def toggle_password_visibility(self):
        """Alterna apenas a apresentação visual do campo de senha."""
        self.password_visible = not self.password_visible

    def handle_submit(self):
        """Dispara a autenticação através do AuthState."""
        return AuthState.login(self.email, self.password)


def login() -> rx.Component:
    """Renderiza a tela de login do Sistema de Gerenciamento de Estoque."""
    return rx.box(
        rx.box(
            position="absolute",
            top="-145px",
            right="-120px",
            width="390px",
            height="390px",
            border_radius="72px",
            background=MINT_SOFT,
            opacity="0.8",
            transform="rotate(45deg)",
            pointer_events="none",
        ),
        rx.box(
            position="absolute",
            left="-160px",
            bottom="-170px",
            width="420px",
            height="420px",
            border_radius="76px",
            background=MINT_SOFT,
            opacity="0.82",
            transform="rotate(45deg)",
            pointer_events="none",
        ),
        rx.center(
            rx.vstack(
                rx.hstack(
                    brand_mark(),
                    rx.vstack(
                        brand_wordmark("clamp(2.1rem, 5vw, 2.75rem)"),
                        rx.text(
                            "Gest\u00e3o inteligente de estoque",
                            color=TEXT_MUTED,
                            font_size="clamp(0.9rem, 2.5vw, 1.1rem)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    align="center",
                    spacing="5",
                    justify="center",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.vstack(
                            rx.heading(
                                "Login",
                                size="6",
                                color=TEXT_PRIMARY,
                                text_align="center",
                            ),
                            align="center",
                            spacing="1",
                            width="100%",
                        ),
                        rx.cond(
                            AuthState.error_message != "",
                            rx.callout(
                                AuthState.error_message,
                                icon="triangle_alert",
                                color_scheme="ruby",
                                role="alert",
                                width="100%",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            AuthState.password_change_notice != "",
                            rx.callout(AuthState.password_change_notice, icon="circle_check", color_scheme="jade", width="100%"),
                        ),
                        rx.cond(
                            (AuthState.session_validation == "temporarily_unavailable")
                            | (AuthState.session_validation == "forbidden"),
                            rx.vstack(
                                rx.text(AuthState.session_status_message, role="status"),
                                rx.button(
                                    "Tentar validar sessão novamente",
                                    type="button",
                                    on_click=AuthState.retry_session_validation,
                                    disabled=AuthState.session_validation == "validating",
                                ),
                                width="100%",
                                align="stretch",
                            ),
                            rx.fragment(),
                        ),
                        rx.form(
                            rx.vstack(
                                rx.vstack(
                                    rx.text(
                                        "E-mail",
                                        weight="medium",
                                        color=TEXT_PRIMARY,
                                    ),
                                    rx.hstack(
                                        rx.icon(
                                            tag="mail",
                                            size=19,
                                            color=TEXT_MUTED,
                                        ),
                                        rx.input(
                                            placeholder="seu@email.com",
                                            type="email",
                                            value=LoginState.email,
                                            on_change=LoginState.set_email,
                                            disabled=AuthState.is_loading,
                                            width="100%",
                                            height="100%",
                                            border="none",
                                            outline="none",
                                            box_shadow="none",
                                            padding="0",
                                            background="transparent",
                                        ),
                                        align="center",
                                        spacing="3",
                                        width="100%",
                                        height="58px",
                                        padding="0 1rem",
                                        border=f"1px solid {BORDER_SOFT}",
                                        border_radius="12px",
                                        background=SURFACE,
                                        transition="border-color 150ms ease, box-shadow 150ms ease",
                                        _focus_within={
                                            "border_color": SAGE_DARK,
                                            "box_shadow": "0 0 0 3px rgba(141, 186, 166, 0.28)",
                                        },
                                    ),
                                    align="stretch",
                                    spacing="2",
                                    width="100%",
                                ),
                                rx.vstack(
                                    rx.text(
                                        "Senha",
                                        weight="medium",
                                        color=TEXT_PRIMARY,
                                    ),
                                    rx.hstack(
                                        rx.icon(
                                            tag="lock_keyhole",
                                            size=19,
                                            color=TEXT_MUTED,
                                        ),
                                        rx.input(
                                            placeholder="Digite sua senha",
                                            type=rx.cond(
                                                LoginState.password_visible,
                                                "text",
                                                "password",
                                            ),
                                            value=LoginState.password,
                                            on_change=LoginState.set_password,
                                            disabled=AuthState.is_loading,
                                            width="100%",
                                            height="100%",
                                            border="none",
                                            outline="none",
                                            box_shadow="none",
                                            padding="0",
                                            background="transparent",
                                        ),
                                        rx.button(
                                            rx.cond(
                                                LoginState.password_visible,
                                                rx.icon(
                                                    tag="eye_off",
                                                    size=18,
                                                    color=TEXT_MUTED,
                                                ),
                                                rx.icon(
                                                    tag="eye",
                                                    size=18,
                                                    color=TEXT_MUTED,
                                                ),
                                            ),
                                            type="button",
                                            on_click=LoginState.toggle_password_visibility,
                                            aria_label="Mostrar ou ocultar senha",
                                            variant="ghost",
                                            width="32px",
                                            height="32px",
                                            padding="0",
                                            min_width="32px",
                                            color=TEXT_MUTED,
                                            cursor="pointer",
                                            _hover={"background": MINT_SOFT},
                                        ),
                                        align="center",
                                        spacing="3",
                                        width="100%",
                                        height="58px",
                                        padding="0 1rem",
                                        border=f"1px solid {BORDER_SOFT}",
                                        border_radius="12px",
                                        background=SURFACE,
                                        transition="border-color 150ms ease, box-shadow 150ms ease",
                                        _focus_within={
                                            "border_color": SAGE_DARK,
                                            "box_shadow": "0 0 0 3px rgba(141, 186, 166, 0.28)",
                                        },
                                    ),
                                    align="stretch",
                                    spacing="2",
                                    width="100%",
                                ),
                                rx.hstack(
                                    rx.checkbox(
                                        "Manter-me conectado",
                                        default_checked=True,
                                        size="2",
                                        color_scheme="jade",
                                    ),
                                    rx.link(
                                        "Esqueceu sua senha?",
                                        href="/recuperar-senha",
                                        color=SAGE_DARK,
                                        font_size="0.875rem",
                                        font_weight="600",
                                        _hover={"color": SAGE_DARK},
                                    ),
                                    align="center",
                                    justify="between",
                                    flex_wrap="wrap",
                                    column_gap="1rem",
                                    row_gap="0.5rem",
                                    width="100%",
                                ),
                                rx.button(
                                    rx.hstack(
                                        rx.text("Entrar", font_weight="600"),
                                        rx.icon(
                                            tag="arrow_right",
                                            size=20,
                                        ),
                                        align="center",
                                        justify="center",
                                        spacing="2",
                                        width="100%",
                                    ),
                                    type="submit",
                                    width="100%",
                                    height="56px",
                                    loading=AuthState.is_loading,
                                    disabled=AuthState.is_loading,
                                    color=TEXT_PRIMARY,
                                    background=SAGE,
                                    border_radius="10px",
                                    font_weight="600",
                                    cursor="pointer",
                                    transition="background-color 160ms ease",
                                    _hover={"background": SAGE_DARK, "color": SURFACE},
                                ),
                                width="100%",
                                align="stretch",
                                spacing="4",
                            ),
                            on_submit=LoginState.handle_submit,
                            width="100%",
                        ),
                        width="100%",
                        align="stretch",
                        spacing="5",
                    ),
                    width="100%",
                    max_width="680px",
                    padding="clamp(1.5rem, 5vw, 3rem)",
                    background=SURFACE,
                    border=f"1px solid {BORDER_SOFT}",
                    border_radius="17px",
                    box_shadow="0 24px 72px rgba(15, 23, 42, 0.09)",
                ),
                align="center",
                spacing="9",
                width="100%",
                max_width="720px",
            ),
            width="100%",
            min_height="100vh",
            padding="1rem",
            position="relative",
            z_index="1",
        ),
        width="100%",
        min_height="100vh",
        position="relative",
        overflow="hidden",
        background=SURFACE_ALT,
    )
