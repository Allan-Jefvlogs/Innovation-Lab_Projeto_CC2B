"""Feedbacks visuais reutilizáveis para operações confirmadas."""

import reflex as rx

from .theme import BORDER, MINT_SOFT, SUCCESS_TEXT, SURFACE, TEXT_MUTED, TEXT_PRIMARY


def success_dialog(*, is_open, title, message, on_open_change) -> rx.Component:
    """Modal acessível de sucesso controlado pelo estado da página."""
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
                rx.dialog.title(title, text_align="center", color=TEXT_PRIMARY),
                rx.dialog.description(message, text_align="center", color=TEXT_MUTED),
                rx.button(
                    "Fechar",
                    on_click=on_open_change(False),
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
        open=is_open,
        on_open_change=on_open_change,
    )
