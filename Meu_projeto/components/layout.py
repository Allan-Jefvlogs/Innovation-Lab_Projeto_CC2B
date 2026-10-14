import reflex as rx

from ..state import AuthState


MENU_LINKS = [
    ("Dashboard", "/dashboard", None, False),
    ("Produtos", "/produtos", "product.read", False),
    ("Categorias", "/categorias", "category.read", False),
    ("Fornecedores", "/fornecedores", "supplier.read", False),
    ("Estoque", "/estoque", "stock.read", False),
    ("Entradas", "/movimentacoes/entradas", "stock.entry", False),
    ("Saídas", "/movimentacoes/saidas", "stock.exit", False),
    ("Histórico", "/movimentacoes", "movement.read", False),
    ("Relatórios", "/relatorios", "report.read", False),
    ("Usuários", "/usuarios", None, True),
    ("Perfis e permissões", "/perfis", None, True),
]

PERMISSION_VISIBILITY = {
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
    return rx.link(
        label,
        href=href,
        width="100%",
        padding="0.6rem 0.8rem",
        border_radius="0.4rem",
        _hover={"background": "#f1f1f1"},
    )

def menu_items() -> rx.Component:
    return rx.vstack(
        *[
            rx.cond(
                AuthState.is_administrator
                if admin_only
                else (AuthState.is_administrator | PERMISSION_VISIBILITY[permission])
                if permission
                else True,
                nav_item(label, href),
                rx.fragment(),
            )
            for label, href, permission, admin_only in MENU_LINKS
        ],
        width="100%",
        align="stretch",
        spacing="1",
    )

def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("NexStock", size="6"),
            rx.text("Sistema de Gerenciamento", size="2", color="#666"),
            rx.divider(),

            menu_items(),

            rx.spacer(),

            rx.button(
                "Sair",
                on_click=AuthState.logout,
                width="100%",
                variant="ghost",
                color_scheme="gray",
                cursor="pointer",
            ),

            width="100%",
            height="100%",
            align="stretch",
            spacing="3",
        ),
        width="250px",
        min_width="250px",
        min_height="100vh",
        padding="1.25rem",
        border_right="1px solid #ddd",
        background="#fafafa",
    )


def page(title: str, content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading(title, size="7"),
                    rx.spacer(),
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                AuthState.user_name,
                                weight="bold",
                                size="2",
                                text_align="right",
                            ),
                            rx.text(
                                AuthState.profile_name,
                                color="#666",
                                size="1",
                                text_align="right",
                            ),
                            align="end",
                            spacing="0",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                content,
                width="100%",
                align="stretch",
                spacing="5",
            ),
            padding="2rem",
            width="100%",
            min_height="100vh",
        ),
        width="100%",
        align="stretch",
        spacing="0",
    )


def card(title: str, value: str, detail: str = "") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, color="#666", size="2"),
            rx.heading(value, size="7"),
            rx.text(detail, color="#777", size="2") if detail else rx.fragment(),
            align="start",
            spacing="1",
        ),
        border="1px solid #ddd",
        border_radius="0.5rem",
        padding="1.25rem",
        flex="1",
        min_width="180px",
    )


def section(title: str, body: rx.Component) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(title, size="5"),
            rx.divider(),
            body,
            width="100%",
            align="stretch",
            spacing="3",
        ),
        border="1px solid #ddd",
        border_radius="0.5rem",
        padding="1.25rem",
        width="100%",
    )


def mock_table(headers: list[str], rows: list[list[str]]) -> rx.Component:
    header = rx.hstack(
        *[
            rx.text(h, weight="bold", flex="1", min_width="120px")
            for h in headers
        ],
        width="100%",
        padding="0.75rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
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
                border_bottom="1px solid #eee",
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
        border="1px solid #ddd",
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
