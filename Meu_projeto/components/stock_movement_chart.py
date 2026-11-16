"""Gráfico de linhas para contagens reais, mantendo a identidade visual."""

import reflex as rx

from .theme import BORDER_SOFT, CHART_ENTRY, CHART_EXIT, PEACH, SAGE, SURFACE, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY


# A referência usa 204 px de área de desenho, além da faixa dos rótulos.
CHART_HEIGHT = 228


def _legend_item(label: str, color: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background=color,
            aria_hidden=True,
        ),
        rx.text(label, font_size="10px", color=TEXT_MUTED),
        gap="6px",
        align="center",
    )


def stock_movement_chart(
    data: list[dict[str, str | int]] | rx.Var,
    *,
    status_message: str = "",
    period: str | rx.Var = "7d",
    on_period_change=None,
    loading: bool | rx.Var = False,
    enabled: bool | rx.Var = True,
) -> rx.Component:
    """Recebe a série por parâmetro para permitir futura integração sem refazer o layout."""
    is_empty = len(data) == 0 if isinstance(data, list) else data.length() == 0
    return rx.vstack(
        rx.flex(
            rx.vstack(
                rx.heading("Movimentação do estoque", font_size="15px", font_weight="650", letter_spacing="-0.2px", color=TEXT_PRIMARY),
                rx.text(
                    rx.cond(period == "12m", "Número de movimentações por mês", "Número de movimentações por dia"),
                    font_size="11px",
                    color=TEXT_MUTED,
                    margin_top="4px",
                ),
                rx.cond(
                    (data.length() > 0 if not isinstance(data, list) else len(data) > 0) & (status_message != ""),
                    rx.text(status_message, font_size="10px", color=TEXT_MUTED, role="status"),
                    rx.fragment(),
                ),
                align="start",
                spacing="0",
            ),
            rx.hstack(
                rx.hstack(
                    *[
                        rx.button(
                            label,
                            on_click=on_period_change(value) if on_period_change is not None else None,
                            variant=rx.cond(period == value, "solid", "soft"),
                            background=rx.cond(period == value, SAGE, SURFACE),
                            color=TEXT_PRIMARY, border=f"1px solid {BORDER_SOFT}",
                            border_radius="8px", size="1", padding="4px 9px",
                            aria_pressed=period == value,
                            disabled=rx.cond(enabled, loading, True),
                        )
                        for value, label in (("7d", "7 dias"), ("30d", "30 dias"), ("12m", "12 meses"))
                    ],
                    gap="4px", align="center", flex_shrink="0",
                    role="group", aria_label="Período do gráfico",
                ),
                _legend_item("Entradas", SAGE),
                _legend_item("Saídas", PEACH),
                gap="16px",
                align="center",
                wrap="wrap",
                aria_label="Legenda: entradas em sálvia e saídas em amarelo pêssego",
            ),
            width="100%",
            justify="between",
            align="center",
            wrap="wrap",
            gap="12px",
        ),
        rx.cond(
            is_empty,
            rx.center(
                rx.text(
                    rx.cond(status_message != "", status_message, "Nenhuma movimentação no período."),
                    font_size="12px",
                    color=TEXT_MUTED,
                ),
                height=f"{CHART_HEIGHT}px",
                width="100%",
            ),
            rx.box(
            rx.recharts.line_chart(
                rx.recharts.cartesian_grid(
                    stroke="#EEF2EF",
                    vertical=False,
                ),
                rx.recharts.x_axis(
                    data_key="dia",
                    axis_line=False,
                    tick_line=False,
                    tick={"fill": TEXT_MUTED, "fontSize": 10},
                    interval="preserveStartEnd",
                    min_tick_gap=rx.cond(period == "30d", 20, 8),
                    height=24,
                    padding={"left": 0, "right": 0},
                ),
                rx.recharts.y_axis(
                    axis_line=False,
                    tick_line=False,
                    hide=True,
                    allow_decimals=False,
                    tick_count=5,
                ),
                rx.recharts.graphing_tooltip(
                    content_style={
                        "background": SURFACE,
                        "border": f"1px solid {BORDER_SOFT}",
                        "borderRadius": "10px",
                        "fontSize": "12px",
                    },
                    item_style={"color": TEXT_SECONDARY},
                    label_style={"color": TEXT_MUTED},
                    cursor={"stroke": BORDER_SOFT, "strokeWidth": 1},
                    is_animation_active=False,
                ),
                rx.recharts.line(
                    data_key="entradas",
                    name="Entradas",
                    type_="monotone",
                    stroke=CHART_ENTRY,
                    stroke_width=3,
                    dot=False,
                    active_dot={"r": 5, "fill": SURFACE, "strokeWidth": 3},
                    is_animation_active=False,
                ),
                rx.recharts.line(
                    data_key="saidas",
                    name="Saídas",
                    type_="monotone",
                    stroke=CHART_EXIT,
                    stroke_width=3,
                    dot=False,
                    active_dot={"r": 5, "fill": SURFACE, "strokeWidth": 3},
                    is_animation_active=False,
                ),
                data=data,
                width="100%",
                height=CHART_HEIGHT,
                min_width=0,
                margin={"top": 0, "right": 4, "left": 4, "bottom": 0},
                custom_attrs={"accessibilityLayer": True},
            ),
            width="100%",
            min_width="0",
            height=f"{CHART_HEIGHT}px",
            min_height=f"{CHART_HEIGHT}px",
            role="group",
            aria_label="Gráfico de linhas de entradas e saídas no período selecionado.",
            ),
        ),
        width="100%",
        min_width="0",
        align="stretch",
        gap="15px",
    )
