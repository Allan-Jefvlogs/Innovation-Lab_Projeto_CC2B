import reflex as rx
from ..components.layout import page, mock_table, section


def perfis() -> rx.Component:
    return page(
        "Perfis e permissões",
        rx.vstack(
            section(
                "Perfis cadastrados",
                mock_table(
                    ["Perfil", "Descrição", "Usuários", "Permissões"],
                    [
                        ["Administrador", "Acesso administrativo", "1", "Todas"],
                        ["Estoquista", "Operações de estoque", "2", "Produtos, estoque, entradas e saídas"],
                        ["Usuário de consulta", "Somente consulta", "1", "Dashboard, estoque e relatórios"],
                    ],
                ),
            ),
            section(
                "Matriz de permissões (mock)",
                mock_table(
                    ["Funcionalidade", "Administrador", "Estoquista", "Consulta"],
                    [
                        ["Dashboard", "Sim", "Sim", "Sim"],
                        ["Usuários", "Sim", "Não", "Não"],
                        ["Produtos", "Sim", "Sim", "Não"],
                        ["Categorias", "Sim", "Sim", "Não"],
                        ["Fornecedores", "Sim", "Sim", "Não"],
                        ["Estoque", "Sim", "Sim", "Sim"],
                        ["Entrada", "Sim", "Sim", "Não"],
                        ["Saída", "Sim", "Sim", "Não"],
                        ["Histórico", "Sim", "Sim", "Sim"],
                        ["Relatórios", "Sim", "Sim", "Sim"],
                    ],
                ),
            ),
        ),
    )
