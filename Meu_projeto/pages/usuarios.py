import reflex as rx
from ..components.layout import page, mock_table, section


def usuarios() -> rx.Component:
    return page(
        "Usuários",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar por nome ou e-mail..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Novo usuário"),
                width="100%",
            ),
            section(
                "Usuários cadastrados",
                mock_table(
                    ["ID", "Nome", "E-mail", "Perfil", "Status"],
                    [
                        ["U001", "Ana Souza", "ana@empresa.com", "Administrador", "Ativo"],
                        ["U002", "Carlos Lima", "carlos@empresa.com", "Estoquista", "Ativo"],
                        ["U003", "Mariana Alves", "mariana@empresa.com", "Usuário de consulta", "Ativo"],
                        ["U004", "João Silva", "joao@empresa.com", "Estoquista", "Inativo"],
                    ],
                ),
            ),
        ),
    )
