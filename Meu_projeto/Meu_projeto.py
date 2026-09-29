import reflex as rx

from .pages.login import login
from .pages.dashboard import dashboard
from .pages.produtos import ProductsState, produtos, novo_produto, editar_produto
from .pages.categorias import categorias
from .pages.fornecedores import fornecedores
from .pages.estoque import estoque
from .pages.movimentacoes import historico, entrada, saida
from .pages.usuarios import usuarios
from .pages.perfis import perfis
from .pages.relatorios import relatorios
from .state import AuthState


app = rx.App()

# Rota pública — redireciona para /dashboard se já autenticado (Task 5.5)
app.add_page(login, route="/", title="Login | NexStock", on_load=AuthState.check_already_logged_in)

# Rotas protegidas — requerem sessão ativa (Task 6.3)
app.add_page(dashboard, route="/dashboard", title="Dashboard | NexStock", on_load=AuthState.require_auth)
app.add_page(editar_produto, route="/produtos/[product_route_id]/editar", title="Editar produto | NexStock", on_load=ProductsState.load_edit_page)
app.add_page(produtos, route="/produtos", title="Produtos | NexStock", on_load=ProductsState.load_page)
app.add_page(novo_produto, route="/produtos/novo", title="Novo produto | NexStock", on_load=ProductsState.load_create_page)
app.add_page(categorias, route="/categorias", title="Categorias | NexStock", on_load=AuthState.require_auth)
app.add_page(fornecedores, route="/fornecedores", title="Fornecedores | NexStock", on_load=AuthState.require_auth)
app.add_page(estoque, route="/estoque", title="Estoque | NexStock", on_load=AuthState.require_auth)
app.add_page(historico, route="/movimentacoes", title="Histórico | NexStock", on_load=AuthState.require_auth)
app.add_page(entrada, route="/movimentacoes/entradas", title="Entrada | NexStock", on_load=AuthState.require_auth)
app.add_page(saida, route="/movimentacoes/saidas", title="Saída | NexStock", on_load=AuthState.require_auth)
app.add_page(usuarios, route="/usuarios", title="Usuários | NexStock", on_load=AuthState.require_auth)
app.add_page(perfis, route="/perfis", title="Perfis | NexStock", on_load=AuthState.require_auth)
app.add_page(relatorios, route="/relatorios", title="Relatórios | NexStock", on_load=AuthState.require_auth)
