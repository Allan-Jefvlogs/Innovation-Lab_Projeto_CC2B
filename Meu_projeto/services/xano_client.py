"""Cliente HTTP para comunicação com a API do Xano."""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import httpx


logger = logging.getLogger(__name__)


# Carrega variáveis do arquivo .env caso exista na raiz do projeto
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


DEFAULT_XANO_URL = "https://x8ki-letl-twmt.n7.xano.io"
AUTH_CANONICAL_GROUP = "api:DipsnlZk"
INVENTORY_CANONICAL_GROUP = "api:gestao-estoque-cadastros"
STOCK_CANONICAL_GROUP = "api:estoque"

_XANO_ERROR_CODES = {
    "DUPLICATE_VALUE",
    "BUSINESS_RULE_VIOLATION",
    "INVALID_INPUT",
    "INPUT_ERROR",
    "INPUTERROR",
    "VALIDATION_ERROR",
    "NOT_FOUND",
    "PERMISSION_DENIED",
    "PROFILE_UNASSIGNED",
    "PROFILE_INVALID",
    "PRODUCT_CREATE_FAILED",
    "PRODUCT_NOT_FOUND",
    "PRODUCT_INACTIVE",
    "SUPPLIER_NOT_FOUND",
    "SUPPLIER_INACTIVE",
    "STOCK_BALANCE_NOT_FOUND",
    "INSUFFICIENT_STOCK",
    "STOCK_UPDATE_FAILED",
    "STOCK_CONCURRENCY_CONFLICT",
}

_SENSITIVE_LOG_KEYS = {"authorization", "token", "auth_token", "password", "secret"}


def _safe_error_log_value(value: Any) -> Any:
    """Redacte dados de autenticação antes de registrar detalhes do Xano."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).lower() in _SENSITIVE_LOG_KEYS else _safe_error_log_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_error_log_value(item) for item in value]
    return value


def _extract_xano_error_code(payload: Any) -> str:
    """Localiza códigos conhecidos em formatos de erro Xano, inclusive aninhados."""
    pending = [payload]
    found = set()
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key in ("code", "name", "error_code", "error", "message", "details", "payload"):
                value = current.get(key)
                if isinstance(value, str):
                    normalized = value.strip().upper()
                    if normalized in _XANO_ERROR_CODES:
                        found.add(normalized)
                elif isinstance(value, (dict, list)):
                    pending.append(value)
            pending.extend(
                value for key, value in current.items()
                if key not in {"code", "name", "error_code", "error", "message", "details", "payload"}
                and isinstance(value, (dict, list))
            )
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, str):
            normalized = current.strip().upper()
            if normalized in _XANO_ERROR_CODES:
                found.add(normalized)
    for code in (
        "DUPLICATE_VALUE",
        "BUSINESS_RULE_VIOLATION",
        "PRODUCT_CREATE_FAILED",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "PROFILE_UNASSIGNED",
        "PROFILE_INVALID",
        "PRODUCT_NOT_FOUND",
        "PRODUCT_INACTIVE",
        "SUPPLIER_NOT_FOUND",
        "SUPPLIER_INACTIVE",
        "STOCK_BALANCE_NOT_FOUND",
        "INSUFFICIENT_STOCK",
        "STOCK_UPDATE_FAILED",
        "STOCK_CONCURRENCY_CONFLICT",
        "INVALID_INPUT",
        "VALIDATION_ERROR",
        "INPUT_ERROR",
        "INPUTERROR",
    ):
        if code in found:
            return code
    return "API_ERROR"


class XanoError(Exception):
    """Exceção base para erros de comunicação com a API do Xano."""

    def __init__(self, message: str, status_code: Optional[int] = None, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class XanoAuthError(XanoError):
    """Exceção para falhas de autenticação ou credenciais inválidas (HTTP 401/403)."""
    pass


class XanoPermissionError(XanoError):
    """Exceção para uma operação recusada pelas permissões do usuário."""
    pass


class XanoRequestError(XanoError):
    """Erro funcional retornado por uma API do Xano."""

    def __init__(self, message: str, error_code: str, status_code: int, payload: Dict[str, Any]):
        super().__init__(message, status_code=status_code, payload=payload)
        self.error_code = error_code


class XanoConnectionError(XanoError):
    """Exceção para falhas de conectividade, timeout ou transporte de rede."""
    pass


class XanoServerError(XanoError):
    """Exceção para erros internos do servidor Xano (HTTP 5xx) ou respostas inesperadas."""
    pass


class XanoAuthClient:
    """Cliente responsável pelas operações de autenticação e identificação de usuário no Xano."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        self.base_url = (base_url or os.getenv("XANO_API_BASE_URL", DEFAULT_XANO_URL)).rstrip("/")
        self.timeout = timeout

    @property
    def auth_group_url(self) -> str:
        """Retorna a URL base do grupo de APIs de Autenticação."""
        return f"{self.base_url}/{AUTH_CANONICAL_GROUP}"

    @property
    def inventory_group_url(self) -> str:
        """Retorna a URL base do grupo de APIs de cadastros do estoque."""
        return f"{self.base_url}/{INVENTORY_CANONICAL_GROUP}"

    @property
    def stock_group_url(self) -> str:
        """Retorna a URL base do grupo de consulta de estoque."""
        return f"{self.base_url}/{STOCK_CANONICAL_GROUP}"

    async def _inventory_request(
        self,
        method: str,
        path: str,
        auth_token: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        group_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executa uma chamada autenticada a um grupo de APIs do estoque."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{(group_url or self.inventory_group_url)}/{path.lstrip('/')}",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    params=params,
                    json=json_payload,
                )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.exception(
                "Xano transport failed: method=%s path=%s exception_type=%s",
                method,
                path,
                type(exc).__name__,
            )
            raise XanoConnectionError(
                "Não foi possível conectar ao Xano. Verifique sua conexão e tente novamente."
            ) from exc

        try:
            data = response.json() if response.content else {}
        except ValueError as exc:
            logger.exception(
                "Xano JSON decode failed: method=%s path=%s status=%s",
                method,
                path,
                response.status_code,
            )
            raise XanoServerError(
                "O Xano retornou uma resposta inválida.", status_code=response.status_code
            ) from exc

        logger.info(
            "Xano response: method=%s path=%s status=%s python_type=%s keys=%s",
            method,
            path,
            response.status_code,
            type(data).__name__,
            sorted(data.keys()) if isinstance(data, dict) else None,
        )

        if response.status_code in (200, 201):
            if not isinstance(data, dict):
                logger.error(
                    "Unexpected Xano success response: method=%s path=%s status=%s python_type=%s",
                    method,
                    path,
                    response.status_code,
                    type(data).__name__,
                )
                raise XanoServerError(
                    "O Xano retornou uma resposta em formato inesperado.",
                    status_code=response.status_code,
                )
            return data

        payload = data if isinstance(data, dict) else {}
        logger.error(
            "Xano request failed: method=%s path=%s status=%s python_type=%s keys=%s error_code=%r error_message=%r error_payload=%r",
            method,
            path,
            response.status_code,
            type(data).__name__,
            sorted(data.keys()) if isinstance(data, dict) else None,
            _safe_error_log_value(data.get("code")) if isinstance(data, dict) else None,
            _safe_error_log_value(data.get("message")) if isinstance(data, dict) else None,
            _safe_error_log_value(data.get("payload")) if isinstance(data, dict) else None,
        )
        if response.status_code == 401:
            raise XanoAuthError(
                "Sua sessão expirou. Faça login novamente.",
                status_code=response.status_code,
                payload=payload,
            )
        if response.status_code == 403:
            raise XanoPermissionError(
                "Você não tem permissão para executar esta operação.",
                status_code=response.status_code,
                payload=payload,
            )

        error_code = _extract_xano_error_code(data)
        friendly_messages = {
            "INVALID_INPUT": "Confira os campos informados e tente novamente.",
            "INPUT_ERROR": "Confira os campos obrigatórios e os valores informados.",
            "INPUTERROR": "Confira os campos obrigatórios e os valores informados.",
            "VALIDATION_ERROR": "Confira os campos obrigatórios e os valores informados.",
            "DUPLICATE_VALUE": "Já existe um produto com esse código.",
            "BUSINESS_RULE_VIOLATION": "A Categoria selecionada não existe ou está inativa. Selecione uma Categoria ativa.",
            "NOT_FOUND": "O produto solicitado não foi encontrado.",
            "PERMISSION_DENIED": "Você não tem permissão para executar esta operação.",
            "PROFILE_UNASSIGNED": "Seu usuário ainda não possui um perfil de estoque atribuído.",
            "PROFILE_INVALID": "O perfil do usuário não está válido para esta operação.",
            "PRODUCT_NOT_FOUND": "Produto não encontrado.",
            "PRODUCT_INACTIVE": "Não é possível registrar entrada para um produto inativo.",
            "SUPPLIER_NOT_FOUND": "Fornecedor não encontrado.",
            "SUPPLIER_INACTIVE": "O fornecedor selecionado está inativo.",
            "STOCK_BALANCE_NOT_FOUND": "Não foi encontrado saldo de estoque para este produto.",
            "STOCK_UPDATE_FAILED": "Não foi possível atualizar o estoque. Tente novamente.",
            "STOCK_CONCURRENCY_CONFLICT": "Houve um conflito ao atualizar o estoque. Tente novamente.",
        }
        message = friendly_messages.get(
            error_code,
            f"O Xano não concluiu a operação ({response.status_code}). Tente novamente.",
        )
        raise XanoRequestError(message, error_code, response.status_code, payload)

    async def list_products(
        self, auth_token: str, page: int = 1, per_page: int = 100
    ) -> Dict[str, Any]:
        """Consulta a listagem paginada de produtos com a sessão atual."""
        data = await self._inventory_request(
            "GET", "/products", auth_token, params={"page": page, "per_page": per_page}
        )
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou uma lista de produtos em formato inesperado.")
        return data

    async def list_categories(
        self, auth_token: str, page: int = 1, per_page: int = 100, status: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status is not None:
            params["status"] = status
        data = await self._inventory_request(
            "GET",
            "/categories",
            auth_token,
            params=params,
        )
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou Categorias em formato inesperado.")
        return data

    async def create_category(self, auth_token: str, nome: str) -> Dict[str, Any]:
        """Cria uma Categoria; normalização e validação definitivas ficam no Xano."""
        return await self._inventory_request(
            "POST",
            "/categories",
            auth_token,
            json_payload={"nome": nome.strip()},
        )

    async def activate_category(self, auth_token: str, category_id: int) -> Dict[str, Any]:
        """Ativa uma Categoria e retorna o estado persistido pelo Xano."""
        return await self._inventory_request(
            "PATCH",
            f"/categories/by_id/{category_id}/activate",
            auth_token,
        )

    async def inactivate_category(self, auth_token: str, category_id: int) -> Dict[str, Any]:
        """Inativa uma Categoria sem removê-la nem alterar vínculos de Produto."""
        return await self._inventory_request(
            "PATCH",
            f"/categories/by_id/{category_id}/inactivate",
            auth_token,
        )

    async def get_category(self, auth_token: str, category_id: int) -> Dict[str, Any]:
        """Consulta uma Categoria por ID para preservar vínculos existentes no formulário."""
        return await self._inventory_request(
            "GET", f"/categories/by_id/{category_id}", auth_token
        )

    async def list_suppliers(
        self, auth_token: str, page: int = 1, per_page: int = 100
    ) -> Dict[str, Any]:
        data = await self._inventory_request(
            "GET",
            "/suppliers",
            auth_token,
            params={"page": page, "per_page": per_page},
        )
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou Fornecedores em formato inesperado.")
        return data

    async def get_supplier(self, auth_token: str, supplier_id: int) -> Dict[str, Any]:
        return await self._inventory_request(
            "GET", f"/suppliers/by_id/{supplier_id}", auth_token
        )

    async def create_supplier(
        self,
        auth_token: str,
        *,
        nome_razao_social: str,
        tipo_documento: str,
        documento: str,
        contato: Optional[str] = None,
        endereco: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria Fornecedor usando os campos e validações cadastrais do Xano."""
        payload: Dict[str, Any] = {
            "nome_razao_social": nome_razao_social.strip(),
            "tipo_documento": tipo_documento.strip(),
            "documento": documento.strip(),
        }
        if contato and contato.strip():
            payload["contato"] = contato.strip()
        if endereco and endereco.strip():
            payload["endereco"] = endereco.strip()
        return await self._inventory_request(
            "POST", "/suppliers", auth_token, json_payload=payload
        )

    async def update_supplier(
        self,
        auth_token: str,
        supplier_id: int,
        *,
        nome_razao_social: str,
        tipo_documento: str,
        documento: str,
        contato: Optional[str] = None,
        endereco: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atualiza dados cadastrais sem alterar status nem ID do Fornecedor."""
        payload: Dict[str, Any] = {
            "nome_razao_social": nome_razao_social.strip(),
            "tipo_documento": tipo_documento.strip(),
            "documento": documento.strip(),
        }
        if contato and contato.strip():
            payload["contato"] = contato.strip()
        else:
            payload["limpar_contato"] = True
        if endereco and endereco.strip():
            payload["endereco"] = endereco.strip()
        else:
            payload["limpar_endereco"] = True
        return await self._inventory_request(
            "PATCH",
            f"/suppliers/by_id/{supplier_id}",
            auth_token,
            json_payload=payload,
        )

    async def list_stock(
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 100,
        situacao: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta uma página autenticada dos saldos oficiais de estoque."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if situacao in {"normal", "abaixo_minimo", "sem_estoque"}:
            params["situacao"] = situacao
        if search and search.strip():
            params["search"] = search.strip()
        logger.info("Stock request params: %r", params)
        data = await self._inventory_request(
            "GET",
            "/stock",
            auth_token,
            params=params,
            group_url=self.stock_group_url,
        )
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou saldos de estoque em formato inesperado.")
        return data

    async def get_stock_summary(self, auth_token: str) -> Dict[str, int]:
        """Consulta os totais de produtos monitorados e por situaÃ§Ã£o."""
        data = await self._inventory_request(
            "GET",
            "/stock_summary",
            auth_token,
            group_url=self.stock_group_url,
        )
        try:
            return {
                "total": int(data["total"]),
                "normal": int(data["normal"]),
                "abaixo_minimo": int(data["abaixo_minimo"]),
                "sem_estoque": int(data["sem_estoque"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise XanoServerError("O Xano retornou um resumo de estoque em formato inesperado.") from exc

    async def list_movements(
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 20,
        tipo: Optional[str] = None,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Consulta uma página do histórico enriquecido no grupo Inventory Stock."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if tipo in {"entrada", "saida"}:
            params["tipo"] = tipo
        for name, value in (("product_id", product_id), ("user_id", user_id)):
            if value is None or value == "":
                continue
            try:
                numeric_id = int(value)
            except (TypeError, ValueError):
                continue
            if numeric_id <= 0:
                continue
            params[name] = numeric_id
        logger.info("Movement history params: %r", params)
        data = await self._inventory_request(
            "GET",
            "/movements",
            auth_token,
            params=params,
            group_url=self.stock_group_url,
        )
        if not isinstance(data.get("items"), list):
            logger.error(
                "Unexpected paginated Xano response: method=GET path=/movements python_type=%s keys=%s items_type=%s",
                type(data).__name__,
                sorted(data.keys()),
                type(data.get("items")).__name__,
            )
            raise XanoServerError("O Xano retornou movimentações em formato inesperado.")
        return data

    async def list_movement_users(
        self, auth_token: str, page: int = 1, per_page: int = 100
    ) -> Dict[str, Any]:
        """Lista somente ID e nome para preencher o filtro do histórico."""
        data = await self._inventory_request(
            "GET",
            "/movement_users",
            auth_token,
            params={"page": page, "per_page": per_page},
            group_url=self.stock_group_url,
        )
        if not isinstance(data.get("items"), list):
            logger.error(
                "Unexpected paginated Xano response: method=GET path=/movement_users python_type=%s keys=%s items_type=%s",
                type(data).__name__,
                sorted(data.keys()),
                type(data.get("items")).__name__,
            )
            raise XanoServerError("O Xano retornou usuários em formato inesperado.")
        return data

    async def create_stock_entry(
        self,
        auth_token: str,
        *,
        product_id: int,
        quantidade: float,
        motivo: str,
        supplier_id: Optional[int] = None,
        data_hora: Optional[str] = None,
        observacao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra uma Entrada no grupo Inventory Stock usando a sessão atual."""
        payload: Dict[str, Any] = {
            "product_id": product_id,
            "quantidade": quantidade,
            "motivo": motivo.strip(),
        }
        if supplier_id is not None and supplier_id > 0:
            payload["supplier_id"] = supplier_id
        if data_hora and data_hora.strip():
            payload["data_hora"] = data_hora.strip()
        if observacao and observacao.strip():
            payload["observacao"] = observacao.strip()
        return await self._inventory_request(
            "POST",
            "/entries",
            auth_token,
            json_payload=payload,
            group_url=self.stock_group_url,
        )

    async def create_stock_exit(
        self,
        auth_token: str,
        *,
        product_id: int,
        quantidade: float,
        motivo: str,
        data_hora: Optional[str] = None,
        observacao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra uma Saída autenticada no grupo Inventory Stock."""
        payload: Dict[str, Any] = {
            "product_id": product_id,
            "quantidade": quantidade,
            "motivo": motivo.strip(),
        }
        if data_hora and data_hora.strip():
            payload["data_hora"] = data_hora.strip()
        if observacao and observacao.strip():
            payload["observacao"] = observacao.strip()
        return await self._inventory_request(
            "POST",
            "/exits",
            auth_token,
            json_payload=payload,
            group_url=self.stock_group_url,
        )

    async def create_product(self, auth_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._inventory_request("POST", "/products", auth_token, json_payload=payload)

    async def get_product(self, auth_token: str, product_id: int) -> Dict[str, Any]:
        return await self._inventory_request(
            "GET", f"/products/by_id/{product_id}", auth_token
        )

    async def update_product(
        self, auth_token: str, product_id: int, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._inventory_request(
            "PATCH", f"/products/by_id/{product_id}", auth_token, json_payload=payload
        )

    async def inactivate_product(self, auth_token: str, product_id: int) -> Dict[str, Any]:
        return await self._inventory_request(
            "PATCH", f"/products/by_id/{product_id}/inactivate", auth_token
        )

    async def activate_product(self, auth_token: str, product_id: int) -> Dict[str, Any]:
        return await self._inventory_request(
            "PATCH", f"/products/by_id/{product_id}/activate", auth_token
        )

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Realiza autenticação por e-mail e senha consumindo POST auth/login.

        Args:
            email: E-mail do usuário.
            password: Senha em texto claro.

        Returns:
            Dicionário contendo authToken (str) e user_id (int).

        Raises:
            XanoAuthError: Se as credenciais forem inválidas (HTTP 401/403).
            XanoConnectionError: Se houver falha de rede ou timeout.
            XanoServerError: Se o servidor retornar erro inesperado.
        """
        url = f"{self.auth_group_url}/auth/login"
        payload = {"email": email, "password": password}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise XanoConnectionError(
                "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
            ) from exc

        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict) or "authToken" not in data:
                raise XanoServerError(
                    "Resposta do servidor inválida: token de autenticação não encontrado.",
                    status_code=response.status_code,
                    payload=data if isinstance(data, dict) else {},
                )
            return data

        # Tratamento de erro 401 ou 403 (acesso negado / credenciais inválidas)
        if response.status_code in (401, 403):
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {}
            raise XanoAuthError(
                "E-mail ou senha incorretos.",
                status_code=response.status_code,
                payload=error_payload,
            )

        # Demais erros HTTP (4xx, 5xx)
        try:
            error_payload = response.json()
        except Exception:
            error_payload = {}

        raise XanoServerError(
            f"Erro na autenticação ({response.status_code}). Tente novamente mais tarde.",
            status_code=response.status_code,
            payload=error_payload,
        )

    async def get_current_user(self, auth_token: str) -> Dict[str, Any]:
        """Obtém o registro do usuário autenticado consumindo GET auth/me.

        Args:
            auth_token: Token JWT de autenticação emitido pelo Xano.

        Returns:
            Dicionário com os dados do usuário, incluindo id, name, email,
            role e inventory_profile_id.

        Raises:
            XanoAuthError: Se o token for inválido ou tiver expirado (HTTP 401/403).
            XanoConnectionError: Se houver falha de rede ou timeout.
            XanoServerError: Se o servidor retornar erro inesperado.
        """
        url = f"{self.auth_group_url}/auth/me"
        headers = {"Authorization": f"Bearer {auth_token}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise XanoConnectionError(
                "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
            ) from exc

        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict) or "id" not in data:
                raise XanoServerError(
                    "Resposta do servidor inválida: dados de usuário não encontrados.",
                    status_code=response.status_code,
                    payload=data if isinstance(data, dict) else {},
                )
            return data

        if response.status_code in (401, 403):
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {}
            raise XanoAuthError(
                "Sessão expirada ou não autorizada. Faça login novamente.",
                status_code=response.status_code,
                payload=error_payload,
            )

        try:
            error_payload = response.json()
        except Exception:
            error_payload = {}

        raise XanoServerError(
            f"Erro ao recuperar dados do usuário ({response.status_code}).",
            status_code=response.status_code,
            payload=error_payload,
        )


# Instância padrão compartilhada
auth_client = XanoAuthClient()
