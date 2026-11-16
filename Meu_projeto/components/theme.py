"""Tokens centrais da identidade visual NexStock."""

import reflex as rx


# Cores de marca fornecidas pelo grupo.
MINT = "#BEEADB"
SAGE = "#8DBAA6"
PEACH = "#F7C683"
PEACH_ROSE = "#F0CBB9"
TAUPE = "#9E8D85"

# Tons de apoio derivados da paleta para fundos, bordas e contraste de texto.
SAGE_DARK = "#527964"
TEXT_PRIMARY = "#3F4945"
TEXT_SECONDARY = "#596B62"
TEXT_MUTED = "#66766D"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#FAFBF9"
MINT_SOFT = "#E7F6EE"
PEACH_SOFT = "#FFF0D8"
PEACH_TINT = "#FFFCF7"
ROSE_SOFT = "#F8E7DF"
BORDER = "#DCE7DF"
BORDER_SOFT = "#E6ECE8"
TABLE_HEADER = "#F8FAF8"
NEUTRAL_STATUS_BACKGROUND = SURFACE_ALT
NEUTRAL_STATUS_TEXT = TEXT_SECONDARY
NEUTRAL_STATUS_BORDER = TAUPE
TOPBAR_SURFACE = "#EFF8F3"
NAV_ACTIVE_SURFACE = "#EDF8F2"
NAV_TEXT = "#F8FFFB"
PRIMARY_ACTION = "#6E9985"
PRIMARY_ACTION_HOVER = "#5E8875"
CHART_ENTRY = "#78A68F"
CHART_EXIT = "#EDC178"
FONT_FAMILY = 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
SECTION_SURFACES = {
    "mint": MINT_SOFT,
    "peach": PEACH_SOFT,
    "rose": ROSE_SOFT,
    "white": SURFACE,
}
SECTION_BANDS = {
    "mint": MINT,
    "peach": PEACH,
    "rose": PEACH_ROSE,
    "white": SURFACE_ALT,
}
SUCCESS_TEXT = "#315D49"
WARNING_TEXT = "#604A31"
ROSE_TEXT = "#725346"
ERROR_TEXT = "#A13131"
ERROR_SOFT = "#FCEBEC"

# Geometria compartilhada do shell e dos painéis do Dashboard.
SIDEBAR_WIDTH = "252px"
TOPBAR_HEIGHT = "78px"
CONTENT_MAX_WIDTH = "1440px"
DESKTOP_CONTENT_PADDING = "38px"
DASHBOARD_GAP = "17px"
PANEL_RADIUS = "17px"


APP_GLOBAL_STYLE = {
    "body": {
        "background_color": SURFACE_ALT,
        "color": TEXT_PRIMARY,
        "font_family": FONT_FAMILY,
        "font_size": "14px",
        "line_height": "1.45",
    },
    ".radix-themes": {"--default-font-family": FONT_FAMILY},
    "::selection": {
        "background_color": MINT,
        "color": TEXT_PRIMARY,
    },
    rx.input: {
        "background_color": SURFACE,
        "border_color": BORDER,
        "color": TEXT_PRIMARY,
        "_focus": {
            "border_color": SAGE_DARK,
            "box_shadow": "0 0 0 2px rgba(141, 186, 166, 0.28)",
        },
    },
    rx.text_area: {
        "background_color": SURFACE,
        "border_color": BORDER,
        "color": TEXT_PRIMARY,
        "_focus": {
            "border_color": SAGE_DARK,
            "box_shadow": "0 0 0 2px rgba(141, 186, 166, 0.28)",
        },
    },
    rx.button: {
        "border_radius": "0.6rem",
        "transition": "background-color 150ms ease, border-color 150ms ease, color 150ms ease",
    },
    # Ações da marca; variantes explícitas de perigo/aviso mantêm suas cores.
    ".rt-Button.rt-variant-solid:not([data-accent-color]), .rt-Button.rt-variant-solid[data-accent-color='jade']": {
        "background_color": PRIMARY_ACTION,
        "color": SURFACE,
        "&:hover:not(:disabled)": {"background_color": PRIMARY_ACTION_HOVER},
        "&:focus-visible": {
            "outline": f"2px solid {SAGE_DARK}",
            "outline_offset": "2px",
        },
        "&:disabled": {
            "background_color": BORDER_SOFT,
            "color": TEXT_MUTED,
        },
    },
    rx.heading: {"color": TEXT_PRIMARY},
    rx.link: {"color": TEXT_SECONDARY},
    rx.divider: {"color": BORDER},
}
