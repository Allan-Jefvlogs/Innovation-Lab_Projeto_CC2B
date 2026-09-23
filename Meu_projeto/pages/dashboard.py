import reflex as rx
from ..components.layout import page, card, section, mock_table


def dashboard() -> rx.Component:
    return page(
        "Dashboard",
        rx.vstack(
            rx.text("Visão geral do estoque e das movimentações recentes.", color="#666"),
            rx.hstack(
                card("Produtos", "128", "4 abaixo do mínimo"),
                card("Categorias", "12"),
                card("Fornecedores", "24"),
                card("Estoque baixo", "4", "Atenção necessária"),
                width="100%",
                spacing="4",
                wrap="wrap",
            ),
            rx.hstack(
                section(
                    "Movimentações recentes",
                    mock_table(
                        ["Tipo", "Produto", "Quantidade", "Data", "Usuário"],
                        [
                            ["Entrada", "Arroz 5kg", "50", "22/09/2026 14:32", "Ana"],
                            ["Saída", "Café 500g", "8", "22/09/2026 13:10", "Carlos"],
                            ["Entrada", "Detergente", "30", "22/09/2026 11:45", "Ana"],
                        ],
                    ),
                ),
                section(
                    "Alertas de estoque",
                    rx.vstack(
                        rx.text("• Café 500g — atual: 6 / mínimo: 10"),
                        rx.text("• Açúcar 1kg — atual: 4 / mínimo: 8"),
                        rx.text("• Papel A4 — atual: 12 / mínimo: 20"),
                        rx.text("• Caneta azul — atual: 5 / mínimo: 15"),
                        align="start",
                    ),
                ),
                width="100%",
                align="start",
                spacing="4",
            ),
        ),
    )
