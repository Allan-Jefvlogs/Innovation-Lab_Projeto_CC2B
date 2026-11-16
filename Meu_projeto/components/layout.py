from typing import Any

import reflex as rx

from .theme import (
    BORDER,
    BORDER_SOFT,
    CONTENT_MAX_WIDTH,
    DESKTOP_CONTENT_PADDING,
    MINT,
    MINT_SOFT,
    NAV_ACTIVE_SURFACE,
    NAV_TEXT,
    PEACH_ROSE,
    ROSE_SOFT,
    SAGE,
    SAGE_DARK,
    SECTION_BANDS,
    SECTION_SURFACES,
    SIDEBAR_WIDTH,
    SURFACE,
    SURFACE_ALT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TOPBAR_HEIGHT,
    TOPBAR_SURFACE,
    PANEL_RADIUS,
)

from .brand import brand_mark, brand_wordmark
from ..state import AuthState
from ..state.dashboard_notifications import DashboardNotificationsState


def _notification_item(item: dict[str, Any]) -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.vstack(
                rx.text(item["descricao"], font_size="13px", color=TEXT_PRIMARY, overflow_wrap="anywhere"),
                rx.text("Solicitação #", item["purchase_request_id"], " · ", item["data_formatada"], font_size="11px", color=TEXT_MUTED, overflow_wrap="anywhere"),
                align="start", spacing="1", min_width="0", width="100%",
            ),
            variant="ghost", padding="0", margin="0", height="auto", flex="1", min_width="0",
            text_align="left", white_space="normal", cursor="pointer", font_weight="400",
            _hover={"background": "transparent", "text_decoration": "underline"},
            _focus_visible={"outline": f"2px solid {SAGE}", "outline_offset": "3px"},
            aria_label=f"Abrir detalhes da solicitação #{item['purchase_request_id']}",
            on_click=DashboardNotificationsState.open_notification(item["history_id"]).stop_propagation,
        ),
        rx.cond(
            item["lida"],
            rx.text("Lida", font_size="11px", color=TEXT_MUTED, flex_shrink="0"),
            rx.button("Marcar como lida", size="1", variant="soft", padding="4px 8px", flex_shrink="0", on_click=DashboardNotificationsState.mark_read(item["history_id"]).stop_propagation, disabled=DashboardNotificationsState.loading),
        ),
        on_click=DashboardNotificationsState.open_notification(item["history_id"]),
        cursor="pointer", _hover={"background": SURFACE_ALT}, border_radius="6px",
        align="center", width="100%", min_width="0", wrap="wrap", gap="8px", padding="10px 0", border_bottom=f"1px solid {BORDER_SOFT}",
    )


MENU_LINKS = [
    ("Dashboard", "/dashboard", None, False),
    ("Produtos", "/produtos", "product.read", False),
    ("Categorias", "/categorias", "category.read", False),
    ("Fornecedores", "/fornecedores", "supplier.read", False),
    ("Estoque", "/estoque", "stock.read", False),
    ("Entradas", "/movimentacoes/entradas", "stock.entry", False),
    ("Saídas", "/movimentacoes/saidas", "stock.exit", False),
    ("Auditoria", "/auditoria", None, True),
    ("Relatórios", "/relatorios", "report.read", False),
    ("Usuários", "/usuarios", None, True),
    ("Perfis e permissões", "/perfis", None, True),
]

PURCHASE_MENU_LINKS = [("Compras solicitadas", "/compras", "purchase_request.read", False)]

MENU_ICONS = {
    "Compras solicitadas": "shopping-cart",
    "Dashboard": "home",
    "Produtos": "package",
    "Categorias": "tag",
    "Fornecedores": "truck",
    "Estoque": "boxes",
    "Entradas": "arrow-down",
    "Saídas": "arrow-up",
    "Auditoria": "clipboard",
    "Relatórios": "chart-bar",
    "Usuários": "users",
    "Perfis e permissões": "shield",
}

PERMISSION_VISIBILITY = {
    "purchase_request.read": AuthState.can_read_purchase_requests,
    "purchase_request.manage": AuthState.can_manage_purchase_requests,
    "product.read": AuthState.can_read_products,
    "category.read": AuthState.can_read_categories,
    "supplier.read": AuthState.can_read_suppliers,
    "stock.read": AuthState.can_read_stock,
    "stock.entry": AuthState.can_stock_entry,
    "stock.exit": AuthState.can_stock_exit,
    "movement.read": AuthState.can_read_movements,
    "report.read": AuthState.can_read_reports,
}


def nav_item(label: str, href: str) -> rx.Component:
    is_active = (AuthState.router.url.path == href) | AuthState.router.url.path.startswith(f"{href}/")
    return rx.link(
        rx.hstack(
            rx.icon(tag=MENU_ICONS[label], size=18),
            rx.text("Painel" if label == "Dashboard" else label, font_size="14px"),
            align="center",
            gap="12px",
            width="100%",
        ),
        href=href,
        width="100%",
        padding="11px 13px",
        border_radius="12px",
        color=rx.cond(is_active, SAGE_DARK, NAV_TEXT),
        background=rx.cond(is_active, NAV_ACTIVE_SURFACE, "transparent"),
        box_shadow=rx.cond(is_active, "0 5px 14px #608b7833", "none"),
        font_weight=rx.cond(is_active, "700", "560"),
        aria_current=rx.cond(is_active, "page", "false"),
        text_decoration="none",
        transition="background-color 180ms ease",
        _hover={"background": rx.cond(is_active, NAV_ACTIVE_SURFACE, "rgba(255,255,255,0.15)")},
    )


def _menu_group(title: str, links: list[tuple], *, mobile: bool) -> rx.Component:
    return rx.vstack(
        rx.text(title, text_transform="uppercase", font_size="10px", weight="bold", letter_spacing="1.3px", color=NAV_TEXT, opacity="0.75", padding="0 12px 8px"),
        rx.grid(
            *[
                rx.cond(
                    AuthState.is_administrator
                    if admin_only
                    else (AuthState.is_administrator | PERMISSION_VISIBILITY[permission])
                    if permission
                    else True,
                    rx.dialog.close(nav_item(label, href)) if mobile else nav_item(label, href),
                    rx.fragment(),
                )
                for label, href, permission, admin_only in links
            ],
            width="100%",
            grid_template_columns="minmax(0, 1fr)",
            gap="6px",
        ),
        width="100%",
        spacing="0",
        align="stretch",
    )


def menu_items(*, mobile: bool = False) -> rx.Component:
    administration = {"Auditoria", "Relatórios", "Usuários", "Perfis e permissões"}
    regular_menu = rx.vstack(
        _menu_group("Menu principal", [link for link in MENU_LINKS if link[0] not in administration], mobile=mobile),
        rx.cond(
            AuthState.can_read_purchase_requests,
            _menu_group("Compras", PURCHASE_MENU_LINKS, mobile=mobile),
            rx.fragment(),
        ),
        rx.cond(
            AuthState.is_administrator | AuthState.can_read_reports,
            _menu_group("Administração", [link for link in MENU_LINKS if link[0] in administration], mobile=mobile),
            rx.fragment(),
        ),
        width="100%",
        align="stretch",
        gap="28px",
    )
    return rx.cond(
        AuthState.inventory_profile_code == "compras",
        _menu_group("Compras", PURCHASE_MENU_LINKS, mobile=mobile),
        regular_menu,
    )


def _user_identity(*, on_sage: bool = False) -> rx.Component:
    return rx.hstack(
        rx.center(
            rx.text(AuthState.user_name[:1].upper(), font_size="13px", weight="bold", color="#705D54"),
            width="34px",
            height="34px",
            border_radius="50%",
            background=PEACH_ROSE,
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(AuthState.user_name, weight="bold", font_size="12px", color=NAV_TEXT if on_sage else TEXT_PRIMARY),
            rx.text(AuthState.profile_name, font_size="11px", color=NAV_TEXT if on_sage else TEXT_MUTED, opacity="0.82" if on_sage else "1"),
            align="start",
            spacing="0",
            display=rx.breakpoints({"0px": "none", "701px": "flex"}) if not on_sage else "flex",
        ),
        gap="10px",
        align="center",
    )


def sidebar(*, mobile: bool = False) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(brand_mark(scale=0.25), width="38px", height="38px", border_radius="13px", background="#E9F7F0", flex_shrink="0"),
                rx.vstack(
                    brand_wordmark("20px", prefix="Next", color=SURFACE),
                    rx.text("Gestão inteligente de estoque", font_size="9px", color=SURFACE, opacity="0.78", letter_spacing="1.3px", text_transform="uppercase", line_height="1.4"),
                    align="start",
                    spacing="1",
                    min_width="0",
                ),
                align="center",
                gap="12px",
                width="100%",
                padding="1px 10px",
            ),
            menu_items(mobile=mobile),
            rx.spacer(),
            rx.vstack(
                rx.button(
                    rx.icon(tag="log-out", size=16),
                    "Sair",
                    on_click=AuthState.logout,
                    width="100%",
                    variant="ghost",
                    color=NAV_TEXT,
                    _hover={"background": "rgba(255,255,255,0.15)"},
                    cursor="pointer",
                    height="36px",
                ),
                rx.box(_user_identity(on_sage=True), width="100%", padding="13px 9px 0", border_top="1px solid #ffffff55"),
                width="100%",
                align="stretch",
                spacing="2",
            ),
            width="100%",
            min_height="100%",
            align="stretch",
            gap="28px",
        ),
        width="100%" if mobile else rx.breakpoints({"0px": "210px", "1051px": SIDEBAR_WIDTH}),
        min_width="0" if mobile else rx.breakpoints({"0px": "210px", "1051px": SIDEBAR_WIDTH}),
        flex_shrink="0",
        height="100dvh",
        position="relative" if mobile else "sticky",
        top="0",
        align_self="start",
        overflow_y="auto",
        display="block" if mobile else rx.breakpoints({"0px": "none", "701px": "block"}),
        padding="24px 17px 18px",
        background=SAGE,
    )


def _mobile_menu() -> rx.Component:
    return rx.box(
        rx.dialog.root(
            rx.dialog.trigger(rx.button(rx.icon(tag="menu", size=18), variant="ghost", color=TEXT_MUTED, aria_label="Abrir menu", padding="8px")),
            rx.dialog.content(
                rx.dialog.title("Navegação NextStock", position="absolute", width="1px", height="1px", overflow="hidden", clip_path="inset(50%)"),
                rx.dialog.description("Páginas disponíveis conforme suas permissões.", position="absolute", width="1px", height="1px", overflow="hidden", clip_path="inset(50%)"),
                sidebar(mobile=True),
                width=SIDEBAR_WIDTH,
                max_width="90vw",
                height="100dvh",
                max_height="100dvh",
                position="fixed",
                top="0",
                left="0",
                margin="0",
                padding="0",
                border_radius="0",
                transform="none",
            ),
        ),
        display=rx.breakpoints({"0px": "block", "701px": "none"}),
    )


def _topbar(title: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            _mobile_menu(),
            rx.text(
                "NextStock ",
                rx.text("/", as_="span", color="#A3B1A8"),
                " ",
                rx.text("Painel" if title == "Dashboard" else title, as_="span", weight="bold", color=TEXT_PRIMARY),
                color=TEXT_MUTED,
                font_size="13px",
                flex="1",
                min_width="0",
            ),
            rx.popover.root(
                rx.popover.trigger(
                    rx.button(
                        rx.icon(tag="bell", size=17, color=TEXT_MUTED),
                        rx.cond(
                            (DashboardNotificationsState.unread_count > 0)
                            & AuthState.can_read_purchase_requests
                            & (DashboardNotificationsState.owner_user_id == AuthState.user_id)
                            & (DashboardNotificationsState.global_scope == AuthState.can_manage_purchase_requests),
                            rx.text(
                                DashboardNotificationsState.badge_label,
                                position="absolute", top="2px", right="2px",
                                min_width="18px", height="18px", padding="0 3px",
                                box_sizing="border-box", border_radius="999px",
                                background="#B65353", color="white", border=f"2px solid {SURFACE}",
                                font_size="9px", font_weight="700", line_height="14px",
                                text_align="center", pointer_events="none", aria_hidden=True,
                            ), rx.fragment()),
                        on_click=DashboardNotificationsState.load_page,
                        aria_label=rx.cond(
                            (DashboardNotificationsState.unread_count > 0)
                            & AuthState.can_read_purchase_requests
                            & (DashboardNotificationsState.owner_user_id == AuthState.user_id)
                            & (DashboardNotificationsState.global_scope == AuthState.can_manage_purchase_requests),
                            "Abrir central de notificações, " + DashboardNotificationsState.unread_count.to_string() + " não lidas",
                            "Abrir central de notificações",
                        ),
                        width="40px",
                        height="40px",
                        padding="0",
                        position="relative",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        background=SURFACE,
                        border=f"1px solid {BORDER_SOFT}",
                        border_radius="11px",
                    )
                ),
                rx.popover.content(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Notificações", size="4"),
                            rx.cond(
                                (DashboardNotificationsState.unread_count != None)
                                & (DashboardNotificationsState.owner_user_id == AuthState.user_id)
                                & AuthState.can_read_purchase_requests
                                & (DashboardNotificationsState.global_scope == AuthState.can_manage_purchase_requests),
                                rx.text(DashboardNotificationsState.unread_count, " não lidas", font_size="12px", color=TEXT_MUTED),
                                rx.fragment(),
                            ),
                            justify="between", width="100%",
                        ),
                        rx.cond(DashboardNotificationsState.loading, rx.hstack(rx.spinner(size="1"), rx.text("Carregando notificações...", size="2"))),
                        rx.cond(
                            DashboardNotificationsState.error != "",
                            rx.hstack(
                                rx.text(DashboardNotificationsState.error, color=TEXT_MUTED, font_size="13px", flex="1", min_width="0", overflow_wrap="anywhere"),
                                rx.button("Tentar novamente", size="1", variant="ghost", on_click=DashboardNotificationsState.reload, disabled=DashboardNotificationsState.loading),
                                align="center", width="100%", min_width="0", wrap="wrap",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            DashboardNotificationsState.enabled
                            & (DashboardNotificationsState.owner_user_id == AuthState.user_id)
                            & (DashboardNotificationsState.items.length() == 0)
                            & (DashboardNotificationsState.error == ""),
                            rx.text("Nenhuma notificação para exibir.", color=TEXT_MUTED, font_size="13px"),
                            rx.fragment(),
                        ),
                        rx.box(
                            rx.cond(
                                (DashboardNotificationsState.owner_user_id == AuthState.user_id)
                                & AuthState.can_read_purchase_requests
                                & (DashboardNotificationsState.global_scope == AuthState.can_manage_purchase_requests),
                                rx.foreach(DashboardNotificationsState.items, _notification_item),
                                rx.fragment(),
                            ),
                            rx.cond(
                                DashboardNotificationsState.has_next & (DashboardNotificationsState.error == ""),
                                rx.button(
                                    "Carregar mais", size="1", variant="ghost",
                                    on_click=DashboardNotificationsState.load_more(DashboardNotificationsState.page),
                                    disabled=DashboardNotificationsState.loading,
                                    margin_top="8px", width="100%",
                                ),
                                rx.fragment(),
                            ),
                            id="notification-scroll-list",
                            custom_attrs={"data-page": DashboardNotificationsState.page},
                            on_scroll=rx.call_script(
                                "(() => { const el = document.getElementById('notification-scroll-list'); "
                                "return el ? {near_end: el.scrollTop > 0 && el.scrollHeight - el.scrollTop - el.clientHeight < 96, "
                                "page: Number(el.dataset.page)} : {}; })()",
                                callback=DashboardNotificationsState.on_list_scroll,
                            ).throttle(600),
                            role="region", aria_label="Lista de notificações", tab_index=0,
                            aria_busy=DashboardNotificationsState.loading,
                            max_height="min(48vh, 380px)", overflow_y="auto", overflow_x="hidden",
                            overscroll_behavior="contain", width="100%", min_width="0", min_height="0", flex="1 1 auto",
                        ),
                        width="100%", min_width="0",
                        max_height="min(65vh, 520px)",
                        overflow_y="hidden",
                        overflow_x="hidden",
                        align="stretch",
                        spacing="3",
                    ),
                    side="bottom",
                    align="end",
                    max_width="90vw",
                    width="min(420px, 86vw)", box_sizing="border-box", overflow_x="hidden",
                    background=SURFACE,
                ),
                on_open_change=DashboardNotificationsState.set_panel_open,
            ),
            rx.popover.root(
                rx.popover.trigger(
                    rx.button(_user_identity(), variant="ghost", padding="4px 8px", height="44px", border_radius="12px", aria_label="Menu do usuário"),
                ),
                rx.popover.content(
                    rx.vstack(
                        rx.text(AuthState.user_name, font_weight="bold", color=TEXT_PRIMARY),
                        rx.link("Alterar senha", href="/conta/alterar-senha", width="100%", padding="9px", border_radius="8px", _hover={"background": SURFACE_ALT}),
                        rx.button("Sair", on_click=AuthState.logout, variant="ghost", width="100%", justify_content="start"),
                        width="210px", align="stretch", spacing="2",
                    ),
                    side="bottom", align="end", background=SURFACE,
                ),
            ),
            width="100%",
            height=rx.breakpoints({"0px": "66px", "701px": TOPBAR_HEIGHT}),
            padding=rx.breakpoints({"0px": "0 14px", "701px": "0 24px", "1051px": f"0 {DESKTOP_CONTENT_PADDING}"}),
            align="center",
            gap="13px",
        ),
        width="100%",
        background=TOPBAR_SURFACE,
        border_bottom=f"1px solid {BORDER_SOFT}",
        role="banner",
        position="sticky",
        top="0",
        z_index="5",
    )


def page(title: str, content: rx.Component) -> rx.Component:
    page_content = rx.box(
        sidebar(),
        rx.box(
            _topbar(title),
            rx.box(
                *([rx.heading(title, font_size="27px", letter_spacing="-0.8px", margin_bottom="25px")] if title != "Dashboard" else []),
                content,
                width="100%",
                max_width=CONTENT_MAX_WIDTH,
                margin="0 auto",
                padding=rx.breakpoints({"0px": "24px 15px 36px", "701px": "28px 24px", "1051px": "34px 38px 50px"}),
                role="main",
            ),
            width="100%",
            flex="1",
            min_width="0",
            min_height="100vh",
            background=SURFACE_ALT,
        ),
        display="flex",
        flex_direction="row",
        width="100%",
    )
    return rx.cond(
        AuthState.session_is_valid,
        page_content,
        session_validation_panel(),
    )


def session_validation_panel() -> rx.Component:
    """Keep protected pages covered until the server validates the session."""
    can_retry = (AuthState.session_validation == "temporarily_unavailable") | (
        AuthState.session_validation == "forbidden"
    )
    return rx.center(
        rx.vstack(
            rx.heading("Sessão não validada", size="6"),
            rx.text(AuthState.session_status_message, role="status", text_align="center"),
            rx.cond(
                can_retry,
                rx.button(
                    "Tentar novamente",
                    on_click=AuthState.retry_session_validation,
                    disabled=AuthState.session_validation == "validating",
                ),
                rx.fragment(),
            ),
            rx.button("Voltar ao login", on_click=AuthState.logout, variant="ghost"),
            align="center",
            spacing="4",
            max_width="32rem",
            padding="2rem",
        ),
        width="100%",
        min_height="100vh",
        padding="1rem",
    )


def card(title: str, value: str, detail: str = "") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, color=TEXT_MUTED, size="2"),
            rx.heading(value, size="7"),
            rx.text(detail, color=TEXT_MUTED, size="2") if detail else rx.fragment(),
            align="start",
            spacing="1",
        ),
        border=f"1px solid {BORDER}",
        border_radius="0.85rem",
        padding="1.25rem",
        flex="1",
        min_width="180px",
        background=SURFACE,
        box_shadow="0 1px 4px rgba(41, 53, 46, 0.04)",
    )


def section(title: str, body: rx.Component, *, tone: str = "mint") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(title, font_size="15px", font_weight="650", letter_spacing="-0.2px", color=TEXT_PRIMARY),
            body,
            width="100%",
            align="stretch",
            gap="15px",
        ),
        border=f"1px solid {BORDER_SOFT}",
        border_radius=PANEL_RADIUS,
        padding=rx.breakpoints({"0px": "15px", "701px": "19px"}),
        width="100%",
        background=SURFACE,
        box_shadow="0 3px 12px rgba(45,65,54,0.025)",
    )


def mock_table(headers: list[str], rows: list[list[str]]) -> rx.Component:
    header = rx.hstack(
        *[
            rx.text(h, weight="bold", flex="1", min_width="120px")
            for h in headers
        ],
        width="100%",
        padding="0.75rem",
        background=MINT_SOFT,
        border_bottom=f"1px solid {BORDER}",
    )

    body = rx.vstack(
        *[
            rx.hstack(
                *[
                    rx.text(cell, flex="1", min_width="120px")
                    for cell in row
                ],
                width="100%",
                padding="0.75rem",
                border_bottom=f"1px solid {BORDER_SOFT}",
            )
            for row in rows
        ],
        width="100%",
        spacing="0",
    )

    return rx.box(
        header,
        body,
        width="100%",
        overflow_x="auto",
        border=f"1px solid {BORDER}",
        border_radius="0.4rem",
    )


def form_input(label: str, placeholder: str = "", value: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(label, weight="bold"),
        rx.input(value=value, placeholder=placeholder, width="100%"),
        width="100%",
        align="stretch",
        spacing="1",
    )
