"""Demonstração visual local de recuperação de senha, sem envio ou alteração real."""

import re

import reflex as rx

from ..components.brand import brand_mark, brand_wordmark
from ..components.theme import (
    BORDER,
    BORDER_SOFT,
    MINT_SOFT,
    SAGE,
    SAGE_DARK,
    SUCCESS_TEXT,
    SURFACE,
    SURFACE_ALT,
    TEXT_MUTED,
    TEXT_PRIMARY,
)


CONFIRMATION_MESSAGE = (
    "Se o e-mail informado estiver vinculado a uma conta, você receberá em breve "
    "as instruções para redefinir sua senha."
)
_EMAIL_FORMAT = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PasswordRecoveryDemoState(rx.State):
    """Estado apenas para apresentar a confirmação demonstrativa."""

    confirmation_open: bool = False
    error_message: str = ""

    def submit_demo(self, form_data: dict[str, str]):
        """Valida o formato durante a solicitação e descarta o e-mail imediatamente."""
        email_value = str(form_data.get("email") or "").strip()
        self.error_message = ""
        if not email_value or not _EMAIL_FORMAT.fullmatch(email_value):
            self.error_message = "Informe um e-mail válido."
            self.confirmation_open = False
            return
        # O valor só é usado na validação desta chamada e não é guardado no State.
        del email_value
        self.confirmation_open = True

    def set_confirmation_open(self, is_open: bool):
        self.confirmation_open = is_open

    def acknowledge_and_return(self):
        self.confirmation_open = False
        self.error_message = ""
        return rx.redirect("/")


def _recovery_confirmation_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.center(
                    rx.icon(tag="circle-check", size=34, color=SUCCESS_TEXT),
                    width="62px",
                    height="62px",
                    border_radius="50%",
                    background=MINT_SOFT,
                    aria_hidden=True,
                ),
                rx.dialog.title(
                    "Solicitação recebida!",
                    text_align="center",
                    color=TEXT_PRIMARY,
                ),
                rx.dialog.description(
                    CONFIRMATION_MESSAGE,
                    text_align="center",
                    color=TEXT_MUTED,
                ),
                rx.button(
                    "Entendi",
                    on_click=PasswordRecoveryDemoState.acknowledge_and_return,
                    width="fit-content",
                    min_width="96px",
                    align_self="center",
                    auto_focus=True,
                ),
                align="center",
                spacing="4",
                width="100%",
                padding="8px 4px 4px",
            ),
            max_width="min(440px, calc(100vw - 32px))",
            width="100%",
            padding="28px",
            border=f"1px solid {BORDER}",
            border_radius="18px",
            background=SURFACE,
            box_shadow="0 18px 55px rgba(46, 67, 56, 0.18)",
        ),
        open=PasswordRecoveryDemoState.confirmation_open,
        on_open_change=PasswordRecoveryDemoState.set_confirmation_open,
    )


def password_recovery_demo() -> rx.Component:
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
                            "Gestão inteligente de estoque",
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
                rx.vstack(
                    rx.heading("Recuperar senha", size="6", color=TEXT_PRIMARY),
                    rx.text(
                        "Informe seu e-mail para receber as instruções de redefinição de senha.",
                        color=TEXT_MUTED,
                        text_align="center",
                    ),
                    rx.form(
                        rx.vstack(
                            rx.text("E-mail", weight="medium", color=TEXT_PRIMARY),
                            rx.input(
                                type="email",
                                name="email",
                                placeholder="seu@email.com",
                                auto_complete="email",
                                aria_label="E-mail",
                                required=True,
                                width="100%",
                                height="48px",
                            ),
                            align="stretch",
                            spacing="2",
                            width="100%",
                        ),
                        rx.cond(
                            PasswordRecoveryDemoState.error_message != "",
                            rx.callout(
                                PasswordRecoveryDemoState.error_message,
                                icon="triangle_alert",
                                color_scheme="ruby",
                                role="alert",
                                width="100%",
                            ),
                        ),
                        rx.button(
                            "Solicitar recuperação",
                            type="submit",
                            margin_top="16px",
                            width="100%",
                            height="48px",
                            color=TEXT_PRIMARY,
                            background=SAGE,
                            border_radius="10px",
                            font_weight="600",
                            cursor="pointer",
                            _hover={"background": SAGE_DARK, "color": SURFACE},
                        ),
                        on_submit=PasswordRecoveryDemoState.submit_demo,
                        width="100%",
                    ),
                    rx.link(
                        "Voltar ao login",
                        href="/",
                        color=SAGE_DARK,
                        font_weight="600",
                    ),
                    align="stretch",
                    spacing="4",
                    width="100%",
                ),
                _recovery_confirmation_dialog(),
                width="100%",
                max_width="680px",
                padding="clamp(1.5rem, 5vw, 3rem)",
                background=SURFACE,
                border=f"1px solid {BORDER_SOFT}",
                border_radius="17px",
                box_shadow="0 24px 72px rgba(15, 23, 42, 0.09)",
                spacing="8",
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
