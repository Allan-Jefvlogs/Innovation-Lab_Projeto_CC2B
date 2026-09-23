import reflex as rx

from .pages.login import login
from .pages.dashboard import dashboard
from .pages.produtos import produtos, novo_produto
from .pages.categorias import categorias
from .pages.fornecedores import fornecedores
from .pages.estoque import estoque
from .pages.movimentacoes import historico, entrada, saida
from .pages.usuarios import usuarios
from .pages.perfis import perfis
from .pages.relatorios import relatorios


app = rx.App()

app.add_page(login, route="/", title="Login | Estoque")
app.add_page(dashboard, route="/dashboard", title="Dashboard | Estoque")
app.add_page(produtos, route="/produtos", title="Produtos | Estoque")
app.add_page(novo_produto, route="/produtos/novo", title="Novo produto | Estoque")
app.add_page(categorias, route="/categorias", title="Categorias | Estoque")
app.add_page(fornecedores, route="/fornecedores", title="Fornecedores | Estoque")
app.add_page(estoque, route="/estoque", title="Estoque | Estoque")
app.add_page(historico, route="/movimentacoes", title="Histórico | Estoque")
app.add_page(entrada, route="/movimentacoes/entradas", title="Entrada | Estoque")
app.add_page(saida, route="/movimentacoes/saidas", title="Saída | Estoque")
app.add_page(usuarios, route="/usuarios", title="Usuários | Estoque")
app.add_page(perfis, route="/perfis", title="Perfis | Estoque")
app.add_page(relatorios, route="/relatorios", title="Relatórios | Estoque")
