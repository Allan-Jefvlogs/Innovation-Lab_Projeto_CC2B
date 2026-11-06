"""Leitura das listas autorizadas de reposicao de estoque."""

from __future__ import annotations

import os
import logging
import secrets
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Any

import reflex as rx

from ..components.layout import page, section
from ..services.purchase_request_email import (
    CANCELAMENTO_DESTINATARIO,
    enviar_email_cancelamento_compra,
    enviar_email_solicitacao_compra,
)
from ..services.session_read_cache import CACHE_MISS, session_read_cache
from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestError,
    XanoServerError,
    auth_client,
    normalize_purchase_request_email,
)
from ..state import AuthState


def _cache_ttl() -> float:
    try:
        return max(0.0, float(os.getenv("NEXSTOCK_REPLENISHMENT_CACHE_TTL_SECONDS", "15")))
    except (TypeError, ValueError):
        return 15.0


def _recipient_email_contract_enabled() -> bool:
    return os.getenv("NEXSTOCK_PURCHASE_REQUEST_EMAIL_ENABLED", "false").strip().lower() == "true"


REPLENISHMENT_CACHE_TTL = _cache_ttl()
REPLENISHMENT_PAGE_SIZE = 20
REPLENISHMENT_ENDPOINT = "GET /stock/replenishment"
REPLENISHMENT_SCOPE = "stock.read+purchase_request.read"
PURCHASE_REQUEST_SUMMARY_ENDPOINT = "GET /purchase_requests/summary"
PURCHASE_REQUEST_LIST_ENDPOINT = "GET /purchase_requests"
URGENCY_CODES = {
    "Baixa": "baixa",
    "Normal": "normal",
    "Alta": "alta",
    "Crítica": "critica",
}
logger = logging.getLogger(__name__)
URGENCY_OPTIONS = ["Baixa", "Normal", "Alta", "Crítica"]
SITUATION_LABELS = {
    "sem_estoque": "Sem estoque",
    "abaixo_minimo": "Abaixo do mínimo",
}


def _format_quantity(value: object) -> str:
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return "—"
        return format(number.normalize(), "f").replace(".", ",")
    except (InvalidOperation, TypeError, ValueError):
        return "—"


def _format_request_date(value: object) -> str:
    if value in (None, ""):
        return "—"
    try:
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return "—"


def _retry_delay_seconds(error: Exception) -> float:
    if isinstance(error, XanoRateLimitError):
        return max(0.0, float(error.retry_after_seconds))
    retry_after = getattr(error, "retry_after", None)
    if retry_after:
        try:
            return max(0.0, float(str(retry_after).strip()))
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(retry_after))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, retry_at.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return max(
        20.0,
        float(getattr(getattr(auth_client, "coordinator", None), "window_seconds", 20.0)),
    )


def _read_error_origin(error: Exception) -> str:
    if isinstance(error, XanoRateLimitError):
        return "local_coordinator"
    if isinstance(error, XanoRequestError) and error.status_code == 429:
        return "remote_xano"
    if isinstance(error, XanoConnectionError):
        return "network_transport"
    if isinstance(error, XanoAuthError):
        return "authentication"
    if isinstance(error, XanoPermissionError):
        return "authorization"
    if isinstance(error, (KeyError, TypeError, ValueError)):
        return "response_contract"
    if getattr(error, "status_code", None) == 200:
        return "response_contract"
    if isinstance(getattr(error, "status_code", None), int):
        return "remote_xano"
    return "client_or_state"


def _log_read_failure(error: Exception) -> None:
    origin = _read_error_origin(error)
    status = getattr(error, "status_code", None)
    if status is None and origin == "response_contract":
        status = 200
    logger.warning(
        "Replenishment read failed: endpoint=%s status=%s exception_type=%s origin=%s "
        "contract_section=%s contract_field=%s expected=%s found_type=%s",
        REPLENISHMENT_ENDPOINT,
        status,
        type(error).__name__,
        origin,
        getattr(error, "contract_section", "-"),
        getattr(error, "contract_field", "-"),
        getattr(error, "contract_expected", "-"),
        getattr(error, "contract_found_type", "-"),
    )


def suggested_purchase_quantity(current: object, minimum: object) -> str:
    try:
        balance = Decimal(str(current))
        threshold = Decimal(str(minimum))
        if not balance.is_finite() or not threshold.is_finite() or balance < 0 or threshold < 0:
            return ""
        if balance == 0 and threshold == 0:
            return "1"
        deficit = threshold - balance
        return format(deficit.normalize(), "f") if deficit > 0 else ""
    except (InvalidOperation, TypeError, ValueError):
        return ""


def _normalize_positive_quantity(value: str) -> str | None:
    try:
        number = Decimal(str(value).strip().replace(",", "."))
        if not number.is_finite() or number <= 0:
            return None
        return format(number.normalize(), "f")
    except (InvalidOperation, TypeError, ValueError):
        return None


def _invalidate_purchase_reads(token: str) -> None:
    for endpoint in (
        REPLENISHMENT_ENDPOINT,
        PURCHASE_REQUEST_LIST_ENDPOINT,
        PURCHASE_REQUEST_SUMMARY_ENDPOINT,
    ):
        session_read_cache.invalidate(endpoint=endpoint, token=token)


def _write_is_ambiguous(error: Exception) -> bool:
    if isinstance(error, XanoRateLimitError):
        return False  # O coordenador local rejeitou antes do envio HTTP.
    if isinstance(error, (XanoConnectionError, XanoServerError)):
        return True
    if isinstance(error, XanoRequestError):
        return error.status_code == 429 or error.status_code >= 500
    return not isinstance(error, (XanoAuthError, XanoPermissionError, ValueError))


def _map_item(item: dict[str, Any], *, requested: bool) -> dict[str, str]:
    row = {
        "id": str(item.get("produto_id") or ""),
        "codigo": str(item.get("codigo") or "—"),
        "produto": str(item.get("nome") or "Produto sem nome"),
        "unidade": str(item.get("unidade_medida") or ""),
        "estoque_atual": _format_quantity(item.get("quantidade_disponivel")),
        "estoque_minimo": _format_quantity(item.get("estoque_minimo")),
        "situacao": str(item.get("situacao_estoque") or ""),
        "situacao_label": SITUATION_LABELS.get(
            str(item.get("situacao_estoque") or ""), "Situação desconhecida"
        ),
        # A linha veio da lista elegível do servidor; revalidação ainda ocorre no POST.
        "eligible": "true",
        "quantidade_raw": str(item.get("quantidade_disponivel", "")),
        "estoque_minimo_raw": str(item.get("estoque_minimo", "")),
    }
    if requested:
        row.update(
            {
                "solicitacao_id": str(item.get("solicitacao_id") or ""),
                "quantidade_solicitada": _format_quantity(item.get("quantidade_solicitada")),
                "urgencia": str(item.get("urgencia") or item.get("urgencia_solicitacao") or "\u2014"),
                "status": str(item.get("solicitacao_status") or "—"),
                "data_solicitacao": _format_request_date(item.get("data_criacao_solicitacao")),
            }
        )
    return row


class ReplenishmentState(rx.State):
    """Carrega as duas listas em uma chamada, preservando paginação independente."""

    requestable_status: str = "loading"
    requested_status: str = "loading"
    error_message: str = ""
    integration_available: bool = False
    data_stale: bool = False
    retry_available: bool = False
    retry_after_epoch: float = 0.0
    load_attempted: bool = False
    is_loading: bool = False
    active_tab: str = "to_request"
    requestable_products: list[dict[str, str]] = []
    requested_products: list[dict[str, str]] = []
    requestable_page: int = 1
    requested_page: int = 1
    page_size: int = REPLENISHMENT_PAGE_SIZE
    requestable_total: int = 0
    requested_total: int = 0
    requestable_page_total: int = 1
    requested_page_total: int = 1
    can_create_request: bool = False
    can_cancel_requests: bool = False
    request_form_open: bool = False
    request_product_id: str = ""
    request_product_code: str = ""
    request_product_name: str = ""
    request_product_unit: str = ""
    request_quantity: str = ""
    request_urgency: str = "Normal"
    request_recipient_email: str = ""
    request_email_contract_enabled: bool = False
    request_create_error: str = ""
    request_success_message: str = ""
    request_submission_in_progress: bool = False
    request_attempt_key: str = ""
    request_attempt_signature: str = ""
    request_attempt_ambiguous: bool = False
    request_retry_after_epoch: float = 0.0
    cancel_form_open: bool = False
    cancel_request_id: str = ""
    cancel_product_label: str = ""
    cancel_justification: str = ""
    cancel_error_message: str = ""
    cancel_success_message: str = ""
    cancel_submission_in_progress: bool = False
    cancel_attempt_ambiguous: bool = False
    cancel_retry_after_epoch: float = 0.0
    session_fingerprint_cache: str = ""

    @rx.var
    def cancel_justification_valid(self) -> bool:
        return bool(self.cancel_justification.strip())

    def _set_status(self, status: str) -> None:
        self.requestable_status = status
        self.requested_status = status

    async def _clear_for_session_change(self, token: str) -> None:
        fingerprint = session_read_cache.session_fingerprint(token) if token else ""
        if fingerprint != self.session_fingerprint_cache:
            self.requestable_products = []
            self.requested_products = []
            self.requestable_total = 0
            self.requested_total = 0
            self.can_create_request = False
            self.can_cancel_requests = False
            self.integration_available = False
            self.data_stale = False
            self.request_form_open = False
            self.request_product_id = ""
            self.request_product_code = ""
            self.request_product_name = ""
            self.request_product_unit = ""
            self.request_quantity = ""
            self.request_urgency = "Normal"
            self.request_recipient_email = ""
            self.request_email_contract_enabled = False
            self.request_create_error = ""
            self.request_success_message = ""
            self.request_submission_in_progress = False
            self.request_attempt_key = ""
            self.request_attempt_signature = ""
            self.request_attempt_ambiguous = False
            self.request_retry_after_epoch = 0.0
            self.cancel_form_open = False
            self.cancel_request_id = ""
            self.cancel_product_label = ""
            self.cancel_justification = ""
            self.cancel_error_message = ""
            self.cancel_success_message = ""
            self.cancel_submission_in_progress = False
            self.cancel_attempt_ambiguous = False
            self.cancel_retry_after_epoch = 0.0
            self.session_fingerprint_cache = fingerprint

    def _cache_key(self, token: str) -> tuple[str, str, str, str]:
        return session_read_cache.key(
            REPLENISHMENT_SCOPE,
            REPLENISHMENT_ENDPOINT,
            token,
            {
                "page": self.requestable_page,
                "per_page": self.page_size,
                "requested_page": self.requested_page,
                "requested_per_page": self.page_size,
            },
        )

    async def load_page(self):
        if self.is_loading or (self.load_attempted and self.retry_available):
            return
        self.requestable_page = 1
        self.requested_page = 1
        async for event in self._load_data(False):
            yield event

    async def _load_data(self, force_refresh: bool = False):
        if self.is_loading:
            return
        self.is_loading = True
        self.error_message = ""
        self.retry_available = False
        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()
        if redirect is not None:
            self.is_loading = False
            yield redirect
            return
        if not auth.session_is_valid:
            await self._clear_for_session_change("")
            self.integration_available = False
            self._set_status("error")
            self.error_message = auth.session_status_message or "Não foi possível validar a sessão."
            self.retry_available = auth.session_validation in {
                "temporarily_unavailable", "forbidden"
            }
            self.is_loading = False
            yield
            return

        token = str(auth.auth_token or "").strip()
        await self._clear_for_session_change(token)
        required = auth.has_permission("stock.read") and auth.has_permission("purchase_request.read")
        self.can_create_request = required and auth.has_permission("purchase_request.create")
        self.can_cancel_requests = required and (
            auth.has_permission("purchase_request.cancel")
            or auth.has_permission("purchase_request.manage")
        )
        if not required:
            self.requestable_products = []
            self.requested_products = []
            self.requestable_total = 0
            self.requested_total = 0
            self.data_stale = False
            self.can_create_request = False
            self.can_cancel_requests = False
            self.integration_available = False
            self._set_status("access_denied")
            self.error_message = "Você não possui as permissões necessárias para visualizar a reposição."
            self.is_loading = False
            yield rx.redirect("/dashboard")
            return

        self.load_attempted = True
        key = self._cache_key(token)
        cached, fresh = session_read_cache.get(key, REPLENISHMENT_CACHE_TTL, allow_stale=True)
        if fresh and not force_refresh:
            self._apply_response(cached)
            self.data_stale = False
            self._set_ready_status()
            self.integration_available = True
            self.is_loading = False
            yield
            return

        self.is_loading = True
        yield
        try:
            response = await auth_client.list_stock_replenishment(
                token,
                page=self.requestable_page,
                per_page=self.page_size,
                requested_page=self.requested_page,
                requested_per_page=self.page_size,
            )
            self._apply_response(response)
            session_read_cache.set(key, response, REPLENISHMENT_CACHE_TTL)
            self.integration_available = True
            self.data_stale = False
            self.retry_after_epoch = 0.0
            self._set_ready_status()
            self.error_message = ""
        except XanoAuthError as exc:
            _log_read_failure(exc)
            # 401 means the API has rejected the session; do not retain private rows.
            self.requestable_products = []
            self.requested_products = []
            self.requestable_total = 0
            self.requested_total = 0
            self.integration_available = False
            self.error_message = exc.message or "Sua sessão expirou. Entre novamente."
            self._set_status("error")
            yield auth.logout()
            return
        except XanoPermissionError as exc:
            _log_read_failure(exc)
            session_read_cache.invalidate(endpoint=REPLENISHMENT_ENDPOINT, token=token)
            self.requestable_products = []
            self.requested_products = []
            self.requestable_total = 0
            self.requested_total = 0
            self.integration_available = False
            self.data_stale = False
            self.error_message = "O servidor não autorizou a consulta de reposição."
            self._set_status("access_denied")
            self.retry_available = False
        except XanoRequestError as exc:
            _log_read_failure(exc)
            if exc.status_code == 404:
                self.integration_available = False
                self.data_stale = False
                self._set_status("unavailable")
                self.error_message = "O endpoint de reposição não está disponível no ambiente publicado."
                self.retry_available = True
            else:
                self._handle_read_error(exc, cached, token)
        except (XanoConnectionError, XanoServerError, XanoError) as exc:
            _log_read_failure(exc)
            self._handle_read_error(exc, cached, token)
        except Exception as exc:
            _log_read_failure(exc)
            self.integration_available = False
            self.data_stale = False
            self._set_status("error")
            self.error_message = (
                "O Xano respondeu, mas os dados de reposição vieram em formato inesperado."
                if _read_error_origin(exc) == "response_contract"
                else "Não foi possível carregar a reposição. Tente novamente."
            )
            self.retry_available = True
        finally:
            self.is_loading = False
        yield

    def _apply_response(self, response: dict[str, Any]) -> None:
        requestable = response["a_solicitar"]
        requested = response["compra_ja_solicitada"]
        self.requestable_products = [
            _map_item(item, requested=False)
            for item in requestable["items"]
            if isinstance(item, dict)
        ]
        self.requested_products = [
            _map_item(item, requested=True)
            for item in requested["items"]
            if isinstance(item, dict)
        ]
        self.requestable_page = int(requestable["curPage"])
        self.requested_page = int(requested["curPage"])
        self.requestable_total = int(requestable["itemsTotal"])
        self.requested_total = int(requested["itemsTotal"])
        self.requestable_page_total = max(
            1, (self.requestable_total + int(requestable["perPage"]) - 1) // int(requestable["perPage"])
        )
        self.requested_page_total = max(
            1, (self.requested_total + int(requested["perPage"]) - 1) // int(requested["perPage"])
        )

    def _set_ready_status(self) -> None:
        self.requestable_status = "ready" if self.requestable_total else "empty"
        self.requested_status = "ready" if self.requested_total else "empty"

    def _handle_read_error(self, error: Exception, cached: Any, token: str) -> None:
        self.retry_available = True
        status_code = getattr(error, "status_code", None)
        if status_code == 429:
            self.retry_after_epoch = max(
                self.retry_after_epoch, time.time() + _retry_delay_seconds(error)
            )
        temporary = isinstance(error, (XanoConnectionError, XanoRateLimitError)) or (
            isinstance(status_code, int) and (status_code == 429 or status_code >= 500)
        )
        if cached is not CACHE_MISS and temporary:
            self._apply_response(cached)
            self.data_stale = True
            self.integration_available = True
            self._set_ready_status()
            self.error_message = "A consulta não foi atualizada; os dados exibidos podem estar desatualizados."
            return
        self.data_stale = False
        self.integration_available = False
        self._set_status("error")
        if status_code == 429:
            delay = max(1, int(self.retry_after_epoch - time.time() + 0.999))
            origin = _read_error_origin(error)
            if origin == "local_coordinator":
                self.error_message = (
                    f"Limite local de solicitações atingido. Aguarde {delay} segundo(s) e tente novamente."
                )
            else:
                self.error_message = (
                    f"O Xano está limitando as solicitações. Aguarde {delay} segundo(s) e tente novamente."
                )
        elif isinstance(error, XanoConnectionError):
            self.error_message = "Não foi possível conectar ao Xano. Verifique a conexão e tente novamente."
        elif status_code == 200:
            self.error_message = "O Xano respondeu, mas os dados de reposição vieram em formato inesperado."
        elif isinstance(status_code, int) and status_code >= 500:
            self.error_message = "O Xano encontrou uma falha ao consultar a reposição. Tente novamente mais tarde."
        else:
            self.error_message = "Não foi possível carregar a reposição. Tente novamente."

    async def retry_session_or_data(self):
        if self.is_loading:
            return
        remaining = self.retry_after_epoch - time.time()
        if remaining > 0:
            self.error_message = (
                f"Aguarde pelo menos {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
            )
            return
        auth = await self.get_state(AuthState)
        if not auth.session_is_valid:
            remaining = auth.session_retry_after_epoch - time.time()
            if remaining > 0:
                self.error_message = (
                    f"Aguarde pelo menos {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
                )
                return
            if not await auth.restore_session(force=True):
                self.error_message = auth.session_status_message or "A sessão continua indisponível."
                self.retry_available = auth.session_validation in {
                    "temporarily_unavailable", "forbidden"
                }
                return
        async for event in self._load_data(True):
            yield event

    def select_tab(self, tab: str):
        if tab in {"to_request", "requested"}:
            self.active_tab = tab

    async def load_requestable_page(self, page_number: int):
        if 1 <= page_number <= self.requestable_page_total and page_number != self.requestable_page:
            self.requestable_page = page_number
            async for event in self._load_data(False):
                yield event

    async def load_requested_page(self, page_number: int):
        if 1 <= page_number <= self.requested_page_total and page_number != self.requested_page:
            self.requested_page = page_number
            async for event in self._load_data(False):
                yield event

    async def open_request_form(
        self,
        product_id: str,
        code: str = "",
        name: str = "",
        current: str = "0",
        minimum: str = "0",
        unit: str = "",
        product_active: str = "true",
        balance_registered: str = "true",
    ):
        auth = await self.get_state(AuthState)
        if not auth.session_is_valid or not auth.has_permission("purchase_request.create"):
            self.request_form_open = False
            return
        if self.request_attempt_ambiguous:
            if self.request_product_id == str(product_id):
                self.request_form_open = True
            else:
                self.request_create_error = (
                    "Resolva primeiro a tentativa anterior com a mesma chave de idempotência."
                )
            return
        if self.data_stale or self.requestable_status != "ready" or not self.integration_available:
            self.request_form_open = False
            return
        if product_active.lower() != "true" or balance_registered.lower() != "true":
            self.request_form_open = False
            return
        product = next(
            (row for row in self.requestable_products if row["id"] == str(product_id)), None
        )
        if not product or product.get("eligible") != "true":
            self.request_form_open = False
            return
        self.request_product_id = product["id"]
        self.request_product_code = product["codigo"]
        self.request_product_name = product["produto"]
        self.request_product_unit = product["unidade"]
        raw_current = product["quantidade_raw"]
        raw_minimum = product["estoque_minimo_raw"]
        self.request_quantity = suggested_purchase_quantity(raw_current, raw_minimum)
        self.request_urgency = "Normal"
        self.request_recipient_email = ""
        self.request_email_contract_enabled = _recipient_email_contract_enabled()
        self.request_create_error = ""
        self.request_success_message = ""
        self.request_form_open = bool(self.request_quantity)

    def change_request_quantity(self, value: str) -> None:
        self.request_quantity = value
        if not self.request_attempt_ambiguous:
            self.request_attempt_key = ""
            self.request_attempt_signature = ""
            self.request_create_error = ""

    def change_request_urgency(self, value: str) -> None:
        if value in URGENCY_OPTIONS and not self.request_attempt_ambiguous:
            self.request_urgency = value
            self.request_attempt_key = ""
            self.request_attempt_signature = ""
            self.request_create_error = ""

    def change_request_recipient_email(self, value: str) -> None:
        self.request_recipient_email = value
        if not self.request_attempt_ambiguous:
            self.request_attempt_key = ""
            self.request_attempt_signature = ""
            self.request_create_error = ""

    def _clear_request_attempt(self) -> None:
        self.request_attempt_key = ""
        self.request_attempt_signature = ""
        self.request_attempt_ambiguous = False
        self.request_retry_after_epoch = 0.0

    def _clear_request_form(self) -> None:
        self.request_form_open = False
        self.request_product_id = ""
        self.request_product_code = ""
        self.request_product_name = ""
        self.request_product_unit = ""
        self.request_quantity = ""
        self.request_urgency = "Normal"
        self.request_recipient_email = ""
        self._clear_request_attempt()

    def cancel_request_form(self) -> None:
        if self.request_submission_in_progress:
            return
        if self.request_attempt_ambiguous:
            # Closing the modal must not discard an attempt whose POST outcome
            # is uncertain. Reopening this product keeps the exact payload/key.
            self.request_form_open = False
            return
        self._clear_request_form()
        self.request_create_error = ""

    async def submit_purchase_request(self):
        if self.request_submission_in_progress:
            return
        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()
        if redirect is not None:
            yield redirect
            return
        if not auth.session_is_valid:
            self.request_create_error = auth.session_status_message or "Valide sua sessão antes de continuar."
            yield
            return
        if not auth.has_permission("purchase_request.create"):
            self.can_create_request = False
            self.request_create_error = "Você não possui a permissão para criar solicitações de compra."
            yield
            return
        if self.data_stale or not self.integration_available or not self.request_product_id:
            self.request_create_error = "Atualize a reposição antes de enviar esta solicitação."
            yield
            return

        quantity = _normalize_positive_quantity(self.request_quantity)
        urgency_code = URGENCY_CODES.get(self.request_urgency)
        try:
            product_id = int(self.request_product_id)
        except (TypeError, ValueError):
            product_id = 0
        try:
            recipient_email = normalize_purchase_request_email(
                self.request_recipient_email,
                required=self.request_email_contract_enabled,
            )
        except ValueError:
            self.request_create_error = "Informe um e-mail de destinatário válido."
            yield
            return
        if product_id <= 0 or quantity is None or urgency_code is None:
            self.request_create_error = "Confira a quantidade positiva, a urgência e o e-mail exigido pela integração ativa."
            yield
            return

        signature = f"{product_id}|{quantity}|{urgency_code}|{recipient_email or ''}"
        if self.request_attempt_ambiguous and signature != self.request_attempt_signature:
            self.request_create_error = (
                "A resposta anterior é incerta. Mantenha os mesmos dados e use a mesma tentativa."
            )
            yield
            return
        remaining = self.request_retry_after_epoch - time.time()
        if remaining > 0:
            self.request_create_error = (
                f"Aguarde {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
            )
            yield
            return

        if not self.request_attempt_key:
            self.request_attempt_key = secrets.token_urlsafe(32)
            self.request_attempt_signature = signature
        self.request_submission_in_progress = True
        self.request_create_error = ""
        self.request_success_message = ""
        yield

        try:
            create_payload = {
                "produto_id": product_id,
                "quantidade_solicitada": quantity,
                "urgencia": urgency_code,
                "chave_idempotencia": self.request_attempt_key,
            }
            if self.request_email_contract_enabled:
                create_payload["email_destinatario"] = recipient_email
            result = await auth_client.create_purchase_request(
                str(auth.auth_token or "").strip(),
                **create_payload,
            )
        except XanoAuthError as exc:
            self.request_submission_in_progress = False
            self._clear_request_attempt()
            self._clear_request_form()
            self.request_create_error = exc.message or "Sua sessão expirou. Entre novamente."
            yield auth.logout()
            return
        except XanoPermissionError:
            self.request_submission_in_progress = False
            self._clear_request_attempt()
            self.request_create_error = "Você não possui permissão para criar solicitações."
            yield
            return
        except Exception as exc:
            self.request_submission_in_progress = False
            self.request_attempt_ambiguous = _write_is_ambiguous(exc)
            status_code = getattr(exc, "status_code", None)
            if status_code == 429 or isinstance(exc, XanoRateLimitError):
                self.request_retry_after_epoch = time.time() + _retry_delay_seconds(exc)
            if isinstance(exc, XanoRequestError):
                self.request_create_error = (
                    "Somente produtos ativos podem receber solicitação de compra."
                    if exc.error_code == "PRODUCT_INACTIVE"
                    else exc.message
                )
                if not self.request_attempt_ambiguous:
                    self._clear_request_attempt()
            elif isinstance(exc, XanoConnectionError):
                self.request_create_error = (
                    "A conexão falhou e o resultado pode ser incerto. Tente novamente manualmente; "
                    "a mesma chave será reutilizada."
                )
            elif isinstance(exc, XanoRateLimitError):
                self.request_create_error = exc.message
            elif isinstance(exc, ValueError):
                self._clear_request_attempt()
                self.request_create_error = "A quantidade não pode ser enviada nesse formato; ajuste o valor."
            else:
                self.request_create_error = (
                    "Não foi possível confirmar o resultado. Não inicie outra solicitação; "
                    "uma nova tentativa manterá a mesma chave."
                )
            yield
            return

        self.request_submission_in_progress = False
        request = result["solicitacao"]
        was_repeat = result["repeticao_idempotente"]
        email_status = result["email_status"]
        email_detail = {
            "pendente": "E-mail pendente; nenhum e-mail foi enviado nesta etapa.",
            "falhou": "O envio de e-mail está sinalizado como falho; a solicitação permanece registrada.",
            "enviado": "O backend informa que o e-mail foi enviado.",
        }[email_status]
        if recipient_email:
            sent = await enviar_email_solicitacao_compra(
                destinatario=recipient_email,
                solicitacao_id=request["id"],
                codigo=self.request_product_code,
                nome=self.request_product_name,
                quantidade=quantity,
                unidade=self.request_product_unit,
                urgencia=self.request_urgency,
                usuario=getattr(auth, "user_name", ""),
            )
            email_detail = (
                f"E-mail enviado para {recipient_email}."
                if sent
                else f"Não foi possível enviar o e-mail para {recipient_email}; a solicitação permanece registrada."
            )
        _invalidate_purchase_reads(str(auth.auth_token or "").strip())
        self.request_success_message = (
            f"Solicitação {request['id']} já estava registrada. Status: {request['status']}. {email_detail}"
            if was_repeat
            else f"Solicitação {request['id']} registrada. Status: {request['status']}. {email_detail}"
        )
        self.request_create_error = ""
        self._clear_request_form()
        self.requestable_page = 1
        self.requested_page = 1
        yield
        async for event in self._load_data(True):
            yield event

    async def open_cancel_request_form(self, request_id: str):
        auth = await self.get_state(AuthState)
        if not auth.session_is_valid:
            return
        if not (
            auth.has_permission("purchase_request.cancel")
            or auth.has_permission("purchase_request.manage")
        ):
            self.cancel_error_message = "Você não possui permissão para cancelar solicitações."
            return
        if self.cancel_attempt_ambiguous and self.cancel_request_id != str(request_id):
            self.cancel_error_message = "Resolva primeiro o cancelamento anterior antes de iniciar outro."
            return
        row = next(
            (item for item in self.requested_products if item.get("solicitacao_id") == str(request_id)),
            None,
        )
        if not row or row.get("status") not in {"aberta", "em_analise"}:
            self.cancel_error_message = "O status atual não permite cancelar esta solicitação."
            return
        if not self.cancel_attempt_ambiguous:
            self.cancel_request_id = str(request_id)
            self.cancel_justification = ""
            self.cancel_product_label = f"{row.get('codigo', '')} — {row.get('produto', '')}"
            self.cancel_error_message = ""
            self.cancel_success_message = ""
        self.cancel_form_open = True

    def change_cancel_justification(self, value: str) -> None:
        if not self.cancel_submission_in_progress and not self.cancel_attempt_ambiguous:
            self.cancel_justification = value

    def dismiss_cancel_form(self) -> None:
        if self.cancel_submission_in_progress:
            return
        self.cancel_form_open = False
        if not self.cancel_attempt_ambiguous:
            self.cancel_request_id = ""
            self.cancel_product_label = ""
            self.cancel_justification = ""
            self.cancel_error_message = ""

    def _clear_cancel_attempt(self) -> None:
        self.cancel_attempt_ambiguous = False
        self.cancel_retry_after_epoch = 0.0

    async def confirm_cancel_request(self):
        if self.cancel_submission_in_progress:
            return
        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()
        if redirect is not None:
            yield redirect
            return
        if not auth.session_is_valid:
            self.cancel_error_message = auth.session_status_message or "Valide sua sessão antes de continuar."
            yield
            return
        if not (
            auth.has_permission("purchase_request.cancel")
            or auth.has_permission("purchase_request.manage")
        ):
            self.cancel_error_message = "Você não possui permissão para cancelar solicitações."
            yield
            return
        justification = self.cancel_justification.strip()
        try:
            request_id = int(self.cancel_request_id)
        except (TypeError, ValueError):
            request_id = 0
        if request_id <= 0 or not justification:
            self.cancel_error_message = "Informe uma justificativa antes de confirmar."
            yield
            return
        remaining = self.cancel_retry_after_epoch - time.time()
        if remaining > 0:
            self.cancel_error_message = f"Aguarde {int(remaining + 0.999)} segundo(s) antes de tentar novamente."
            yield
            return

        self.cancel_submission_in_progress = True
        self.cancel_error_message = ""
        self.cancel_success_message = ""
        yield
        already_cancelled = False
        try:
            result = await auth_client.cancel_purchase_request(
                str(auth.auth_token or "").strip(), request_id, justification
            )
        except XanoAuthError as exc:
            self.cancel_submission_in_progress = False
            self._clear_cancel_attempt()
            self.dismiss_cancel_form()
            yield auth.logout()
            return
        except XanoPermissionError:
            self.cancel_submission_in_progress = False
            self._clear_cancel_attempt()
            self.cancel_error_message = "Você não possui permissão para cancelar esta solicitação."
            yield
            return
        except Exception as exc:
            self.cancel_submission_in_progress = False
            if isinstance(exc, XanoRequestError) and exc.error_code == "PURCHASE_REQUEST_ALREADY_CANCELLED":
                already_cancelled = True
                result = {"solicitacao": {"id": request_id, "status": "cancelada"}}
            else:
                self.cancel_attempt_ambiguous = _write_is_ambiguous(exc)
                status_code = getattr(exc, "status_code", None)
                if status_code == 429 or isinstance(exc, XanoRateLimitError):
                    self.cancel_retry_after_epoch = time.time() + _retry_delay_seconds(exc)
                if isinstance(exc, XanoRequestError):
                    self.cancel_error_message = exc.message
                    if not self.cancel_attempt_ambiguous:
                        self._clear_cancel_attempt()
                elif isinstance(exc, XanoConnectionError):
                    self.cancel_error_message = (
                        "A conexão falhou; não foi possível confirmar o cancelamento. "
                        "Tente novamente manualmente após verificar o resultado."
                    )
                elif isinstance(exc, XanoRateLimitError):
                    self.cancel_error_message = exc.message
                else:
                    self.cancel_error_message = (
                        "Não foi possível confirmar o cancelamento. Uma nova tentativa manual "
                        "reconsultará o estado no Xano antes de alterar o pedido."
                    )
                yield
                return

        self.cancel_submission_in_progress = False
        _invalidate_purchase_reads(str(auth.auth_token or "").strip())
        self.cancel_success_message = (
            "A solicitação já estava cancelada. As listas foram atualizadas; o estoque não foi alterado."
            if already_cancelled
            else "Solicitação cancelada. O estoque não foi alterado."
        )
        if not already_cancelled:
            sent = await enviar_email_cancelamento_compra(
                solicitacao_id=request_id,
                produto=self.cancel_product_label,
                justificativa=justification,
                usuario=getattr(auth, "user_name", ""),
            )
            self.cancel_success_message += (
                f" Aviso enviado para {CANCELAMENTO_DESTINATARIO}."
                if sent
                else " Não foi possível enviar o e-mail de aviso."
            )
        self.cancel_error_message = ""
        self.cancel_form_open = False
        self.cancel_request_id = ""
        self.cancel_product_label = ""
        self.cancel_justification = ""
        self._clear_cancel_attempt()
        self.requestable_page = 1
        self.requested_page = 1
        yield
        async for event in self._load_data(True):
            yield event


def _status_panel(status: rx.Var, message: rx.Var) -> rx.Component:
    return rx.cond(
        status == "loading",
        rx.center(rx.spinner(), "Carregando dados de reposição...", width="100%", padding="2rem"),
        rx.cond(
            status == "unavailable",
            rx.text("Integração de reposição indisponível.", color="#64748b", role="status"),
            rx.cond(
                status == "access_denied",
                rx.text(message, color="#b91c1c", role="alert"),
                rx.cond(
                    status == "error",
                    rx.hstack(
                        rx.text(message, color="#b91c1c", role="alert"),
                        _retry_action(),
                        width="100%",
                        align="center",
                        spacing="2",
                        wrap="wrap",
                    ),
                    rx.fragment(),
                ),
            ),
        ),
    )


def _retry_action() -> rx.Component:
    return rx.cond(
        ReplenishmentState.retry_available,
        rx.button(
            "Tentar novamente",
            on_click=ReplenishmentState.retry_session_or_data,
            disabled=ReplenishmentState.is_loading,
            size="1",
            variant="ghost",
            color_scheme="blue",
            padding="0 6px",
            flex_shrink="0",
        ),
        rx.fragment(),
    )


def _request_form() -> rx.Component:
    return rx.cond(
        ReplenishmentState.request_form_open,
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Solicitar compra"),
                rx.vstack(
                    rx.text("Produto"),
                    rx.input(value=ReplenishmentState.request_product_name, read_only=True),
                    rx.text("Quantidade solicitada"),
                    rx.input(
                        value=ReplenishmentState.request_quantity,
                        on_change=ReplenishmentState.change_request_quantity,
                        type="number",
                        min="0.0000000001",
                        step="any",
                        disabled=ReplenishmentState.request_submission_in_progress
                        | ReplenishmentState.request_attempt_ambiguous,
                    ),
                    rx.text(
                        "Unidade: ",
                        ReplenishmentState.request_product_unit,
                        size="2",
                        color="#64748b",
                    ),
                    rx.text("Urgência"),
                    rx.select(
                        URGENCY_OPTIONS,
                        value=ReplenishmentState.request_urgency,
                        on_change=ReplenishmentState.change_request_urgency,
                        disabled=ReplenishmentState.request_submission_in_progress
                        | ReplenishmentState.request_attempt_ambiguous,
                    ),
                    rx.text("E-mail do destinatário"),
                    rx.input(
                        value=ReplenishmentState.request_recipient_email,
                        on_change=ReplenishmentState.change_request_recipient_email,
                        type="email",
                        placeholder="exemplo@empresa.com.br",
                        required=ReplenishmentState.request_email_contract_enabled,
                        disabled=ReplenishmentState.request_submission_in_progress
                        | ReplenishmentState.request_attempt_ambiguous,
                        max_length=254,
                    ),
                    rx.text(
                        "Se preenchido, a solicitação será enviada por e-mail ao endereço informado.",
                        size="2",
                        color="#64748b",
                    ),
                    rx.cond(
                        ReplenishmentState.request_create_error != "",
                        rx.text(ReplenishmentState.request_create_error, color="#b91c1c", role="alert"),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                ReplenishmentState.request_attempt_ambiguous,
                                "Tentar novamente com a mesma tentativa",
                                "Enviar pedido",
                            ),
                            on_click=ReplenishmentState.submit_purchase_request,
                            disabled=(~ReplenishmentState.can_create_request)
                            | ReplenishmentState.request_submission_in_progress,
                        ),
                        rx.button(
                            rx.cond(
                                ReplenishmentState.request_attempt_ambiguous,
                                "Fechar e manter tentativa",
                                "Cancelar solicitação",
                            ),
                            on_click=ReplenishmentState.cancel_request_form,
                            variant="soft",
                            disabled=ReplenishmentState.request_submission_in_progress,
                        ),
                        justify="end",
                        width="100%",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
            open=ReplenishmentState.request_form_open,
        ),
        rx.fragment(),
    )


def _cancel_form() -> rx.Component:
    return rx.cond(
        ReplenishmentState.cancel_form_open,
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Cancelar solicitação de compra"),
                rx.vstack(
                    rx.text("Produto"),
                    rx.input(value=ReplenishmentState.cancel_product_label, read_only=True),
                    rx.text(
                        "Esta solicitação será cancelada somente após confirmação do Xano. "
                        "O estoque não será alterado."
                    ),
                    rx.text(
                        "O backend valida a propriedade e o status atual. "
                        "Se a solicitação já mudou, o cancelamento será recusado."
                    ),
                    rx.text("Justificativa"),
                    rx.text_area(
                        value=ReplenishmentState.cancel_justification,
                        on_change=ReplenishmentState.change_cancel_justification,
                        disabled=ReplenishmentState.cancel_submission_in_progress
                        | ReplenishmentState.cancel_attempt_ambiguous,
                    ),
                    rx.cond(
                        ReplenishmentState.cancel_error_message != "",
                        rx.text(ReplenishmentState.cancel_error_message, color="#b91c1c", role="alert"),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                ReplenishmentState.cancel_attempt_ambiguous,
                                "Tentar novamente",
                                "Confirmar cancelamento",
                            ),
                            on_click=ReplenishmentState.confirm_cancel_request,
                            disabled=(~ReplenishmentState.cancel_justification_valid)
                            | ReplenishmentState.cancel_submission_in_progress,
                        ),
                        rx.button(
                            "Fechar",
                            on_click=ReplenishmentState.dismiss_cancel_form,
                            variant="soft",
                            disabled=ReplenishmentState.cancel_submission_in_progress,
                        ),
                        justify="end",
                        width="100%",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
            open=ReplenishmentState.cancel_form_open,
        ),
        rx.fragment(),
    )


def _requestable_content() -> rx.Component:
    return rx.vstack(
        _status_panel(ReplenishmentState.requestable_status, ReplenishmentState.error_message),
        rx.cond(
            (ReplenishmentState.requestable_status == "ready")
            | (ReplenishmentState.requestable_status == "empty"),
            rx.cond(
                ReplenishmentState.requestable_total > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Código", scope="col"),
                            rx.table.column_header_cell("Produto", scope="col"),
                            rx.table.column_header_cell("Estoque atual", scope="col"),
                            rx.table.column_header_cell("Estoque mínimo", scope="col"),
                            rx.table.column_header_cell("Situação", scope="col"),
                            rx.table.column_header_cell("Ação", scope="col"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            ReplenishmentState.requestable_products,
                            lambda row: rx.table.row(
                                rx.table.cell(row["codigo"]),
                                rx.table.cell(row["produto"]),
                                rx.table.cell(
                                    row["estoque_atual"],
                                    rx.cond(row["unidade"] != "", " " + row["unidade"], ""),
                                ),
                                rx.table.cell(
                                    row["estoque_minimo"],
                                    rx.cond(row["unidade"] != "", " " + row["unidade"], ""),
                                ),
                                rx.table.cell(row["situacao_label"]),
                                rx.table.cell(
                                    rx.button(
                                        "Solicitar compra",
                                        on_click=ReplenishmentState.open_request_form(
                                            row["id"], row["codigo"], row["produto"],
                                            row["estoque_atual"], row["estoque_minimo"],
                                            row["unidade"], "true", "true",
                                        ),
                                        disabled=(~ReplenishmentState.can_create_request)
                                        | ReplenishmentState.data_stale,
                                    )
                                ),
                            ),
                        )
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.text("Nenhum produto precisa de reposição.", color="#64748b"),
            ),
            rx.fragment(),
        ),
        rx.cond(
            ReplenishmentState.data_stale,
            rx.hstack(
                rx.text("Dados temporariamente não atualizados; ações estão bloqueadas.", color="#a16207", size="2"),
                _retry_action(),
                spacing="2",
                align="center",
                wrap="wrap",
            ),
            rx.fragment(),
        ),
        rx.cond(
            ReplenishmentState.requestable_total > ReplenishmentState.page_size,
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=ReplenishmentState.load_requestable_page(ReplenishmentState.requestable_page - 1),
                    disabled=ReplenishmentState.requestable_page <= 1,
                ),
                rx.text(
                    "Página ", ReplenishmentState.requestable_page, " de ",
                    ReplenishmentState.requestable_page_total, " · ",
                    ReplenishmentState.requestable_total, " produtos",
                ),
                rx.button(
                    "Próxima",
                    on_click=ReplenishmentState.load_requestable_page(ReplenishmentState.requestable_page + 1),
                    disabled=ReplenishmentState.requestable_page >= ReplenishmentState.requestable_page_total,
                ),
                width="100%",
                justify="between",
            ),
            rx.fragment(),
        ),
        width="100%",
        align="stretch",
        spacing="3",
    )


def _requested_content() -> rx.Component:
    return rx.vstack(
        _status_panel(ReplenishmentState.requested_status, ReplenishmentState.error_message),
        rx.cond(
            (ReplenishmentState.requested_status == "ready")
            | (ReplenishmentState.requested_status == "empty"),
            rx.cond(
                ReplenishmentState.requested_total > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            *[
                                rx.table.column_header_cell(header, scope="col")
                                for header in (
                                    "Código", "Produto", "Estoque atual", "Estoque mínimo",
                                    "Quantidade solicitada", "Urgência", "Status da solicitação",
                                    "Data da solicitação", "Ação",
                                )
                            ]
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            ReplenishmentState.requested_products,
                            lambda row: rx.table.row(
                                rx.table.cell(row["codigo"]),
                                rx.table.cell(row["produto"]),
                                rx.table.cell(
                                    row["estoque_atual"],
                                    rx.cond(row["unidade"] != "", " " + row["unidade"], ""),
                                ),
                                rx.table.cell(
                                    row["estoque_minimo"],
                                    rx.cond(row["unidade"] != "", " " + row["unidade"], ""),
                                ),
                                rx.table.cell(row["quantidade_solicitada"]),
                                rx.table.cell(row["urgencia"]),
                                rx.table.cell(row["status"]),
                                rx.table.cell(row["data_solicitacao"]),
                                rx.table.cell(
                                    rx.cond(
                                        ReplenishmentState.can_cancel_requests
                                        & ((row["status"] == "aberta") | (row["status"] == "em_analise")),
                                        rx.button(
                                            "Cancelar solicitação",
                                            on_click=ReplenishmentState.open_cancel_request_form(row["solicitacao_id"]),
                                            variant="soft",
                                        ),
                                        rx.fragment(),
                                    )
                                ),
                            ),
                        )
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.text("Nenhuma solicitação ativa encontrada.", color="#64748b"),
            ),
            rx.fragment(),
        ),
        rx.cond(
            ReplenishmentState.data_stale,
            rx.hstack(
                rx.text("Dados temporariamente não atualizados.", color="#a16207", size="2"),
                _retry_action(),
                spacing="2",
                align="center",
                wrap="wrap",
            ),
            rx.fragment(),
        ),
        rx.cond(
            ReplenishmentState.requested_total > ReplenishmentState.page_size,
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=ReplenishmentState.load_requested_page(ReplenishmentState.requested_page - 1),
                    disabled=ReplenishmentState.requested_page <= 1,
                ),
                rx.text(
                    "Página ", ReplenishmentState.requested_page, " de ",
                    ReplenishmentState.requested_page_total, " · ",
                    ReplenishmentState.requested_total, " solicitações",
                ),
                rx.button(
                    "Próxima",
                    on_click=ReplenishmentState.load_requested_page(ReplenishmentState.requested_page + 1),
                    disabled=ReplenishmentState.requested_page >= ReplenishmentState.requested_page_total,
                ),
                width="100%",
                justify="between",
            ),
            rx.fragment(),
        ),
        width="100%",
        align="stretch",
        spacing="3",
    )


def reposicao() -> rx.Component:
    return page(
        "Reposição de Estoque",
        rx.vstack(
            rx.cond(
                ReplenishmentState.request_success_message != "",
                rx.text(ReplenishmentState.request_success_message, color="#166534", role="status"),
                rx.fragment(),
            ),
            rx.cond(
                ReplenishmentState.cancel_success_message != "",
                rx.text(ReplenishmentState.cancel_success_message, color="#166534", role="status"),
                rx.fragment(),
            ),
            rx.text(
                "Gerencie produtos com estoque insuficiente e acompanhe solicitações de compras.",
                color="#64748b",
            ),
            rx.hstack(
                rx.button(
                    "A solicitar",
                    on_click=ReplenishmentState.select_tab("to_request"),
                    variant=rx.cond(ReplenishmentState.active_tab == "to_request", "solid", "soft"),
                ),
                rx.button(
                    "Compra já solicitada",
                    on_click=ReplenishmentState.select_tab("requested"),
                    variant=rx.cond(ReplenishmentState.active_tab == "requested", "solid", "soft"),
                ),
                spacing="3",
                width="100%",
            ),
            rx.cond(
                ReplenishmentState.active_tab == "to_request",
                section("A solicitar", _requestable_content()),
                section("Compra já solicitada", _requested_content()),
            ),
            _request_form(),
            _cancel_form(),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
