import reflex as rx
from ..components.layout import page, mock_table, section


def fornecedores() -> rx.Component:
    return page(
        "Fornecedores",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar fornecedor..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Novo fornecedor"),
                width="100%",
            ),
            section(
                "Fornecedores cadastrados",
                mock_table(
                    ["ID", "Nome / Razão social", "Documento", "Contato", "Status"],
                    [
                        ["F001", "Distribuidora São Paulo", "12.345.678/0001-00", "(11) 99999-1111", "Ativo"],
                        ["F002", "Comercial Brasil Ltda.", "23.456.789/0001-11", "(11) 98888-2222", "Ativo"],
                        ["F003", "Office Supply", "34.567.890/0001-22", "(11) 97777-3333", "Ativo"],
                    ],
                ),
            ),
        ),
    )
