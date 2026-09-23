import reflex as rx
from ..components.layout import page, mock_table, section


def historico() -> rx.Component:
    return page(
        "Histórico de movimentações",
        rx.vstack(
            rx.hstack(
                rx.select(["Todos", "Entrada", "Saída"], placeholder="Tipo"),
                rx.input(placeholder="Produto"),
                rx.input(type="date"),
                rx.input(type="date"),
                rx.button("Filtrar"),
                width="100%",
                wrap="wrap",
            ),
            section(
                "Movimentações",
                mock_table(
                    ["ID", "Tipo", "Produto", "Qtd.", "Data/hora", "Usuário", "Motivo"],
                    [
                        ["MOV-104", "Entrada", "Arroz 5kg", "50", "22/09/2026 14:32", "Ana", "Compra"],
                        ["MOV-103", "Saída", "Café 500g", "8", "22/09/2026 13:10", "Carlos", "Consumo interno"],
                        ["MOV-102", "Entrada", "Detergente", "30", "22/09/2026 11:45", "Ana", "Compra"],
                        ["MOV-101", "Saída", "Papel A4", "5", "22/09/2026 09:20", "Carlos", "Uso administrativo"],
                    ],
                ),
            ),
        ),
    )


def entrada() -> rx.Component:
    return page(
        "Registrar entrada de estoque",
        rx.vstack(
            section(
                "Dados da entrada",
                rx.vstack(
                    rx.select(["Arroz 5kg", "Café 500g", "Detergente", "Papel A4"], placeholder="Produto"),
                    rx.input(placeholder="Quantidade", type="number"),
                    rx.select(
                        ["Distribuidora São Paulo", "Comercial Brasil Ltda.", "Office Supply"],
                        placeholder="Fornecedor",
                    ),
                    rx.input(type="date"),
                    rx.input(placeholder="Motivo", value="Compra"),
                    rx.text_area(placeholder="Observação"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button("Registrar entrada"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )


def saida() -> rx.Component:
    return page(
        "Registrar saída de estoque",
        rx.vstack(
            section(
                "Dados da saída",
                rx.vstack(
                    rx.select(["Arroz 5kg", "Café 500g", "Detergente", "Papel A4"], placeholder="Produto"),
                    rx.input(placeholder="Quantidade", type="number"),
                    rx.input(type="date"),
                    rx.select(
                        ["Consumo interno", "Perda", "Avaria", "Doação", "Outro"],
                        placeholder="Motivo",
                    ),
                    rx.text_area(placeholder="Observação"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button("Registrar saída"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )
