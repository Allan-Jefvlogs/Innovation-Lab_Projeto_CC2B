# reflex """Cliente HTTP para comunicação com a API do Xano."""

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import math
import os
import re
import time
from collections import deque
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
import httpx
from .session_read_cache import session_read_cache


logger = logging.getLogger(__name__)

_PURCHASE_EMAIL_LOCAL_PATTERN = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+")
_PURCHASE_EMAIL_DOMAIN_LABEL_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)


def normalize_purchase_request_email(value: Optional[str], *, required: bool) -> Optional[str]:
    """Trim and validate a commercial recipient without changing its spelling."""
    if value is None:
        if required:
            raise ValueError("Informe um e-mail de destinatário válido.")
        return None
    normalized = value.strip()
    if not normalized:
        if required:
            raise ValueError("Informe um e-mail de destinatário válido.")
        return None
    local, separator, domain = normalized.partition("@")
    labels = domain.split(".")
    if (
        not separator
        or len(normalized) > 254
        or len(local) > 64
        or len(domain) > 253
        or not _PURCHASE_EMAIL_LOCAL_PATTERN.fullmatch(local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or len(labels) < 2
        or len(labels[-1]) < 2
        or any(not _PURCHASE_EMAIL_DOMAIN_LABEL_PATTERN.fullmatch(label) for label in labels)
    ):
        raise ValueError("Informe um e-mail de destinatário válido.")
    return normalized


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

_DASHBOARD_CACHE_ENDPOINTS = (
    "GET /dashboard/products",
    "GET /dashboard/categories",
    "GET /dashboard/suppliers",
    "GET /dashboard/stock",
    "GET /stock/insufficient_summary",
    "GET /dashboard/movements",
    "GET /stock/replenishment",
    "GET /purchase_requests/summary",
    "GET /purchase_requests",
    "GET /purchase_requests/by_id",
)

_XANO_ERROR_CODES = {
    "DUPLICATE_VALUE",
    "PASSWORD_CHANGE_NOT_REQUIRED",
    "BUSINESS_RULE_VIOLATION",
    "INVALID_INPUT",
    "INPUT_ERROR",
    "INPUTERROR",
    "VALIDATION_ERROR",
    "NOT_FOUND",
    "PERMISSION_DENIED",
    "PROFILE_UNASSIGNED",
    "PROFILE_INVALID",
    "DUPLICATE_EMAIL",
    "PASSWORD_MISMATCH",
    "USER_INACTIVE",
    "USER_NOT_FOUND",
    "USER_CREATE_FAILED",
    "USER_UPDATE_FAILED",
    "SELF_INACTIVATION_FORBIDDEN",
    "LAST_LEADER_REQUIRED",
    "PRODUCT_CREATE_FAILED",
    "PRODUCT_NOT_FOUND",
    "PRODUCT_INACTIVE",
    "SUPPLIER_NOT_FOUND",
    "SUPPLIER_INACTIVE",
    "STOCK_BALANCE_NOT_FOUND",
    "INSUFFICIENT_STOCK",
    "STOCK_UPDATE_FAILED",
    "STOCK_CONCURRENCY_CONFLICT",
    "PERMISSION_REVISION_CONFLICT",
    "UNKNOWN_PERMISSION_CODE",
    "DUPLICATE_PERMISSION_CODE",
    "IMMUTABLE_PROFILE",
    "INVALID_QUANTITY",
    "INVALID_URGENCY",
    "PRODUCT_STOCK_NOT_INSUFFICIENT",
    "STOCK_BALANCE_INVALID",
    "PURCHASE_REQUEST_ALREADY_ACTIVE",
    "IDEMPOTENCY_KEY_REUSED",
    "PURCHASE_REQUEST_CREATE_FAILED",
    "INVALID_REQUEST_ID",
    "INVALID_JUSTIFICATION",
    "PURCHASE_REQUEST_NOT_FOUND",
    "PURCHASE_REQUEST_ALREADY_CANCELLED",
    "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE",
    "PURCHASE_REQUEST_CANCEL_CONFLICT",
    "PURCHASE_REQUEST_CANCEL_FAILED",
    "TOO_MANY_REQUESTS",
}

_SENSITIVE_LOG_KEYS = {
    "authorization", "token", "auth_token", "password", "confirm_password", "secret"
}


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
        "USER_INACTIVE",
        "DUPLICATE_VALUE",
        "BUSINESS_RULE_VIOLATION",
        "PASSWORD_CHANGE_NOT_REQUIRED",
        "PRODUCT_CREATE_FAILED",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "PROFILE_UNASSIGNED",
        "PROFILE_INVALID",
        "DUPLICATE_EMAIL",
        "PASSWORD_MISMATCH",
        "USER_NOT_FOUND",
        "USER_CREATE_FAILED",
        "USER_UPDATE_FAILED",
        "SELF_INACTIVATION_FORBIDDEN",
        "LAST_LEADER_REQUIRED",
        "PRODUCT_NOT_FOUND",
        "PRODUCT_INACTIVE",
        "SUPPLIER_NOT_FOUND",
        "SUPPLIER_INACTIVE",
        "STOCK_BALANCE_NOT_FOUND",
        "INSUFFICIENT_STOCK",
        "STOCK_UPDATE_FAILED",
        "STOCK_CONCURRENCY_CONFLICT",
        "PERMISSION_REVISION_CONFLICT",
        "UNKNOWN_PERMISSION_CODE",
        "DUPLICATE_PERMISSION_CODE",
        "IMMUTABLE_PROFILE",
        "PURCHASE_REQUEST_NOT_FOUND",
        "PRODUCT_STOCK_NOT_INSUFFICIENT",
        "STOCK_BALANCE_INVALID",
        "PURCHASE_REQUEST_ALREADY_ACTIVE",
        "IDEMPOTENCY_KEY_REUSED",
        "PURCHASE_REQUEST_CREATE_FAILED",
        "INVALID_REQUEST_ID",
        "INVALID_JUSTIFICATION",
        "PURCHASE_REQUEST_ALREADY_CANCELLED",
        "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE",
        "PURCHASE_REQUEST_CANCEL_CONFLICT",
        "PURCHASE_REQUEST_CANCEL_FAILED",
        "INVALID_QUANTITY",
        "INVALID_URGENCY",
        "INVALID_INPUT",
        "TOO_MANY_REQUESTS",
        "VALIDATION_ERROR",
        "INPUT_ERROR",
        "INPUTERROR",
    ):
        if code in found:
            return code
    return "API_ERROR"


class XanoError(Exception):
    """Exceção base para erros de comunicação com a API do Xano."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        retry_after: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
        self.retry_after = retry_after


class XanoAuthError(XanoError):
    """Exceção para falhas de autenticação ou credenciais inválidas (HTTP 401/403)."""
    pass


def is_user_inactive_error(error: XanoError) -> bool:
    """Identifica USER_INACTIVE em respostas Xano, inclusive envelopes aninhados."""
    return _extract_xano_error_code(error.payload) == "USER_INACTIVE" or (
        error.message.strip().upper() == "USER_INACTIVE"
    )


class XanoPermissionError(XanoError):
    """Exceção para uma operação recusada pelas permissões do usuário."""
    pass


class XanoRequestError(XanoError):
    """Erro funcional retornado por uma API do Xano."""

    def __init__(
        self, message: str, error_code: str, status_code: int, payload: Dict[str, Any],
        retry_after: Optional[str] = None,
    ):
        super().__init__(message, status_code=status_code, payload=payload, retry_after=retry_after)
        self.error_code = error_code
        self.origin = "remote_xano" if status_code == 429 else None


class XanoConnectionError(XanoError):
    """Exceção para falhas de conectividade, timeout ou transporte de rede."""
    pass


class XanoServerError(XanoError):
    """Exceção para erros internos do servidor Xano (HTTP 5xx) ou respostas inesperadas."""
    pass


class XanoRateLimitError(XanoServerError):
    """Bloqueio do coordenador local antes de iniciar uma chamada HTTP."""

    def __init__(self, retry_after_seconds: float):
        seconds = max(1, math.ceil(retry_after_seconds))
        super().__init__(
            f"Limite local de requisi\u00e7\u00f5es atingido. Aguarde {seconds} segundo(s) e tente novamente.",
            status_code=429,
            retry_after=str(seconds),
        )
        self.retry_after_seconds = retry_after_seconds
        self.origin = "local_coordinator"


class XanoRequestCoordinator:
    """Limita chamadas por processo e deduplica apenas GETs em andamento.

    O lock protege somente os metadados locais. A chamada HTTP ocorre depois
    que ele é liberado, e Futures concorrentes permitem compartilhar um GET
    entre event loops sem manter clientes HTTP vinculados a um loop.
    """

    def __init__(
        self,
        limit: int = 7,
        window_seconds: float = 20.0,
        *,
        clock=None,
        wall_clock=None,
    ):
        self.limit = max(1, int(limit))
        self.window_seconds = max(0.1, float(window_seconds))
        self._clock = clock or time.monotonic
        self._wall_clock = wall_clock or time.time
        self._lock = Lock()
        self._started: deque[float] = deque()
        self._blocked_until = 0.0
        self._inflight: dict[tuple[str, str, str], concurrent.futures.Future] = {}

    @staticmethod
    def _normalized_params(params: Optional[Dict[str, Any]]) -> str:
        return json.dumps(params or {}, sort_keys=True, separators=(",", ":"), default=str)

    def _get_key(
        self, method: str, url: str, token: Optional[str], params
    ) -> tuple[str, str, str]:
        credential_id = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
        request_id = json.dumps(
            [url, self._normalized_params(params)], separators=(",", ":")
        )
        return method.upper(), credential_id, request_id

    def _retry_error(self, delay: float) -> XanoRateLimitError:
        return XanoRateLimitError(max(0.0, delay))

    def _reserve_locked(self, now: float) -> None:
        while self._started and now - self._started[0] >= self.window_seconds:
            self._started.popleft()
        if now < self._blocked_until:
            raise self._retry_error(self._blocked_until - now)
        if len(self._started) >= self.limit:
            raise self._retry_error(self._started[0] + self.window_seconds - now)
        self._started.append(now)

    @staticmethod
    def _retry_delay(header: Optional[str], fallback: float, wall_now: float) -> float:
        if header:
            try:
                return max(0.0, float(header.strip()))
            except (TypeError, ValueError):
                try:
                    retry_at = parsedate_to_datetime(header)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(0.0, retry_at.timestamp() - wall_now)
                except (TypeError, ValueError, OverflowError):
                    pass
        return fallback

    def mark_rate_limited(self, retry_after: Optional[str]) -> None:
        delay = self._retry_delay(retry_after, self.window_seconds, self._wall_clock())
        with self._lock:
            self._blocked_until = max(self._blocked_until, self._clock() + delay)

    async def request(
        self,
        method: str,
        url: str,
        *,
        token: Optional[str],
        params: Optional[Dict[str, Any]],
        send,
    ) -> httpx.Response:
        method = method.upper()
        key = self._get_key(method, url, token, params) if method == "GET" else None
        leader = True
        shared: Optional[concurrent.futures.Future] = None
        with self._lock:
            if key is not None and key in self._inflight:
                leader = False
                shared = self._inflight[key]
            else:
                self._reserve_locked(self._clock())
                if key is not None:
                    shared = concurrent.futures.Future()
                    self._inflight[key] = shared

        if not leader:
            assert shared is not None
            return await asyncio.shield(asyncio.wrap_future(shared))

        try:
            response = await send()
            if response.status_code == 429:
                self.mark_rate_limited(response.headers.get("Retry-After"))
            if shared is not None and not shared.done():
                shared.set_result(response)
            return response
        except BaseException as exc:
            if shared is not None and not shared.done():
                shared.set_exception(exc)
            raise
        finally:
            if key is not None:
                with self._lock:
                    if self._inflight.get(key) is shared:
                        del self._inflight[key]


def _configured_positive_int(name: str, default: int) -> int:
    try:
        return min(7, max(1, int(os.getenv(name, str(default)))))
    except (TypeError, ValueError):
        return default


def _configured_positive_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


_DEFAULT_REQUEST_COORDINATOR = XanoRequestCoordinator(
    # Cota remota nominal observada: 10/20 s; mantemos margem para outros
    # usuários e ferramentas que compartilham o workspace Xano.
    limit=_configured_positive_int("XANO_REQUEST_BUDGET", 7),
    window_seconds=max(20.0, _configured_positive_float("XANO_REQUEST_WINDOW_SECONDS", 20.0)),
)


class XanoAuthClient:
    """Cliente responsável pelas operações de autenticação e identificação de usuário no Xano."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        *,
        coordinator: Optional[XanoRequestCoordinator] = None,
    ):
        self.base_url = (base_url or os.getenv("XANO_API_BASE_URL", DEFAULT_XANO_URL)).rstrip("/")
        self.timeout = timeout
        self.coordinator = coordinator or _DEFAULT_REQUEST_COORDINATOR

    async def _send_request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                request = getattr(client, "request", None)
                if request is not None:
                    return await request(
                        method, url, headers=headers, params=params, json=json_payload
                    )
                # Compatibilidade com fakes legados usados nos testes do cliente.
                method_call = getattr(client, method.lower())
                kwargs = {"headers": headers, "params": params}
                if json_payload is not None:
                    kwargs["json"] = json_payload
                return await method_call(url, **kwargs)

        return await self.coordinator.request(
            method, url, token=auth_token, params=params, send=send
        )

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
            response = await self._send_request(
                method,
                f"{(group_url or self.inventory_group_url)}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
                json_payload=json_payload,
                auth_token=auth_token,
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
            if method.upper() != "GET":
                for endpoint in _DASHBOARD_CACHE_ENDPOINTS:
                    session_read_cache.invalidate(endpoint=endpoint, token=auth_token)
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
        error_code = (
            "TOO_MANY_REQUESTS"
            if response.status_code == 429
            else _extract_xano_error_code(data)
        )
        if error_code == "USER_INACTIVE":
            raise XanoAuthError(
                "Sua conta foi inativada. Entre em contato com o Líder.",
                status_code=response.status_code,
                payload=payload,
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

        friendly_messages = {
            "INVALID_QUANTITY": "Informe uma quantidade maior que zero.",
            "INVALID_URGENCY": "Selecione uma urgência válida.",
            "STOCK_BALANCE_INVALID": "O saldo de estoque retornado não permite criar a solicitação.",
            "PRODUCT_STOCK_NOT_INSUFFICIENT": "O estoque do Produto já não precisa de reposição.",
            "PURCHASE_REQUEST_ALREADY_ACTIVE": "Já existe uma solicitação ativa para este Produto.",
            "IDEMPOTENCY_KEY_REUSED": "A chave desta tentativa foi usada com dados diferentes. Confira os dados antes de iniciar outra tentativa.",
            "PURCHASE_REQUEST_CREATE_FAILED": "O Xano não confirmou a criação da solicitação. Verifique o resultado antes de iniciar outra tentativa.",
            "INVALID_REQUEST_ID": "A solicitação selecionada não é válida.",
            "INVALID_JUSTIFICATION": "Informe uma justificativa para cancelar a solicitação.",
            "PURCHASE_REQUEST_NOT_FOUND": "A solicitação de compra não foi encontrada.",
            "PURCHASE_REQUEST_ALREADY_CANCELLED": "A solicitação já está cancelada.",
            "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE": "O status atual não permite cancelar esta solicitação.",
            "PURCHASE_REQUEST_CANCEL_CONFLICT": "A solicitação mudou enquanto era cancelada. Atualize a lista.",
            "PURCHASE_REQUEST_CANCEL_FAILED": "O Xano não confirmou o cancelamento. Verifique a lista antes de repetir.",
            "INVALID_INPUT": "Confira os campos informados e tente novamente.",
            "INPUT_ERROR": "Confira os campos obrigatórios e os valores informados.",
            "INPUTERROR": "Confira os campos obrigatórios e os valores informados.",
            "VALIDATION_ERROR": "Confira os campos obrigatórios e os valores informados.",
            "PASSWORD_MISMATCH": "A confirmação da senha não confere.",
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
            "TOO_MANY_REQUESTS": "O Xano está limitando as solicitações. Aguarde e tente novamente.",
        }
        message = friendly_messages.get(
            error_code,
            f"O Xano não concluiu a operação ({response.status_code}). Tente novamente.",
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            delay = self.coordinator._retry_delay(
                retry_after, self.coordinator.window_seconds, time.time()
            )
            message = (
                "O Xano está limitando as solicitações. "
                f"Aguarde {max(1, math.ceil(delay))} segundo(s) e tente novamente."
            )
        raise XanoRequestError(
            message,
            error_code,
            response.status_code,
            payload,
            retry_after=response.headers.get("Retry-After"),
        )

    async def get_permissions(self, auth_token: str) -> Dict[str, Any]:
        """Consulta perfis, catálogo e matriz administrativa já existentes no Xano."""
        data = await self._inventory_request("GET", "/permissions", auth_token)
        if not all(isinstance(data.get(key), list) for key in ("profiles", "permissions", "permission_matrix")):
            raise XanoServerError("O Xano retornou a matriz de permissões em formato inesperado.")
        return data

    async def update_profile_permissions(
        self, auth_token: str, profile_code: str, permissions: list[str], permission_revision: int
    ) -> Dict[str, Any]:
        if profile_code not in {"stockkeeper", "read_only"}:
            raise ValueError("O perfil selecionado não pode ser editado.")
        return await self._inventory_request(
            "PATCH", f"/permissions/profiles/{profile_code}", auth_token,
            json_payload={"permissions": permissions, "permission_revision": permission_revision},
        )

    async def list_users(
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta a listagem paginada de usuários do endpoint existente GET /users."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if search and search.strip():
            params["search"] = search.strip()
        data = await self._inventory_request("GET", "/users", auth_token, params=params)
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou usuários em formato inesperado.")
        return data

    async def get_inventory_profiles(self, auth_token: str) -> Dict[str, Any]:
        """Obtém os perfis reais pelo endpoint existente GET /permissions."""
        data = await self._inventory_request("GET", "/permissions", auth_token)
        if not isinstance(data.get("profiles"), list):
            raise XanoServerError("O Xano retornou perfis em formato inesperado.")
        return data

    async def get_user(self, auth_token: str, user_id: int) -> Dict[str, Any]:
        """Consulta um usuário pelo endpoint existente GET /users/by_id/{user_id}."""
        return await self._inventory_request("GET", f"/users/by_id/{user_id}", auth_token)

    async def create_user(
        self,
        auth_token: str,
        *,
        name: str,
        email: str,
        password: str,
        confirm_password: str,
        inventory_profile_id: int,
    ) -> Dict[str, Any]:
        """Cria usuário pelo endpoint existente POST /users."""
        return await self._inventory_request(
            "POST",
            "/users",
            auth_token,
            json_payload={
                "name": name,
                "email": email,
                "password": password,
                "confirm_password": confirm_password,
                "inventory_profile_id": inventory_profile_id,
            },
        )

    async def update_user(
        self,
        auth_token: str,
        user_id: int,
        *,
        name: str,
        email: str,
        inventory_profile_id: int,
    ) -> Dict[str, Any]:
        """Atualiza dados do usuário pelo endpoint existente PATCH /users/by_id/{user_id}."""
        return await self._inventory_request(
            "PATCH",
            f"/users/by_id/{user_id}",
            auth_token,
            json_payload={
                "name": name,
                "email": email,
                "inventory_profile_id": inventory_profile_id,
            },
        )

    async def reset_user_password(
        self, auth_token: str, user_id: int, password: str, confirm_password: str
    ) -> Dict[str, Any]:
        """Reseta a senha pelo endpoint existente PATCH /users/by_id/{user_id}/reset_password."""
        return await self._inventory_request(
            "PATCH",
            f"/users/by_id/{user_id}/reset_password",
            auth_token,
            json_payload={"password": password, "confirm_password": confirm_password},
        )

    async def activate_user(self, auth_token: str, user_id: int) -> Dict[str, Any]:
        """Ativa um usuário pelo endpoint existente PATCH /users/by_id/{user_id}/activate."""
        return await self._inventory_request(
            "PATCH", f"/users/by_id/{user_id}/activate", auth_token
        )

    async def inactivate_user(self, auth_token: str, user_id: int) -> Dict[str, Any]:
        """Inativa um usuário pelo endpoint existente PATCH /users/by_id/{user_id}/inactivate."""
        return await self._inventory_request(
            "PATCH", f"/users/by_id/{user_id}/inactivate", auth_token
        )

    async def list_products(
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 100,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta a listagem paginada de produtos com a sessão atual."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status in {"ativo", "inativo"}:
            params["status"] = status
        data = await self._inventory_request(
            "GET", "/products", auth_token, params=params
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
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 100,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status in {"ativo", "inativo"}:
            params["status"] = status
        data = await self._inventory_request(
            "GET",
            "/suppliers",
            auth_token,
            params=params,
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

    async def get_stock_insufficient_summary(
        self,
        auth_token: str,
        *,
        page: int = 1,
        per_page: int = 5,
    ) -> Dict[str, Any]:
        """Consulta o resumo limitado de Produtos ativos com estoque insuficiente."""
        if page < 1 or per_page < 1 or per_page > 20:
            raise ValueError("A página deve ser positiva e per_page deve estar entre 1 e 20.")
        data = await self._inventory_request(
            "GET",
            "/stock/insufficient_summary",
            auth_token,
            params={"page": page, "per_page": per_page},
            group_url=self.stock_group_url,
        )
        items = data.get("items")
        total = data.get("itemsTotal")
        current_page = data.get("curPage")
        page_size = data.get("perPage")
        if (
            not isinstance(items, list)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
            or total < len(items)
            or isinstance(current_page, bool)
            or not isinstance(current_page, int)
            or current_page != page
            or isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size != per_page
            or page_size > 20
            or len(items) > page_size
        ):
            raise XanoServerError(
                "O Xano retornou um resumo de estoque insuficiente em formato inesperado.",
                status_code=200,
            )
        return data

    async def get_purchase_requests_summary(self, auth_token: str) -> Dict[str, int]:
        """Consulta e valida a contagem global de solicitações abertas."""
        data = await self._inventory_request(
            "GET",
            "/purchase_requests/summary",
            auth_token,
            group_url=self.stock_group_url,
        )
        count = data.get("solicitacoes_abertas") if isinstance(data, dict) else None
        if type(count) is not int or count < 0:
            raise XanoServerError(
                "O Xano retornou uma contagem de solicitações abertas inválida.",
                status_code=200,
            )
        return {"solicitacoes_abertas": count}

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

    async def list_stock_replenishment(
        self,
        auth_token: str,
        *,
        page: int = 1,
        per_page: int = 20,
        requested_page: int = 1,
        requested_per_page: int = 20,
    ) -> Dict[str, Any]:
        """Consulta as duas listas paginadas pelo endpoint oficial de Reposição."""
        params = {
            "page": page,
            "per_page": per_page,
            "requested_page": requested_page,
            "requested_per_page": requested_per_page,
        }
        data = await self._inventory_request(
            "GET",
            "/stock/replenishment",
            auth_token,
            params=params,
            group_url=self.stock_group_url,
        )

        def contract_error(
            section: str,
            field: str,
            expected: str,
            found: Any = None,
            *,
            missing: bool = False,
        ) -> XanoServerError:
            # Log only schema names and types, never response values.
            error = XanoServerError(
                f"O Xano retornou {section}.{field} incompatible with the replenishment response contract.",
                status_code=200,
            )
            error.contract_section = section
            error.contract_field = field
            error.contract_expected = expected
            error.contract_found_type = "missing" if missing else type(found).__name__
            return error

        def validate_page(name: str) -> Dict[str, Any]:
            if name not in data:
                raise contract_error(name, "$", "object", missing=True)
            result = data[name]
            if not isinstance(result, dict):
                raise contract_error(name, "$", "object", result)
            if "items" not in result:
                raise contract_error(name, "items", "list", missing=True)
            items = result["items"]
            if not isinstance(items, list):
                raise contract_error(name, "items", "list", items)
            if any(not isinstance(item, dict) for item in items):
                invalid_item = next(item for item in items if not isinstance(item, dict))
                raise contract_error(name, "items[]", "object", invalid_item)

            paging: dict[str, int] = {}
            for field in ("curPage", "perPage", "itemsTotal"):
                if field not in result:
                    raise contract_error(name, field, "integer", missing=True)
                value = result[field]
                if type(value) is not int:  # Reject bool and numeric strings.
                    raise contract_error(name, field, "integer", value)
                paging[field] = value

            current_page = paging["curPage"]
            page_size = paging["perPage"]
            total = paging["itemsTotal"]
            if current_page < 1 or page_size < 1 or total < 0:
                field = "curPage" if current_page < 1 else "perPage" if page_size < 1 else "itemsTotal"
                raise contract_error(name, field, "valid pagination integer", result[field])
            return result

        return {
            "a_solicitar": validate_page("a_solicitar"),
            "compra_ja_solicitada": validate_page("compra_ja_solicitada"),
        }

    async def create_purchase_request(
        self,
        auth_token: str,
        *,
        produto_id: int,
        quantidade_solicitada: str,
        urgencia: str,
        chave_idempotencia: str,
        email_destinatario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria/reconcilia uma solicitação usando a chave da tentativa lógica."""
        try:
            quantity_value = float(quantidade_solicitada)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("A quantidade solicitada deve ser um número positivo.") from exc
        if not math.isfinite(quantity_value) or quantity_value <= 0:
            raise ValueError("A quantidade solicitada deve ser um número positivo finito.")
        normalized_email = normalize_purchase_request_email(email_destinatario, required=False)
        payload = {
            "produto_id": produto_id,
            "quantidade_solicitada": quantity_value,
            "urgencia": urgencia,
            "chave_idempotencia": chave_idempotencia,
        }
        if normalized_email is not None:
            payload["email_destinatario"] = normalized_email
        data = await self._inventory_request(
            "POST",
            "/purchase_requests",
            auth_token,
            json_payload=payload,
            group_url=self.stock_group_url,
        )
        request = data.get("solicitacao")
        request_id = request.get("id") if isinstance(request, dict) else None
        returned_product_id = request.get("produto_id") if isinstance(request, dict) else None
        allowed_statuses = {
            "aberta", "em_analise", "aprovada", "em_compra",
            "aguardando_recebimento", "recebimento_parcial", "concluida",
            "cancelada", "rejeitada",
        }
        if (
            isinstance(request_id, bool)
            or not isinstance(request_id, int)
            or request_id <= 0
            or type(returned_product_id) is not int
            or returned_product_id != produto_id
            or request.get("status") not in allowed_statuses
            or request.get("email_status") not in {"pendente", "enviado", "falhou"}
            or data.get("email_status") != request.get("email_status")
            or type(data.get("repeticao_idempotente")) is not bool
            or type(data.get("email_enviado")) is not bool
            or data.get("email_enviado") is not False
        ):
            raise XanoServerError(
                "O Xano respondeu, mas não confirmou o contrato da solicitação criada.",
                status_code=200,
            )
        return data

    async def cancel_purchase_request(
        self,
        auth_token: str,
        request_id: int,
        justificativa: str,
    ) -> Dict[str, Any]:
        """Cancela uma solicitação; autorização e transição são validadas no Xano."""
        data = await self._inventory_request(
            "PATCH",
            f"/purchase_requests/by_id/{request_id}/cancel",
            auth_token,
            json_payload={"justificativa": justificativa.strip()},
            group_url=self.stock_group_url,
        )
        request = data.get("solicitacao")
        returned_id = request.get("id") if isinstance(request, dict) else None
        if (
            isinstance(returned_id, bool)
            or not isinstance(returned_id, int)
            or returned_id != request_id
            or request.get("status") != "cancelada"
        ):
            raise XanoServerError(
                "O Xano respondeu, mas não confirmou o cancelamento da solicitação.",
                status_code=200,
            )
        return data

    async def list_movements(
        self,
        auth_token: str,
        page: int = 1,
        per_page: int = 20,
        tipo: Optional[str] = None,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None,
        date_from: Optional[int] = None,
        date_to: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Consulta uma página do histórico enriquecido no grupo Inventory Stock."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if tipo in {"entrada", "saida"}:
            params["tipo"] = tipo
        for name, value in (
            ("product_id", product_id),
            ("user_id", user_id),
            ("supplier_id", supplier_id),
        ):
            if value is None or value == "":
                continue
            try:
                numeric_id = int(value)
            except (TypeError, ValueError):
                continue
            if numeric_id <= 0:
                continue
            params[name] = numeric_id
        for name, value in (("date_from", date_from), ("date_to", date_to)):
            if value is None:
                continue
            try:
                params[name] = int(value)
            except (TypeError, ValueError):
                continue
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

    async def get_movements_summary(
        self,
        auth_token: str,
        *,
        date_from: Optional[int] = None,
        date_to: Optional[int] = None,
        tipo: Optional[str] = None,
        product_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Consulta o resumo completo do conjunto filtrado de movimentações."""
        params: Dict[str, Any] = {}
        if tipo in {"entrada", "saida"}:
            params["tipo"] = tipo
        for name, value in (("product_id", product_id), ("supplier_id", supplier_id)):
            if value is None or value == "":
                continue
            try:
                numeric_id = int(value)
            except (TypeError, ValueError):
                continue
            if numeric_id > 0:
                params[name] = numeric_id
        for name, value in (("date_from", date_from), ("date_to", date_to)):
            if value is None:
                continue
            try:
                params[name] = int(value)
            except (TypeError, ValueError):
                continue

        data = await self._inventory_request(
            "GET", "/movements_summary", auth_token, params=params, group_url=self.stock_group_url
        )
        try:
            total = int(data["total_movimentacoes"])
            entries = str(data["quantidade_entradas"])
            exits = str(data["quantidade_saidas"])
            float(entries)
            float(exits)
            return {
                "total_movimentacoes": total,
                "quantidade_entradas": entries,
                "quantidade_saidas": exits,
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise XanoServerError("O Xano retornou o resumo de movimentações em formato inesperado.") from exc

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

    async def list_report_options(
        self, auth_token: str, kind: str, page: int = 1, per_page: int = 100
    ) -> Dict[str, Any]:
        """Lista opções mínimas de produtos/fornecedores protegidas por report.read."""
        if kind not in {"product", "supplier"}:
            raise ValueError("O tipo de opção de relatório deve ser product ou supplier.")
        data = await self._inventory_request(
            "GET",
            "/report_options",
            auth_token,
            params={"kind": kind, "page": page, "per_page": per_page},
            group_url=self.stock_group_url,
        )
        if not isinstance(data.get("items"), list):
            raise XanoServerError("O Xano retornou opções de relatório em formato inesperado.")
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

    async def change_initial_password(
        self, auth_token: str, password: str, confirmation: str
    ) -> Dict[str, Any]:
        """Altera a senha inicial pela API autenticada existente do Xano."""
        try:
            data = await self._inventory_request(
                "PATCH",
                "/auth/change-initial-password",
                auth_token,
                json_payload={"password": password, "confirm_password": confirmation},
                group_url=self.auth_group_url,
            )
        except XanoPermissionError as exc:
            if _extract_xano_error_code(exc.payload) == "PASSWORD_CHANGE_NOT_REQUIRED":
                raise XanoRequestError(
                    "Não há troca de senha pendente para esta conta.",
                    "PASSWORD_CHANGE_NOT_REQUIRED",
                    exc.status_code or 403,
                    exc.payload,
                ) from exc
            raise

        if data.get("must_change_password") is not False:
            raise XanoServerError("O Xano retornou uma resposta inesperada ao alterar a senha.")
        return {"must_change_password": False}

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
            response = await self._send_request(
                "POST", url, json_payload=payload
            )
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
            if _extract_xano_error_code(error_payload) == "USER_INACTIVE":
                raise XanoAuthError(
                    "Sua conta foi inativada. Entre em contato com o Líder.",
                    status_code=response.status_code,
                    payload=error_payload,
                )
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
            retry_after=response.headers.get("Retry-After"),
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
            response = await self._send_request(
                "GET", url, headers=headers, auth_token=auth_token
            )
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
            if _extract_xano_error_code(error_payload) == "USER_INACTIVE":
                raise XanoAuthError(
                    "Sua conta foi inativada. Entre em contato com o Líder.",
                    status_code=response.status_code,
                    payload=error_payload,
                )
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
            retry_after=response.headers.get("Retry-After"),
        )


# Instância padrão compartilhada
auth_client = XanoAuthClient()
