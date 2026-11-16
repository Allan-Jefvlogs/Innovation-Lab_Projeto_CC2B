"""Seletor pesquisável local para relacionamentos carregados do backend."""

import unicodedata
from typing import Any

import reflex as rx

from .theme import BORDER_SOFT, SURFACE, TEXT_MUTED, TEXT_PRIMARY


def normalize_search_text(value: object) -> str:
    """Normaliza para comparação parcial sem diferenciar caixa ou acentos."""
    decomposed = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def searchable_select(
    *,
    query: rx.Var[str],
    options: rx.Var[list[dict[str, str]]],
    is_open: rx.Var[bool],
    on_search: Any,
    on_open: Any,
    on_close: Any,
    on_escape: Any,
    on_select: Any,
    has_more: rx.Var[bool] | bool = False,
    is_loading_more: rx.Var[bool] | bool = False,
    on_load_more: Any = None,
    placeholder: str,
    placeholder_color: str | None = None,
    empty_message: str | rx.Var[str] = "Nenhuma opção encontrada.",
) -> rx.Component:
    """Combobox simples com filtro local e carregamento explícito de páginas."""

    def option_button(option: dict[str, str]) -> rx.Component:
        return rx.button(
            option["label"],
            on_click=on_select(option["id"]),
            on_mouse_down=rx.prevent_default,
            disabled=option.get("disabled", "false") == "true",
            variant="ghost",
            width="100%",
            justify="start",
            text_align="left",
        )

    more_options = (
        rx.cond(
            has_more,
            rx.button(
                rx.cond(is_loading_more, "Carregando...", "Carregar mais opções"),
                on_click=on_load_more,
                disabled=is_loading_more,
                variant="soft",
                width="100%",
            ),
            rx.fragment(),
        )
        if on_load_more is not None
        else rx.fragment()
    )

    return rx.box(
        rx.input(
            value=query,
            on_change=on_search,
            on_click=on_open,
            on_focus=on_open,
            on_blur=on_close.debounce(150),
            on_key_down=on_escape,
            placeholder=placeholder,
            color=(rx.cond(query == "", placeholder_color, TEXT_PRIMARY) if placeholder_color else None),
            auto_complete=False,
            role="combobox",
            aria_expanded=is_open,
            aria_autocomplete="list",
            width="100%",
        ),
        rx.cond(
            is_open,
            rx.vstack(
                rx.cond(
                    options.length() > 0,
                    rx.foreach(options, option_button),
                    rx.text(empty_message, color=TEXT_MUTED, padding="0.5rem"),
                ),
                more_options,
                width="100%",
                max_height="16rem",
                overflow_y="auto",
                align="stretch",
                spacing="1",
                padding="0.5rem",
                background=SURFACE,
                border=f"1px solid {BORDER_SOFT}",
                border_radius="0.5rem",
                box_shadow="0 8px 20px rgba(15, 23, 42, 0.12)",
                position="absolute",
                top="calc(100% + 4px)",
                left="0",
                z_index="1000",
            ),
            rx.fragment(),
        ),
        position="relative",
        width="100%",
    )
