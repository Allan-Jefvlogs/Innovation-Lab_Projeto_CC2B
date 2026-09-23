import reflex as rx
from ..components.layout import page, mock_table, section


def produtos() -> rx.Component:
    return page(
        "Produtos",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar por código ou nome...", width="350px"),
                rx.button("Buscar"),
                rx.spacer(),
                rx.link(rx.button("Novo produto"), href="/produtos/novo"),
                width="100%",
            ),
            section(
                "Produtos cadastrados",
                mock_table(
                    ["Código", "Nome", "Categoria", "Unidade", "Qtd.", "Mínimo", "Status"],
                    [
                        ["P001", "Arroz 5kg", "Alimentos", "UN", "50", "20", "Normal"],
                        ["P002", "Café 500g", "Alimentos", "UN", "6", "10", "Baixo"],
                        ["P003", "Detergente", "Limpeza", "UN", "30", "10", "Normal"],
                        ["P004", "Papel A4", "Escritório", "CX", "12", "20", "Baixo"],
                    ],
                ),
            ),
        ),
    )


def novo_produto() -> rx.Component:
    return page(
        "Novo produto",
        rx.vstack(
            section(
                "Dados do produto",
                rx.vstack(
                    rx.input(placeholder="Código"),
                    rx.input(placeholder="Nome"),
                    rx.text_area(placeholder="Descrição"),
                    rx.select(
                        ["Alimentos", "Bebidas", "Limpeza", "Eletrônicos", "Escritório"],
                        placeholder="Categoria",
                    ),
                    rx.select(["UN", "KG", "L", "CX", "PC"], placeholder="Unidade de medida"),
                    rx.input(placeholder="Estoque mínimo", type="number"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/produtos"),
                        rx.button("Salvar produto"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )
