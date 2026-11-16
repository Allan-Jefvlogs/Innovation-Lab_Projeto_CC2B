"""Componentes compartilhados da identidade visual NexStock."""

import reflex as rx

from .theme import MINT, SAGE, SAGE_DARK, TEXT_PRIMARY


def brand_mark(scale: float = 1.0) -> rx.Component:
    """Marca geométrica usada no Login e na navegação lateral."""
    face_width = f"{42 * scale:g}px"
    face_height = f"{48 * scale:g}px"
    offset = f"{27 * scale:g}px"
    size = f"{96 * scale:g}px"

    def face(position: dict[str, str]) -> rx.Component:
        return rx.box(
            rx.box(
                position="absolute",
                top="0",
                left="0",
                width="100%",
                height="100%",
                background=MINT,
                clip_path="polygon(50% 0, 100% 25%, 50% 50%, 0 25%)",
            ),
            rx.box(
                position="absolute",
                top="0",
                left="0",
                width="100%",
                height="100%",
                background=SAGE,
                clip_path="polygon(0 25%, 50% 50%, 50% 100%, 0 75%)",
            ),
            rx.box(
                position="absolute",
                top="0",
                left="0",
                width="100%",
                height="100%",
                background=SAGE_DARK,
                clip_path="polygon(50% 50%, 100% 25%, 100% 75%, 50% 100%)",
            ),
            position="absolute",
            width=face_width,
            height=face_height,
            **position,
        )

    return rx.box(
        face({"left": "0", "bottom": "0"}),
        face({"left": offset, "bottom": "0"}),
        face({"right": "0", "top": "0"}),
        width=size,
        height=size,
        position="relative",
        flex_shrink="0",
    )


def brand_wordmark(font_size: str = "1.35rem", *, prefix: str = "Nex", color: str | None = None) -> rx.Component:
    """Wordmark NexStock com a mesma separação cromática do Login."""
    return rx.hstack(
        rx.text(prefix, color=color or TEXT_PRIMARY, font_size=font_size, font_weight="760", line_height="1.05"),
        rx.text("Stock", color=color or SAGE_DARK, font_size=font_size, font_weight="760", line_height="1.05"),
        spacing="0",
    )
