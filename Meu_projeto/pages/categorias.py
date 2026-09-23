import reflex as rx
from ..components.layout import page, mock_table, section


def categorias() -> rx.Component:
    return page(
        "Categorias",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Nome da categoria..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Nova categoria"),
                width="100%",
            ),
            section(
                "Categorias cadastradas",
                mock_table(
                    ["ID", "Nome", "Produtos", "Status"],
                    [
                        ["1", "Alimentos", "38", "Ativa"],
                        ["2", "Bebidas", "21", "Ativa"],
                        ["3", "Materiais de limpeza", "17", "Ativa"],
                        ["4", "Eletrônicos", "12", "Ativa"],
                        ["5", "Materiais de escritório", "40", "Ativa"],
                    ],
                ),
            ),
        ),
    )
