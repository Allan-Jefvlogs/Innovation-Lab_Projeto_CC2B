"""Estado global de autenticação e sessão do usuário."""

from typing import Any, Dict, Optional
from datetime import timezone
from email.utils import parsedate_to_datetime
import time
import reflex as rx

from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoServerError,
    auth_client,
    is_user_inactive_error,
)
from ..services.session_read_cache import clear_session_read_cache


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


def _retry_after_epoch(value: Optional[str], *, now: Optional[float] = None) -> float:
    """Convert an HTTP Retry-After value to a Unix timestamp."""
    if not value:
        return 0.0
    current_time = time.time() if now is None else now
    try:
        return current_time + max(0.0, float(value.strip()))
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(current_time, retry_at.timestamp())
        except (TypeError, ValueError, OverflowError):
            return 0.0


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
    session_validation: str = "invalid"  # valid, invalid, temporarily_unavailable, forbidden, validating
    session_retry_after_epoch: float = 0.0

    @rx.var
    def session_is_valid(self) -> bool:
        return self.session_validation == "valid" and self.is_authenticated

    @rx.var
    def session_status_message(self) -> str:
        if self.session_validation == "validating":
            return "Validando sua sessão com o servidor..."
        if self.session_validation == "temporarily_unavailable":
            return self.error_message or "O servidor está temporariamente indisponível. Tente novamente."
        if self.session_validation == "forbidden":
            return self.error_message or "O servidor não autorizou a validação da sessão. O acesso está bloqueado."
        return "Sua sessão ainda não foi validada."

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
        self.session_validation = "invalid"
        self.session_retry_after_epoch = 0.0

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
        return self.session_is_valid and (
            self.inventory_profile_code == "administrator"
            or permission_code in self.permission_codes
        )

    @rx.var
    def is_administrator(self) -> bool:
        return self.session_is_valid and self.inventory_profile_code == "administrator"

    def _mark_session_unavailable(self, error: Exception) -> None:
        self._reset_user_data()
        self.session_validation = "temporarily_unavailable"
        self.session_retry_after_epoch = _retry_after_epoch(
            getattr(error, "retry_after", None)
        )
        if getattr(error, "status_code", None) == 429:
            self.error_message = "O servidor limitou temporariamente as solicitações. Aguarde e tente validar a sessão novamente."
        else:
            self.error_message = getattr(error, "message", "") or "Não foi possível validar a sessão com o servidor. Tente novamente."

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

    async def restore_session(self, *, force: bool = False) -> bool:
        """Validate a persisted token without reusing stale identity or grants."""
        if self.session_validation == "valid" and self.is_authenticated and not force:
            return True
        if self.session_validation == "validating":
            return False
        if self.session_validation in {"temporarily_unavailable", "forbidden", "validating"} and not force:
            return False

        token = self.auth_token
        if not token or not str(token).strip():
            self._reset_user_data()
            return False

        # Clear cached grants before every fresh validation attempt.
        self._reset_user_data()
        self.session_validation = "validating"
        self.error_message = ""
        try:
            user_data = await auth_client.get_current_user(str(token).strip())
            self._populate_user(user_data)
            self.is_authenticated = True
            self.session_validation = "valid"
            self.session_retry_after_epoch = 0.0
            self.error_message = ""
            return True
        except XanoAuthError as exc:
            clear_session_read_cache(str(token).strip())
            self._reset_user_data()
            if exc.status_code == 403 and not is_user_inactive_error(exc):
                # The remote /auth/me 403 contract is not confirmed; block access without discarding the token.
                self.session_validation = "forbidden"
                self.error_message = (
                    "O servidor não autorizou a validação da sessão. "
                    "O acesso está bloqueado; tente novamente ou volte ao login."
                )
            else:
                self.auth_token = ""
                self.session_validation = "invalid"
                self.error_message = (
                    "Seu usuário está inativo. Entre em contato com o administrador."
                    if is_user_inactive_error(exc)
                    else exc.message or "Sua sessão expirou. Entre novamente."
                )
            return False
        except (XanoConnectionError, XanoServerError) as exc:
            # Keep the persisted token, remove cached grants, and wait for an explicit retry.
            self._mark_session_unavailable(exc)
            return False
        except Exception as exc:
            self._mark_session_unavailable(exc)
            if not self.error_message:
                self.error_message = "Erro inesperado ao verificar a sessão. Tente novamente."
            return False

    async def login(self, email: str, password: str):
        """Autentica o usuário no Xano e inicializa a sessão.

        Args:
            email: E-mail informado pelo usuário.
            password: Senha em texto claro (não armazenada no estado).
        """
        if self.session_validation == "validating":
            return

        self.is_loading = True
        self.error_message = ""
        self.password_change_notice = ""

        clean_email = email.strip() if email else ""
        if not clean_email or not password:
            self.error_message = "Por favor, preencha todos os campos."
            self.is_loading = False
            return

        remaining = self.session_retry_after_epoch - time.time()
        if remaining > 0:
            self.error_message = (
                f"Aguarde pelo menos {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
            )
            self.is_loading = False
            return

        try:
            # 1. Envia credenciais para o endpoint POST auth/login
            login_response = await auth_client.login(clean_email, password)
            token = str(login_response.get("authToken", "")).strip()

            if not token:
                raise XanoServerError("Token de autenticação não retornado pelo servidor.")

            # 2. Persiste o token no LocalStorage do navegador
            previous_token = str(self.auth_token or "").strip()
            if previous_token and previous_token != token:
                clear_session_read_cache(previous_token)
            self.auth_token = token
            self._reset_user_data()
            self.session_validation = "validating"

            # 3. Consulta GET auth/me para obter dados do usuário e perfil
            user_data = await auth_client.get_current_user(token)
            self._populate_user(user_data)

            # 4. Confirma autenticação e redireciona
            self.is_authenticated = True
            self.session_validation = "valid"
            self.session_retry_after_epoch = 0.0
            self.error_message = ""
            self.is_loading = False
            return rx.redirect("/alterar-senha" if self.must_change_password else "/dashboard")

        except XanoAuthError as exc:
            clear_session_read_cache(str(self.auth_token or "").strip())
            self._reset_user_data()
            self.auth_token = ""
            self.error_message = exc.message or "E-mail ou senha incorretos."
            self.is_loading = False

        except (XanoConnectionError, XanoServerError) as exc:
            if self.auth_token:
                self._mark_session_unavailable(exc)
            else:
                self.session_retry_after_epoch = _retry_after_epoch(
                    getattr(exc, "retry_after", None)
                )
                self.error_message = exc.message
            self.is_loading = False

        except Exception:
            self.error_message = "Ocorreu um erro inesperado. Tente novamente mais tarde."
            self.is_loading = False

    def logout(self):
        """Encerra a sessão do usuário, limpando o token e redirecionando para a tela de login."""
        clear_session_read_cache(str(self.auth_token or "").strip())
        self._reset_user_data()
        self.auth_token = ""
        self.error_message = ""
        self.password_change_notice = ""
        return rx.redirect("/")

    def complete_password_change(self):
        clear_session_read_cache(str(self.auth_token or "").strip())
        self._reset_user_data()
        self.auth_token = ""
        self.password_change_notice = "Senha alterada com sucesso. Entre novamente com sua nova senha."
        return rx.redirect("/")

    async def require_auth(self):
        """Validate access for the current route and keep temporary failures in place."""
        token = self.auth_token
        if not token or not str(token).strip():
            self._reset_user_data()
            return rx.redirect("/")

        if self.session_validation in {"temporarily_unavailable", "forbidden", "validating"}:
            return

        if not await self.restore_session():
            if self.session_validation == "invalid":
                return rx.redirect("/")
            return

        current_path = str(self.router.url.path)
        if self.must_change_password and current_path != "/alterar-senha":
            return rx.redirect("/alterar-senha")
        if current_path == "/alterar-senha":
            if not self.must_change_password:
                return rx.redirect("/dashboard")
            return
        if current_path in {"/usuarios", "/perfis"} and not self.is_administrator:
            return rx.redirect("/dashboard")
        required_permission = _required_route_permission(current_path)
        if required_permission and not self.has_permission(required_permission):
            return rx.redirect("/dashboard")

    async def retry_session_validation(self):
        """Retry only on an explicit user action and honor the server's Retry-After."""
        if self.session_validation not in {"temporarily_unavailable", "forbidden"}:
            return
        remaining = self.session_retry_after_epoch - time.time()
        if remaining > 0:
            self.error_message = (
                f"Aguarde pelo menos {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
            )
            return

        valid = await self.restore_session(force=True)
        if valid:
            return rx.redirect("/alterar-senha" if self.must_change_password else "/dashboard")
        if self.session_validation == "invalid" and str(self.router.url.path) != "/":
            return rx.redirect("/")

    async def check_already_logged_in(self):
        """Restore a persisted session without redirecting during temporary failures."""
        token = self.auth_token
        if not token or not str(token).strip():
            return
        if self.session_validation in {"temporarily_unavailable", "forbidden", "validating"}:
            return
        if await self.restore_session():
            return rx.redirect("/alterar-senha" if self.must_change_password else "/dashboard")
