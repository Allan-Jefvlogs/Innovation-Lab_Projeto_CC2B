"""Estado global de autenticação e sessão do usuário."""

from typing import Any, Dict, Optional
import reflex as rx

from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoServerError,
    auth_client,
    is_user_inactive_error,
)


ROUTE_PERMISSION = {
    "/produtos": "product.read",
    "/categorias": "category.read",
    "/fornecedores": "supplier.read",
    "/estoque": "stock.read",
    "/movimentacoes": "movement.read",
    "/movimentacoes/entradas": "stock.entry",
    "/movimentacoes/saidas": "stock.exit",
    "/relatorios": "report.read",
}


def _required_route_permission(route_path: str) -> Optional[str]:
    """Resolve o grant exigido por uma rota operacional, incluindo subrotas."""
    path = route_path.rstrip("/") or "/"
    if path == "/produtos/novo":
        return "product.create"
    route_parts = path.strip("/").split("/")
    if len(route_parts) == 3 and route_parts[0] == "produtos" and route_parts[1].isdigit() and route_parts[2] == "editar":
        return "product.update"
    if path.startswith("/produtos/"):
        return "product.read"
    return ROUTE_PERMISSION.get(path)


class AuthState(rx.State):
    """Gerencia o ciclo de vida da autenticação, token persistente e perfil do usuário."""

    # Token JWT persistido reativamente no navegador via LocalStorage
    auth_token: str = rx.LocalStorage(name="auth_token")

    # Informações da identidade do usuário
    user_id: int = 0
    user_name: str = ""
    user_email: str = ""
    user_role: str = ""
    inventory_profile_id: Optional[int] = None
    inventory_profile_code: str = ""
    permission_codes: list[str] = []
    profile_name: str = ""
    must_change_password: bool = False
    password_change_notice: str = ""

    # Flags de controle de sessão e interface
    is_authenticated: bool = False
    is_loading: bool = False
    error_message: str = ""

    def clear_error(self):
        """Limpa a mensagem de erro da interface."""
        self.error_message = ""

    def _reset_user_data(self):
        """Reseta as variáveis do usuário em memória."""
        self.user_id = 0
        self.user_name = ""
        self.user_email = ""
        self.user_role = ""
        self.inventory_profile_id = None
        self.inventory_profile_code = ""
        self.permission_codes = []
        self.profile_name = ""
        self.must_change_password = False
        self.is_authenticated = False

    def _populate_user(self, data: Dict[str, Any]):
        """Preenche os dados do usuário e resolve o perfil de domínio."""
        self.user_id = int(data.get("id", 0))
        self.user_name = str(data.get("name", "")).strip()
        self.user_email = str(data.get("email", "")).strip()
        self.user_role = str(data.get("role", "")).strip()
        self.must_change_password = data.get("must_change_password") is True

        # Resolução do perfil de estoque
        raw_profile_id = data.get("inventory_profile_id")
        self.inventory_profile_id = int(raw_profile_id) if raw_profile_id is not None else None
        self.inventory_profile_code = str(data.get("inventory_profile_code") or "")
        raw_permission_codes = data.get("permission_codes")
        self.permission_codes = (
            [code for code in raw_permission_codes if isinstance(code, str)]
            if isinstance(raw_permission_codes, list)
            else []
        )

        pid = self.inventory_profile_id
        if self.inventory_profile_code == "administrator" or pid == 1 or self.user_role == "administrator":
            self.profile_name = "Líder"
        elif pid == 2 or self.user_role == "stockkeeper":
            self.profile_name = "Almoxarife"
        elif pid == 3 or self.user_role == "read_only":
            self.profile_name = "Auxiliar de almoxarifado"
        else:
            self.profile_name = "Sem perfil atribuído"

    def has_permission(self, permission_code: str) -> bool:
        """Usa os grants efetivos retornados pelo Xano para esta sessão."""
        return self.is_administrator or permission_code in self.permission_codes

    @rx.var
    def is_administrator(self) -> bool:
        return self.inventory_profile_code == "administrator"

    @rx.var
    def can_read_products(self) -> bool:
        return self.has_permission("product.read")

    @rx.var
    def can_read_categories(self) -> bool:
        return self.has_permission("category.read")

    @rx.var
    def can_read_suppliers(self) -> bool:
        return self.has_permission("supplier.read")

    @rx.var
    def can_read_stock(self) -> bool:
        return self.has_permission("stock.read")

    @rx.var
    def can_stock_entry(self) -> bool:
        return self.has_permission("stock.entry")

    @rx.var
    def can_stock_exit(self) -> bool:
        return self.has_permission("stock.exit")

    @rx.var
    def can_read_movements(self) -> bool:
        return self.has_permission("movement.read")

    @rx.var
    def can_read_reports(self) -> bool:
        return self.has_permission("report.read")

    async def restore_session(self) -> bool:
        """Restaura a sessão do usuário caso exista um token persistido.

        Returns:
            bool: True se a sessão for válida, False caso contrário.
        """
        token = self.auth_token
        if not token or not str(token).strip():
            self._reset_user_data()
            return False

        try:
            user_data = await auth_client.get_current_user(str(token).strip())
            self._populate_user(user_data)
            self.is_authenticated = True
            self.error_message = ""
            return True
        except XanoAuthError as exc:
            # Token expirado ou revogado
            self._reset_user_data()
            self.auth_token = ""
            self.error_message = (
                "Seu usuário está inativo. Entre em contato com o administrador."
                if is_user_inactive_error(exc)
                else ""
            )
            return False
        except (XanoConnectionError, XanoServerError):
            # Falha de conexão: mantém o token para tentar novamente depois
            self.error_message = "Não foi possível validar a sessão com o servidor."
            return False
        except Exception:
            self.error_message = "Erro inesperado ao verificar a sessão."
            return False

    async def login(self, email: str, password: str):
        """Autentica o usuário no Xano e inicializa a sessão.

        Args:
            email: E-mail informado pelo usuário.
            password: Senha em texto claro (não armazenada no estado).
        """
        self.is_loading = True
        self.error_message = ""
        self.password_change_notice = ""

        clean_email = email.strip() if email else ""
        if not clean_email or not password:
            self.error_message = "Por favor, preencha todos os campos."
            self.is_loading = False
            return

        try:
            # 1. Envia credenciais para o endpoint POST auth/login
            login_response = await auth_client.login(clean_email, password)
            token = str(login_response.get("authToken", "")).strip()

            if not token:
                raise XanoServerError("Token de autenticação não retornado pelo servidor.")

            # 2. Persiste o token no LocalStorage do navegador
            self.auth_token = token

            # 3. Consulta GET auth/me para obter dados do usuário e perfil
            user_data = await auth_client.get_current_user(token)
            self._populate_user(user_data)

            # 4. Confirma autenticação e redireciona
            self.is_authenticated = True
            self.error_message = ""
            self.is_loading = False
            return rx.redirect("/alterar-senha" if self.must_change_password else "/dashboard")

        except XanoAuthError as exc:
            self._reset_user_data()
            self.auth_token = ""
            self.error_message = exc.message or "E-mail ou senha incorretos."
            self.is_loading = False

        except (XanoConnectionError, XanoServerError) as exc:
            self.error_message = exc.message
            self.is_loading = False

        except Exception:
            self.error_message = "Ocorreu um erro inesperado. Tente novamente mais tarde."
            self.is_loading = False

    def logout(self):
        """Encerra a sessão do usuário, limpando o token e redirecionando para a tela de login."""
        self._reset_user_data()
        self.auth_token = ""
        self.error_message = ""
        self.password_change_notice = ""
        return rx.redirect("/")

    def complete_password_change(self):
        self._reset_user_data()
        self.auth_token = ""
        self.password_change_notice = "Senha alterada com sucesso. Entre novamente com sua nova senha."
        return rx.redirect("/")

    async def require_auth(self):
        """Hook on_load para páginas protegidas. Redireciona para / se não houver sessão ativa.

        Observação: Este redirecionamento é uma comodidade de navegação (UX) e não
        substitui a validação de autorização que o backend Xano aplica a cada requisição.
        """
        token = self.auth_token
        if not token or not str(token).strip():
            self.is_authenticated = False
            return rx.redirect("/")

        valid = await self.restore_session()
        if not valid:
            return rx.redirect("/")

        current_path = str(self.router.url.path)
        if self.must_change_password and current_path != "/alterar-senha":
            return rx.redirect("/alterar-senha")
        if current_path == "/alterar-senha":
            if not self.must_change_password:
                return rx.redirect("/dashboard")
            return
        if current_path in {"/usuarios", "/perfis"}:
            if not self.is_administrator:
                return rx.redirect("/dashboard")
        required_permission = _required_route_permission(current_path)
        if required_permission and not self.has_permission(required_permission):
            return rx.redirect("/dashboard")

    async def check_already_logged_in(self):
        """Hook on_load para a tela de login (/). Redireciona para o dashboard se já autenticado."""
        token = self.auth_token
        if token and str(token).strip():
            await self.restore_session()
            if self.is_authenticated:
                return rx.redirect("/alterar-senha" if self.must_change_password else "/dashboard")
