import reflex as rx

from .components.theme import APP_GLOBAL_STYLE
from .pages.login import login
from .pages.alterar_senha import alterar_senha
from .pages.account_password import alterar_senha_conta
from .pages.dashboard import DashboardState, dashboard
from .pages.produtos import ProductsState, produtos, novo_produto, editar_produto
from .pages.categorias import CategoryState, categorias
from .pages.fornecedores import SupplierState, fornecedores
from .pages.estoque import StockState, estoque
from .pages.movimentacoes import EntryState, ExitState, entrada, saida
from .pages.usuarios import UserState, usuarios
from .pages.perfis import PermissionState, perfis
from .pages.relatorios import ReportState, relatorios
from .pages.reposicao import ReplenishmentState, reposicao
from .pages.compras import PurchaseManagementState, compras, compra_detalhe
from .pages.auditoria import AuditState, auditoria
from .state import AuthState


app = rx.App(
    html_lang="pt-BR",
    style=APP_GLOBAL_STYLE,
)

# Rota pública — redireciona para /dashboard se já autenticado (Task 5.5)
app.add_page(login, route="/", title="Login | NexStock", on_load=AuthState.check_already_logged_in)
app.add_page(alterar_senha, route="/alterar-senha", title="Alteração de senha | NexStock", on_load=AuthState.require_auth)
app.add_page(alterar_senha_conta, route="/conta/alterar-senha", title="Alterar senha | NexStock", on_load=AuthState.require_auth)

# Rotas protegidas — requerem sessão ativa (Task 6.3)
app.add_page(dashboard, route="/dashboard", title="Dashboard | NexStock", on_load=DashboardState.load_page)
app.add_page(editar_produto, route="/produtos/[product_route_id]/editar", title="Editar produto | NexStock", on_load=ProductsState.load_edit_page)
app.add_page(produtos, route="/produtos", title="Produtos | NexStock", on_load=ProductsState.load_page)
app.add_page(novo_produto, route="/produtos/novo", title="Novo produto | NexStock", on_load=ProductsState.load_create_page)
app.add_page(categorias, route="/categorias", title="Categorias | NexStock", on_load=CategoryState.load_page)
app.add_page(fornecedores, route="/fornecedores", title="Fornecedores | NexStock", on_load=SupplierState.load_page)
app.add_page(estoque, route="/estoque", title="Estoque | NexStock", on_load=StockState.load_page)
app.add_page(auditoria, route="/auditoria", title="Auditoria | NexStock", on_load=AuditState.load_page)
app.add_page(entrada, route="/movimentacoes/entradas", title="Entrada | NexStock", on_load=EntryState.load_entry_page)
app.add_page(saida, route="/movimentacoes/saidas", title="Saída | NexStock", on_load=ExitState.load_exit_page)
app.add_page(usuarios, route="/usuarios", title="Usuários | NexStock", on_load=UserState.load_page)
app.add_page(perfis, route="/perfis", title="Perfis | NexStock", on_load=PermissionState.load_page)
app.add_page(relatorios, route="/relatorios", title="Relatórios | NexStock", on_load=ReportState.load_page)
app.add_page(
    reposicao,
    route="/reposicao",
    title="Reposição de Estoque | NexStock",
    on_load=ReplenishmentState.load_page,
)
app.add_page(compras, route="/compras", title="Compras solicitadas | NexStock", on_load=PurchaseManagementState.load_list)
app.add_page(compra_detalhe, route="/compras/[request_id]", title="Detalhes da solicitação | NexStock", on_load=PurchaseManagementState.load_detail)
