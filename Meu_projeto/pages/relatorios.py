import reflex as rx
from ..components.layout import page, section, card, mock_table


def relatorios() -> rx.Component:
    return page(
        "Relatórios",
        rx.vstack(
            rx.text("Consultas gerenciais com dados fictícios para o protótipo.", color="#666"),
            rx.hstack(
                card("Entradas no período", "234", "01/09 a 22/09"),
                card("Saídas no período", "187", "01/09 a 22/09"),
                card("Produtos abaixo do mínimo", "4"),
                width="100%",
                wrap="wrap",
                spacing="4",
            ),
            section(
                "Movimentações por período",
                rx.hstack(
                    rx.input(type="date"),
                    rx.text("até"),
                    rx.input(type="date"),
                    rx.button("Gerar relatório"),
                ),
            ),
            section(
                "Resumo por produto",
                mock_table(
                    ["Produto", "Entradas", "Saídas", "Saldo atual"],
                    [
                        ["Arroz 5kg", "120", "70", "50"],
                        ["Café 500g", "45", "39", "6"],
                        ["Detergente", "80", "50", "30"],
                        ["Papel A4", "60", "48", "12"],
                    ],
                ),
            ),
            section(
                "Ações",
                rx.hstack(
                    rx.button("Visualizar relatório"),
                    rx.button("Exportar CSV"),
                    rx.button("Exportar PDF"),
                    spacing="3",
                ),
            ),
        ),
    )
