import reflex as rx
from ..components.layout import page, card, mock_table, section


def estoque() -> rx.Component:
    return page(
        "Estoque",
        rx.vstack(
            rx.hstack(
                card("Itens em estoque", "128"),
                card("Estoque normal", "124"),
                card("Abaixo do mínimo", "4"),
                card("Sem estoque", "0"),
                width="100%",
                wrap="wrap",
                spacing="4",
            ),
            section(
                "Situação atual",
                mock_table(
                    ["Código", "Produto", "Atual", "Mínimo", "Situação"],
                    [
                        ["P001", "Arroz 5kg", "50", "20", "Normal"],
                        ["P002", "Café 500g", "6", "10", "Abaixo do mínimo"],
                        ["P003", "Detergente", "30", "10", "Normal"],
                        ["P004", "Papel A4", "12", "20", "Abaixo do mínimo"],
                        ["P005", "Caneta azul", "5", "15", "Abaixo do mínimo"],
                    ],
                ),
            ),
        ),
    )
