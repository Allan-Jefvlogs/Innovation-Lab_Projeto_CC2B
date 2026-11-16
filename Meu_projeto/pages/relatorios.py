"""RelatÃ³rio operacional de movimentaÃ§Ãµes de estoque."""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

import reflex as rx

from ..components.theme import (
    BORDER,
    BORDER_SOFT,
    ERROR_TEXT,
    MINT_SOFT,
    PEACH_SOFT,
    ROSE_SOFT,
    ROSE_TEXT,
    SECTION_BANDS,
    SECTION_SURFACES,
    SUCCESS_TEXT,
    SURFACE,
    SURFACE_ALT,
    TABLE_HEADER,
    TEXT_MUTED,
    WARNING_TEXT,
)

logger = logging.getLogger(__name__)


def _sao_paulo_timezone():
    try:
        return ZoneInfo("America/Sao_Paulo")
    except Exception:
        return timezone(timedelta(hours=-3))

from ..components.layout import page, section
from ..components.searchable_select import normalize_search_text, searchable_select
from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoError,
    XanoPermissionError,
    XanoRequestError,
    XanoServerError,
    auth_client,
)
from ..services.session_read_cache import CACHE_MISS, session_read_cache
from ..state import AuthState


def _cache_ttl(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


REPORT_PRODUCT_OPTIONS_TTL = _cache_ttl(
    "NEXSTOCK_REPORT_PRODUCTS_CACHE_TTL_SECONDS", 30.0
)
REPORT_SUPPLIER_OPTIONS_TTL = _cache_ttl(
    "NEXSTOCK_REPORT_SUPPLIERS_CACHE_TTL_SECONDS", 120.0
)
REPORT_RESULTS_TTL = _cache_ttl("NEXSTOCK_REPORT_RESULTS_TTL_SECONDS", 30.0)
REPORT_OPTIONS_PER_PAGE = 100


def _temporary_report_read_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    return isinstance(error, XanoConnectionError) or (
        isinstance(status_code, int) and (status_code == 429 or status_code >= 500)
    )


class ReportState(rx.State):
    movements: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    report_data_loaded: bool = False
    report_results_stale: bool = False
    report_retry_available: bool = False
    report_retry_page: int = 1
    report_retry_apply_draft: bool = False
    report_loaded_at: float = 0.0
    summary_loaded_at: float = 0.0
    current_page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 1
    next_page: int | None = None
    prev_page: int | None = None

    start_date: str = ""
    end_date: str = ""
    filter_type: str = ""
    filter_product_id: str = ""
    filter_supplier_id: str = ""
    applied_start_date: str = ""
    applied_end_date: str = ""
    applied_filter_type: str = ""
    applied_filter_product_id: str = ""
    applied_filter_supplier_id: str = ""

    product_options: list[dict[str, str]] = []
    product_query: str = ""
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False
    product_options_loading: bool = False
    product_options_loaded: bool = False
    product_options_loaded_at: float = 0.0
    product_options_stale: bool = False

    supplier_options: list[dict[str, str]] = []
    supplier_query: str = ""
    supplier_options_open: bool = False
    supplier_page: int = 1
    supplier_has_more: bool = False
    supplier_loading_more: bool = False
    supplier_options_loading: bool = False
    supplier_options_loaded: bool = False
    supplier_options_loaded_at: float = 0.0
    supplier_options_stale: bool = False
    filter_options_message: str = ""
    filter_options_error_kind: str = ""
    preserve_product_selection_on_retry: bool = False
    preserve_supplier_selection_on_retry: bool = False

    movement_total: int = 0
    entry_quantity_total: str = "0"
    exit_quantity_total: str = "0"
    export_loading: bool = False

    @rx.var
    def filters_dirty(self) -> bool:
        return any(
            (
                self.start_date != self.applied_start_date,
                self.end_date != self.applied_end_date,
                self.filter_type != self.applied_filter_type,
                self.filter_product_id != self.applied_filter_product_id,
                self.filter_supplier_id != self.applied_filter_supplier_id,
            )
        )

    @rx.var
    def can_export(self) -> bool:
        return (
            self.report_data_loaded
            and not self.filters_dirty
            and not self.report_results_stale
            and not self.error_message
        )

    def _draft_filter_values(self) -> tuple[str, str, str, str, str]:
        return (
            self.start_date, self.end_date, self.filter_type,
            self.filter_product_id, self.filter_supplier_id,
        )

    def _applied_filter_values(self) -> tuple[str, str, str, str, str]:
        return (
            self.applied_start_date, self.applied_end_date, self.applied_filter_type,
            self.applied_filter_product_id, self.applied_filter_supplier_id,
        )

    def _report_results_fresh(self) -> bool:
        now = time.monotonic()
        return (
            self.report_data_loaded
            and now - self.report_loaded_at < REPORT_RESULTS_TTL
            and now - self.summary_loaded_at < REPORT_RESULTS_TTL
        )

    def _summary_fresh(self) -> bool:
        return (
            self.report_data_loaded
            and time.monotonic() - self.summary_loaded_at < REPORT_RESULTS_TTL
        )

    def _clear_report_results(self) -> None:
        self.movements = []
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        self.total_items = 0
        self.total_pages = 1
        self.next_page = None
        self.prev_page = None
        self.report_data_loaded = False
        self.report_results_stale = False
        self.report_retry_available = False
        self.report_loaded_at = 0.0
        self.summary_loaded_at = 0.0

    @rx.var
    def filtered_product_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.product_query)
        if not query:
            return self.product_options
        return [
            item for item in self.product_options
            if query in normalize_search_text(item.get("label", ""))
        ]

    @rx.var
    def filtered_supplier_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.supplier_query)
        if not query:
            return self.supplier_options
        return [
            item for item in self.supplier_options
            if query in normalize_search_text(item.get("label", ""))
        ]

    @rx.var
    def product_options_empty_message(self) -> str:
        if self.product_options_loading:
            return "Carregando opções de produtos..."
        if self.filter_options_error_kind == "product":
            return "Não foi possível confirmar a lista de produtos. Tente novamente."
        if self.product_options_stale:
            return "A lista anterior de produtos está vazia e pode estar desatualizada."
        return "Nenhuma opção encontrada."

    @rx.var
    def supplier_options_empty_message(self) -> str:
        if self.supplier_options_loading:
            return "Carregando opções de fornecedores..."
        if self.filter_options_error_kind == "supplier":
            return "Não foi possível confirmar a lista de fornecedores. Tente novamente."
        if self.supplier_options_stale:
            return "A lista anterior de fornecedores está vazia e pode estar desatualizada."
        return "Nenhuma opção encontrada."

    def load_page(self):
        self.report_data_loaded = False
        self.report_results_stale = False
        self.report_retry_available = False
        self.report_loaded_at = 0.0
        self.summary_loaded_at = 0.0
        self.movements = []
        self.start_date = ""
        self.end_date = ""
        self.filter_type = ""
        self.filter_product_id = ""
        self.filter_supplier_id = ""
        self.applied_start_date = ""
        self.applied_end_date = ""
        self.applied_filter_type = ""
        self.applied_filter_product_id = ""
        self.applied_filter_supplier_id = ""
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        self.product_query = ""
        self.supplier_query = ""
        self.product_options = []
        self.product_page = 1
        self.product_has_more = False
        self.product_loading_more = False
        self.product_options_loading = False
        self.product_options_loaded = False
        self.product_options_loaded_at = 0.0
        self.product_options_stale = False
        self.product_options_open = False
        self.supplier_options = []
        self.supplier_page = 1
        self.supplier_has_more = False
        self.supplier_loading_more = False
        self.supplier_options_loading = False
        self.supplier_options_loaded = False
        self.supplier_options_loaded_at = 0.0
        self.supplier_options_stale = False
        self.supplier_options_open = False
        self.filter_options_message = ""
        self.filter_options_error_kind = ""
        self.preserve_product_selection_on_retry = False
        self.preserve_supplier_selection_on_retry = False
        return [AuthState.require_auth(), ReportState.load_initial()]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
        if not auth_state.is_authenticated or not auth_state.has_permission("report.read"):
            token = str(auth_state.auth_token or "").strip()
            if token:
                session_read_cache.clear_session(token)
            self._clear_report_results()
            self.product_options = []
            self.product_options_loaded = False
            self.product_options_stale = False
            self.supplier_options = []
            self.supplier_options_loaded = False
            self.supplier_options_stale = False
            self.filter_options_error_kind = ""
            self.filter_options_message = ""
            return ""
        return str(auth_state.auth_token or "").strip()

    @staticmethod
    def _product_option(item: dict[str, Any]) -> dict[str, str]:
        product_id = str(item.get("id", ""))
        code = str(item.get("codigo") or "")
        name = str(item.get("nome") or "Produto sem nome")
        return {"id": product_id, "label": f"{code} - {name}".strip(" -")}

    @staticmethod
    def _supplier_option(item: dict[str, Any]) -> dict[str, str]:
        supplier_id = str(item.get("id", ""))
        name = str(item.get("nome_razao_social") or "Fornecedor sem nome")
        return {"id": supplier_id, "label": name}

    async def load_initial(self):
        self.is_loading = True
        self.error_message = ""
        self.report_retry_available = False
        self.report_retry_page = 1
        self.report_retry_apply_draft = False
        self.movements = []
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            await self._load_report_data(token, 1, self._applied_filter_values())
        except XanoAuthError:
            self.error_message = "Sua sessÃ£o expirou. FaÃ§a login novamente."
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.error_message = "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        except XanoRequestError as exc:
            self.error_message = self._request_error_message(exc)
            self.report_retry_available = _temporary_report_read_error(exc)
        except (XanoConnectionError, XanoServerError, XanoError) as exc:
            self.error_message = (
                exc.message
                if getattr(exc, "status_code", None) == 429
                else "Não foi possível carregar os relatórios. Tente novamente."
            )
            self.report_retry_available = _temporary_report_read_error(exc)
        except Exception as exc:
            logger.exception("Reports load failed: exception_type=%s", type(exc).__name__)
            self.error_message = "Não foi possível carregar os relatórios. Tente novamente."
        finally:
            self.is_loading = False
        yield

    async def _load_option_page(self, token: str, kind: str, page: int = 1):
        ttl = (
            REPORT_PRODUCT_OPTIONS_TTL
            if kind == "product"
            else REPORT_SUPPLIER_OPTIONS_TTL
        )
        params = {"kind": kind, "page": page, "per_page": REPORT_OPTIONS_PER_PAGE}
        key = session_read_cache.key(
            "report_filter_options", "GET /report_options", token, params
        )
        cached, fresh = session_read_cache.get(key, ttl, allow_stale=True)
        if fresh:
            return cached, False

        try:
            response = await auth_client.list_report_options(
                token, kind, page=page, per_page=REPORT_OPTIONS_PER_PAGE
            )
        except XanoError as exc:
            if cached is not CACHE_MISS and _temporary_report_read_error(exc):
                self.filter_options_error_kind = kind
                self.filter_options_message = (
                    f"{self._filter_options_error_message(exc)} "
                    "As opções anteriores permanecem disponíveis e podem estar desatualizadas."
                )
                return cached, True
            raise

        option_mapper = self._product_option if kind == "product" else self._supplier_option
        result = {
            "items": [
                option_mapper(item)
                for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            ],
            "has_more": len(response["items"]) == REPORT_OPTIONS_PER_PAGE,
        }
        session_read_cache.set(key, result, ttl)
        return result, False

    async def _load_products(self, token: str):
        result, stale = await self._load_option_page(token, "product", 1)
        self.product_options = list(result["items"])
        self.product_page = 1
        self.product_has_more = result["has_more"]
        self.product_options_loaded = not stale
        self.product_options_loaded_at = time.monotonic() if not stale else 0.0
        self.product_options_stale = stale
        return stale

    async def _load_suppliers(self, token: str):
        result, stale = await self._load_option_page(token, "supplier", 1)
        self.supplier_options = list(result["items"])
        self.supplier_page = 1
        self.supplier_has_more = result["has_more"]
        self.supplier_options_loaded = not stale
        self.supplier_options_loaded_at = time.monotonic() if not stale else 0.0
        self.supplier_options_stale = stale
        return stale

    async def open_product_options(self):
        preserve_selection = self.preserve_product_selection_on_retry
        self.preserve_product_selection_on_retry = False
        if self.filter_product_id and not preserve_selection:
            self.filter_product_id = ""
            self.product_query = ""
        self.product_options_open = True
        self.supplier_options_open = False
        if self.product_options_loading:
            return
        if (
            self.product_options_loaded
            and time.monotonic() - self.product_options_loaded_at < REPORT_PRODUCT_OPTIONS_TTL
        ):
            return
        self.product_options_loading = True
        self.filter_options_message = ""
        self.filter_options_error_kind = ""
        yield
        try:
            token = await self._session_token()
            if not token:
                yield rx.redirect("/")
                return
            stale = await self._load_products(token)
            self.filter_options_error_kind = "product" if stale else ""
            if stale and not self.filter_options_message:
                self.filter_options_message = (
                    "As opções de produtos exibidas podem estar desatualizadas. "
                    "Feche e abra o seletor novamente depois do período de espera para atualizar."
                )
        except XanoAuthError:
            self.product_options = []
            self.product_options_loaded = False
            self.product_options_stale = False
            session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            yield rx.redirect("/")
            return
        except XanoError as exc:
            self.product_options_loaded = False
            self.filter_options_error_kind = "product"
            temporary = _temporary_report_read_error(exc)
            self.product_options_stale = temporary and bool(self.product_options)
            if isinstance(exc, XanoPermissionError) or not temporary:
                self.product_options = []
            if isinstance(exc, XanoPermissionError):
                session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            self.filter_options_message = self._filter_options_error_message(exc)
            if self.product_options_stale:
                self.filter_options_message += " As opções anteriores permanecem disponíveis e podem estar desatualizadas."
        finally:
            self.product_options_loading = False

    async def open_supplier_options(self):
        preserve_selection = self.preserve_supplier_selection_on_retry
        self.preserve_supplier_selection_on_retry = False
        if self.filter_supplier_id and not preserve_selection:
            self.filter_supplier_id = ""
            self.supplier_query = ""
        self.supplier_options_open = True
        self.product_options_open = False
        if self.supplier_options_loading:
            return
        if (
            self.supplier_options_loaded
            and time.monotonic() - self.supplier_options_loaded_at < REPORT_SUPPLIER_OPTIONS_TTL
        ):
            return
        self.supplier_options_loading = True
        self.filter_options_message = ""
        self.filter_options_error_kind = ""
        yield
        try:
            token = await self._session_token()
            if not token:
                yield rx.redirect("/")
                return
            stale = await self._load_suppliers(token)
            self.filter_options_error_kind = "supplier" if stale else ""
            if stale and not self.filter_options_message:
                self.filter_options_message = (
                    "As opções de fornecedores exibidas podem estar desatualizadas. "
                    "Feche e abra o seletor novamente depois do período de espera para atualizar."
                )
        except XanoAuthError:
            self.supplier_options = []
            self.supplier_options_loaded = False
            self.supplier_options_stale = False
            session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            yield rx.redirect("/")
            return
        except XanoError as exc:
            self.supplier_options_loaded = False
            self.filter_options_error_kind = "supplier"
            temporary = _temporary_report_read_error(exc)
            self.supplier_options_stale = temporary and bool(self.supplier_options)
            if isinstance(exc, XanoPermissionError) or not temporary:
                self.supplier_options = []
            if isinstance(exc, XanoPermissionError):
                session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            self.filter_options_message = self._filter_options_error_message(exc)
            if self.supplier_options_stale:
                self.filter_options_message += " As opções anteriores permanecem disponíveis e podem estar desatualizadas."
        finally:
            self.supplier_options_loading = False

    def retry_product_options(self):
        self.preserve_product_selection_on_retry = True
        return ReportState.open_product_options

    def retry_supplier_options(self):
        self.preserve_supplier_selection_on_retry = True
        return ReportState.open_supplier_options

    async def load_more_products(self):
        if self.product_loading_more or not self.product_has_more:
            return
        token = await self._session_token()
        if not token:
            return
        self.product_loading_more = True
        try:
            page = self.product_page + 1
            result, stale = await self._load_option_page(token, "product", page)
            known = {item["id"] for item in self.product_options}
            self.product_options.extend(
                item for item in result["items"] if item["id"] not in known
            )
            self.product_page = page
            self.product_has_more = result["has_more"]
            self.product_options_loaded = not stale
            self.product_options_stale = stale
            self.filter_options_error_kind = "product" if stale else ""
            if stale and not self.filter_options_message:
                self.filter_options_message = "As opções de produtos podem estar desatualizadas enquanto a consulta estiver indisponível."
        except XanoAuthError:
            self.product_options = []
            self.product_options_loaded = False
            self.product_options_stale = False
            session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            return rx.redirect("/")
        except XanoError as exc:
            logger.warning(
                "Report filter options failed: operation=products path=/products exception_type=%s",
                type(exc).__name__,
            )
            self.filter_options_message = self._filter_options_error_message(exc)
            self.filter_options_error_kind = "product"
            self.product_options_stale = _temporary_report_read_error(exc) and bool(self.product_options)
            self.product_options_loaded = False
            self.product_options_loaded_at = 0.0
            if isinstance(exc, XanoPermissionError):
                self.product_options = []
                session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            elif not self.product_options_stale:
                self.product_options = []
        finally:
            self.product_loading_more = False

    async def load_more_suppliers(self):
        if self.supplier_loading_more or not self.supplier_has_more:
            return
        token = await self._session_token()
        if not token:
            return
        self.supplier_loading_more = True
        try:
            page = self.supplier_page + 1
            result, stale = await self._load_option_page(token, "supplier", page)
            known = {item["id"] for item in self.supplier_options}
            self.supplier_options.extend(
                item for item in result["items"] if item["id"] not in known
            )
            self.supplier_page = page
            self.supplier_has_more = result["has_more"]
            self.supplier_options_loaded = not stale
            self.supplier_options_stale = stale
            self.filter_options_error_kind = "supplier" if stale else ""
            if stale and not self.filter_options_message:
                self.filter_options_message = "As opções de fornecedores podem estar desatualizadas enquanto a consulta estiver indisponível."
        except XanoAuthError:
            self.supplier_options = []
            self.supplier_options_loaded = False
            self.supplier_options_stale = False
            session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            return rx.redirect("/")
        except XanoError as exc:
            logger.warning(
                "Report filter options failed: operation=suppliers path=/suppliers exception_type=%s",
                type(exc).__name__,
            )
            self.filter_options_message = self._filter_options_error_message(exc)
            self.filter_options_error_kind = "supplier"
            self.supplier_options_stale = _temporary_report_read_error(exc) and bool(self.supplier_options)
            self.supplier_options_loaded = False
            self.supplier_options_loaded_at = 0.0
            if isinstance(exc, XanoPermissionError):
                self.supplier_options = []
                session_read_cache.invalidate(endpoint="GET /report_options", token=token)
            elif not self.supplier_options_stale:
                self.supplier_options = []
        finally:
            self.supplier_loading_more = False

    def search_products(self, value: str):
        self.product_query = value
        self.filter_product_id = ""
        self.product_options_open = True
        self.supplier_options_open = False

    def close_product_options(self, value: str = ""):
        self.product_options_open = False

    def close_product_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.product_options_open = False

    def select_product(self, product_id: str):
        self.filter_product_id = str(product_id or "")
        option = next((item for item in self.product_options if item["id"] == self.filter_product_id), None)
        self.product_query = option["label"] if option else ""
        self.product_options_open = False

    def search_suppliers(self, value: str):
        self.supplier_query = value
        self.filter_supplier_id = ""
        self.supplier_options_open = True
        self.product_options_open = False

    def close_supplier_options(self, value: str = ""):
        self.supplier_options_open = False

    def close_supplier_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.supplier_options_open = False

    def select_supplier(self, supplier_id: str):
        self.filter_supplier_id = str(supplier_id or "")
        option = next((item for item in self.supplier_options if item["id"] == self.filter_supplier_id), None)
        self.supplier_query = option["label"] if option else ""
        self.supplier_options_open = False

    @staticmethod
    def _date_boundary(value: str, *, end_of_day: bool) -> int | None:
        if not value.strip():
            return None
        parsed = datetime.strptime(value, "%Y-%m-%d")
        local_timezone = _sao_paulo_timezone()
        if end_of_day:
            parsed = parsed + timedelta(days=1) - timedelta(milliseconds=1)
        return int(parsed.replace(tzinfo=local_timezone).timestamp() * 1000)

    def change_start_date(self, value: str):
        self.start_date = value

    def change_end_date(self, value: str):
        self.end_date = value

    def change_type(self, value: str):
        self.filter_type = value if value in {"entrada", "saida"} else ""

    @staticmethod
    def _request_error_message(exc: XanoRequestError) -> str:
        if exc.status_code == 429:
            return exc.message or "Muitas solicitações foram feitas em pouco tempo. Aguarde e tente novamente."
        if exc.error_code == "PERMISSION_DENIED":
            return "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        if exc.error_code in {"INVALID_INPUT", "ERROR_CODE_INPUT_ERROR"}:
            return "Os filtros informados sÃ£o invÃ¡lidos. Confira as datas selecionadas."
        return "Não foi possível carregar os relatórios. Tente novamente."

    @classmethod
    def _filter_options_error_message(cls, exc: XanoError) -> str:
        if isinstance(exc, XanoPermissionError):
            return "Seu perfil não permite carregar as opções dos relatórios."
        if isinstance(exc, XanoRequestError):
            return cls._request_error_message(exc)
        if isinstance(exc, (XanoConnectionError, XanoServerError)):
            return exc.message or "Não foi possível carregar as opções. Tente novamente."
        return "Não foi possível carregar as opções. Tente novamente."

    @staticmethod
    def _format_quantity(value: object) -> str:
        try:
            number = Decimal(str(value))
            if not number.is_finite():
                return "—"
            return format(number.normalize(), "f").replace(".", ",")
        except (InvalidOperation, TypeError, ValueError):
            return "—"

    @staticmethod
    def _format_datetime(value: object) -> str:
        try:
            timestamp = float(value)
            if timestamp > 100_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, _sao_paulo_timezone()).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError, OverflowError, OSError):
            try:
                return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y %H:%M")
            except (TypeError, ValueError):
                return "—"

    @classmethod
    def _movement_row(cls, item: dict[str, Any]) -> dict[str, str]:
        tipo = str(item.get("tipo") or "")
        return {
            "data_hora": cls._format_datetime(item.get("data_hora")),
            "tipo": "Entrada" if tipo == "entrada" else "Saída" if tipo == "saida" else "—",
            "codigo": str(item.get("product_code") or "—"),
            "produto": str(item.get("product_name") or "Produto não encontrado"),
            "quantidade": cls._format_quantity(item.get("quantidade")),
            "usuario": str(item.get("user_name") or "Usuário não encontrado"),
            "fornecedor": str(item.get("supplier_name") or "—"),
            "motivo": str(item.get("motivo") or "—"),
        }

    async def _load_report_data(
        self,
        token: str,
        page: int,
        filter_values: tuple[str, str, str, str, str] | None = None,
    ):
        filter_values = filter_values or self._applied_filter_values()
        start_date, end_date, filter_type, filter_product_id, filter_supplier_id = filter_values
        try:
            from_ms = self._date_boundary(start_date, end_of_day=False)
            to_ms = self._date_boundary(end_date, end_of_day=True)
        except ValueError:
            self.error_message = "Informe datas v\u00e1lidas para o per\u00edodo."
            return
        if from_ms is not None and to_ms is not None and from_ms > to_ms:
            self.error_message = "A data inicial deve ser anterior ou igual \u00e0 data final."
            return

        product_id = int(filter_product_id) if filter_product_id.isdigit() and int(filter_product_id) > 0 else None
        supplier_id = int(filter_supplier_id) if filter_supplier_id.isdigit() and int(filter_supplier_id) > 0 else None
        tipo = filter_type or None
        same_applied_filters = filter_values == self._applied_filter_values()
        summary = None

        if page == 1 or not self._summary_fresh() or not same_applied_filters:
            summary, movements = await asyncio.gather(
                auth_client.get_movements_summary(
                    token,
                    date_from=from_ms,
                    date_to=to_ms,
                    tipo=tipo,
                    product_id=product_id,
                    supplier_id=supplier_id,
                ),
                auth_client.list_movements(
                    token,
                    page=page,
                    per_page=self.per_page,
                    tipo=tipo,
                    product_id=product_id,
                    date_from=from_ms,
                    date_to=to_ms,
                    supplier_id=supplier_id,
                ),
            )
        else:
            movements = await auth_client.list_movements(
                token,
                page=page,
                per_page=self.per_page,
                tipo=tipo,
                product_id=product_id,
                date_from=from_ms,
                date_to=to_ms,
                supplier_id=supplier_id,
            )

        # Swap results and applied filters only after every required response succeeds.
        if summary is not None:
            self.movement_total = summary["total_movimentacoes"]
            self.entry_quantity_total = self._format_quantity(summary["quantidade_entradas"])
            self.exit_quantity_total = self._format_quantity(summary["quantidade_saidas"])
            self.summary_loaded_at = time.monotonic()
        self.movements = [
            self._movement_row(item)
            for item in movements["items"]
            if isinstance(item, dict)
        ]
        self.current_page = int(movements.get("curPage") or page)
        self.total_items = int(movements.get("itemsTotal") or 0)
        self.total_pages = max(1, int(movements.get("pageTotal") or 0))
        self.next_page = int(movements["nextPage"]) if movements.get("nextPage") is not None else None
        self.prev_page = int(movements["prevPage"]) if movements.get("prevPage") is not None else None
        (
            self.applied_start_date,
            self.applied_end_date,
            self.applied_filter_type,
            self.applied_filter_product_id,
            self.applied_filter_supplier_id,
        ) = filter_values
        self.report_data_loaded = True
        self.report_loaded_at = time.monotonic()
        self.report_results_stale = False
        self.report_retry_available = False

    async def apply_filters(self):
        if self._report_results_fresh() and not self.filters_dirty:
            self.error_message = ""
            return
        return ReportState.load_report(1, True)

    async def clear_filters(self):
        self.start_date = ""
        self.end_date = ""
        self.filter_type = ""
        self.filter_product_id = ""
        self.filter_supplier_id = ""
        self.product_query = ""
        self.supplier_query = ""
        if self._report_results_fresh() and not self.filters_dirty:
            self.error_message = ""
            return
        return ReportState.load_report(1, True)

    async def load_report(self, page: int = 1, apply_draft: bool = False):
        filter_values = self._draft_filter_values() if apply_draft else self._applied_filter_values()
        if self._report_results_fresh() and page == 1 and filter_values == self._applied_filter_values():
            self.error_message = ""
            return
        self.is_loading = True
        self.error_message = ""
        self.report_retry_page = page
        self.report_retry_apply_draft = apply_draft
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            await self._load_report_data(token, page, filter_values)
        except XanoAuthError:
            self._clear_report_results()
            self.error_message = "Sua sess\u00e3o expirou. Fa\u00e7a login novamente."
            yield rx.redirect("/")
        except XanoPermissionError:
            self._clear_report_results()
            self.error_message = "Voc\u00ea n\u00e3o possui permiss\u00e3o para visualizar os relat\u00f3rios."
        except XanoRequestError as exc:
            message = self._request_error_message(exc)
            self._set_report_failure(
                message,
                apply_draft=apply_draft,
                retryable=_temporary_report_read_error(exc),
            )
        except (XanoConnectionError, XanoServerError, XanoError) as exc:
            message = (
                exc.message
                if getattr(exc, "status_code", None) == 429
                else "N\u00e3o foi poss\u00edvel carregar os relat\u00f3rios. Tente novamente."
            )
            self._set_report_failure(
                message,
                apply_draft=apply_draft,
                retryable=_temporary_report_read_error(exc),
            )
        except Exception as exc:
            logger.exception("Reports load failed: exception_type=%s", type(exc).__name__)
            message = "N\u00e3o foi poss\u00edvel carregar os relat\u00f3rios. Tente novamente."
            self._set_report_failure(
                message,
                apply_draft=apply_draft,
                retryable=False,
            )
        finally:
            self.is_loading = False

    def _set_report_failure(self, message: str, *, apply_draft: bool, retryable: bool) -> None:
        self.report_retry_available = retryable
        self.report_results_stale = self.report_data_loaded
        if self.report_results_stale:
            if apply_draft and self.filters_dirty:
                context = (
                    "Os novos filtros não foram aplicados. Os resultados anteriores continuam visíveis, "
                    "correspondem aos filtros aplicados anteriormente e podem estar desatualizados. "
                )
            else:
                context = (
                    "Os resultados anteriores continuam visíveis e podem estar desatualizados; "
                    "eles correspondem aos filtros aplicados anteriormente. "
                )
        elif apply_draft:
            context = "Os novos filtros não foram aplicados. "
        else:
            context = ""
        self.error_message = context + message

    def retry_report(self):
        if not self.report_retry_available or self.is_loading:
            return
        return ReportState.load_report(
            self.report_retry_page, self.report_retry_apply_draft
        )

    def load_previous_page(self):
        if self.prev_page is not None:
            return ReportState.load_report(self.prev_page)

    def load_next_page(self):
        if self.next_page is not None:
            return ReportState.load_report(self.next_page)

    async def _all_filtered_rows(self, token: str) -> list[dict[str, str]]:
        from_ms = self._date_boundary(self.applied_start_date, end_of_day=False)
        to_ms = self._date_boundary(self.applied_end_date, end_of_day=True)
        product_id = int(self.applied_filter_product_id) if self.applied_filter_product_id.isdigit() and int(self.applied_filter_product_id) > 0 else None
        supplier_id = int(self.applied_filter_supplier_id) if self.applied_filter_supplier_id.isdigit() and int(self.applied_filter_supplier_id) > 0 else None
        tipo = self.applied_filter_type or None
        rows: list[dict[str, str]] = []
        page = 1
        while True:
            response = await auth_client.list_movements(
                token, page=page, per_page=100, tipo=tipo, product_id=product_id,
                supplier_id=supplier_id, date_from=from_ms, date_to=to_ms,
            )
            rows.extend(self._movement_row(item) for item in response["items"] if isinstance(item, dict))
            if len(rows) > 100_000:
                raise ValueError("O relatório excedeu o limite seguro de exportação (100.000 registros).")
            if response.get("nextPage") is None:
                break
            page = int(response["nextPage"])
        return rows

    async def export_excel(self):
        if self.export_loading or not self.can_export:
            return
        self.export_loading = True
        self.error_message = ""
        yield
        token = await self._session_token()
        if not token:
            self.export_loading = False
            yield rx.redirect("/")
            return
        try:
            rows = await self._all_filtered_rows(token)
            content = self._build_xlsx(rows)
            filename = datetime.now(_sao_paulo_timezone()).strftime("relatorio_movimentacoes_%Y%m%d_%H%M%S.xlsx")
            yield rx.download(data=content, filename=filename, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except XanoAuthError:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
        except XanoError as exc:
            logger.exception("Report export failed: operation=xlsx path=/movements")
            self.error_message = self._request_error_message(exc) if isinstance(exc, XanoRequestError) else "Não foi possível exportar o relatório. Tente novamente."
        except Exception as exc:
            logger.exception("Report export failed: operation=xlsx exception_type=%s", type(exc).__name__)
            self.error_message = str(exc) if isinstance(exc, ValueError) else "Não foi possível exportar o relatório. Tente novamente."
        finally:
            self.export_loading = False

    def _build_xlsx(self, rows: list[dict[str, str]]) -> bytes:
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        pkg_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        ET.register_namespace("", ns)
        ET.register_namespace("r", rel_ns)

        headers = ["Data/Hora", "Tipo", "C\u00f3digo", "Produto", "Quantidade", "Usu\u00e1rio", "Fornecedor", "Motivo"]
        keys = ("data_hora", "tipo", "codigo", "produto", "quantidade", "usuario", "fornecedor", "motivo")
        worksheet = ET.Element(f"{{{ns}}}worksheet")
        views = ET.SubElement(worksheet, f"{{{ns}}}sheetViews")
        view = ET.SubElement(views, f"{{{ns}}}sheetView", {"workbookViewId": "0"})
        ET.SubElement(view, f"{{{ns}}}pane", {"ySplit": "1", "topLeftCell": "A2", "activePane": "bottomLeft", "state": "frozen"})
        ET.SubElement(view, f"{{{ns}}}selection", {"pane": "bottomLeft", "activeCell": "A2", "sqref": "A2"})
        columns = ET.SubElement(worksheet, f"{{{ns}}}cols")
        for index, width in enumerate((19, 12, 13, 32, 15, 26, 26, 42), start=1):
            ET.SubElement(columns, f"{{{ns}}}col", {"min": str(index), "max": str(index), "width": str(width), "customWidth": "1"})

        sheet_data = ET.SubElement(worksheet, f"{{{ns}}}sheetData")

        def text_cell(row_el: ET.Element, reference: str, value: object, style: int = 0) -> None:
            cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": str(style), "t": "inlineStr"})
            inline = ET.SubElement(cell, f"{{{ns}}}is")
            ET.SubElement(inline, f"{{{ns}}}t").text = str(value)

        header_row = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": "1"})
        for col_number, label in enumerate(headers):
            text_cell(header_row, f"{chr(65 + col_number)}1", label, style=1)

        excel_epoch = datetime(1899, 12, 30)
        for row_number, row in enumerate(rows, start=2):
            row_el = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": str(row_number)})
            for col_number, key in enumerate(keys):
                reference = f"{chr(65 + col_number)}{row_number}"
                value = row.get(key)
                if value is None or value == "":
                    value = "\u2014" if key == "fornecedor" else ""
                if key == "data_hora":
                    try:
                        timestamp = datetime.strptime(str(value), "%d/%m/%Y %H:%M")
                    except ValueError:
                        text_cell(row_el, reference, value)
                    else:
                        serial = (timestamp - excel_epoch).total_seconds() / 86400
                        cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": "2"})
                        ET.SubElement(cell, f"{{{ns}}}v").text = str(serial)
                elif key == "quantidade":
                    try:
                        number = Decimal(str(value).replace(",", "."))
                        if not number.is_finite():
                            raise InvalidOperation
                    except (InvalidOperation, ValueError):
                        text_cell(row_el, reference, value)
                    else:
                        cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": "3"})
                        ET.SubElement(cell, f"{{{ns}}}v").text = format(number, "f")
                else:
                    text_cell(row_el, reference, value)

        ET.SubElement(worksheet, f"{{{ns}}}autoFilter", {"ref": f"A1:H{max(1, len(rows) + 1)}"})

        styles = ET.Element(f"{{{ns}}}styleSheet")
        formats = ET.SubElement(styles, f"{{{ns}}}numFmts", {"count": "2"})
        ET.SubElement(formats, f"{{{ns}}}numFmt", {"numFmtId": "164", "formatCode": "dd/mm/yyyy hh:mm"})
        ET.SubElement(formats, f"{{{ns}}}numFmt", {"numFmtId": "165", "formatCode": "0.########"})
        fonts = ET.SubElement(styles, f"{{{ns}}}fonts", {"count": "2"})
        ET.SubElement(fonts, f"{{{ns}}}font")
        bold_font = ET.SubElement(fonts, f"{{{ns}}}font")
        ET.SubElement(bold_font, f"{{{ns}}}b")
        fills = ET.SubElement(styles, f"{{{ns}}}fills", {"count": "2"})
        ET.SubElement(ET.SubElement(fills, f"{{{ns}}}fill"), f"{{{ns}}}patternFill", {"patternType": "none"})
        ET.SubElement(ET.SubElement(fills, f"{{{ns}}}fill"), f"{{{ns}}}patternFill", {"patternType": "gray125"})
        borders = ET.SubElement(styles, f"{{{ns}}}borders", {"count": "1"})
        border = ET.SubElement(borders, f"{{{ns}}}border")
        for side in ("left", "right", "top", "bottom", "diagonal"):
            ET.SubElement(border, f"{{{ns}}}{side}")
        base_styles = ET.SubElement(styles, f"{{{ns}}}cellStyleXfs", {"count": "1"})
        ET.SubElement(base_styles, f"{{{ns}}}xf", {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
        cell_styles = ET.SubElement(styles, f"{{{ns}}}cellXfs", {"count": "4"})
        for format_id, font_id in ((0, 0), (0, 1), (164, 0), (165, 0)):
            ET.SubElement(cell_styles, f"{{{ns}}}xf", {
                "numFmtId": str(format_id), "fontId": str(font_id), "fillId": "0",
                "borderId": "0", "xfId": "0", "applyNumberFormat": "1" if format_id else "0",
            })

        content_types = ET.Element(f"{{{ct_ns}}}Types")
        ET.SubElement(content_types, f"{{{ct_ns}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Default", {"Extension": "xml", "ContentType": "application/xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/workbook.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/worksheets/sheet1.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/styles.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"})
        root_rels = ET.Element(f"{{{pkg_ns}}}Relationships")
        ET.SubElement(root_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId1", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "Target": "xl/workbook.xml"})
        workbook = ET.Element(f"{{{ns}}}workbook")
        sheets = ET.SubElement(workbook, f"{{{ns}}}sheets")
        sheet = ET.SubElement(sheets, f"{{{ns}}}sheet", {"name": "Movimenta\u00e7\u00f5es", "sheetId": "1"})
        sheet.set(f"{{{rel_ns}}}id", "rId1")
        book_rels = ET.Element(f"{{{pkg_ns}}}Relationships")
        ET.SubElement(book_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId1", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet", "Target": "worksheets/sheet1.xml"})
        ET.SubElement(book_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId2", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "Target": "styles.xml"})
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for name, root in (
                ("[Content_Types].xml", content_types), ("_rels/.rels", root_rels),
                ("xl/workbook.xml", workbook), ("xl/_rels/workbook.xml.rels", book_rels),
                ("xl/styles.xml", styles), ("xl/worksheets/sheet1.xml", worksheet),
            ):
                archive.writestr(name, ET.tostring(root, encoding="utf-8", xml_declaration=True))
        return output.getvalue()

    async def export_pdf(self):
        if self.export_loading or not self.can_export:
            return
        self.export_loading = True
        self.error_message = ""
        yield
        token = await self._session_token()
        if not token:
            self.export_loading = False
            yield rx.redirect("/")
            return
        try:
            rows = await self._all_filtered_rows(token)
            content = self._build_pdf(rows)
            filename = datetime.now(_sao_paulo_timezone()).strftime("relatorio_movimentacoes_%Y%m%d_%H%M%S.pdf")
            yield rx.download(data=content, filename=filename, mime_type="application/pdf")
        except XanoAuthError:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
        except XanoError as exc:
            logger.exception("Report export failed: operation=pdf path=/movements")
            self.error_message = self._request_error_message(exc) if isinstance(exc, XanoRequestError) else "Não foi possível exportar o relatório. Tente novamente."
        except Exception as exc:
            logger.exception("Report export failed: operation=pdf exception_type=%s", type(exc).__name__)
            self.error_message = str(exc) if isinstance(exc, ValueError) else "Não foi possível exportar o relatório. Tente novamente."
        finally:
            self.export_loading = False

    def _build_pdf(self, rows: list[dict[str, str]]) -> bytes:
        page_width, page_height = 842, 595
        margin, font_size, line_height = 22, 7, 9
        widths = [92, 50, 54, 150, 62, 110, 110, 170]
        labels = ["Data/Hora", "Tipo", "C\u00f3digo", "Produto", "Quantidade", "Usu\u00e1rio", "Fornecedor", "Motivo"]
        keys = ("data_hora", "tipo", "codigo", "produto", "quantidade", "usuario", "fornecedor", "motivo")
        pages: list[bytes] = []
        commands: list[str] = []
        y = 0.0

        def pdf_text(value: str) -> str:
            return "<" + value.encode("cp1252", errors="replace").hex().upper() + ">"

        def wrap(value: str, width: float) -> list[str]:
            limit = max(4, int(width / (font_size * 0.52)))
            words = str(value).split() or [""]
            lines: list[str] = []
            line = ""
            for word in words:
                while len(word) > limit:
                    if line:
                        lines.append(line)
                        line = ""
                    lines.append(word[:limit])
                    word = word[limit:]
                candidate = f"{line} {word}".strip()
                if len(candidate) > limit:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            if line or not lines:
                lines.append(line)
            return lines

        def table_header(top: float) -> float:
            header_height = 21
            x = margin
            commands.append("0.90 0.92 0.94 rg")
            commands.append(f"{x} {top-header_height} {sum(widths)} {header_height} re f")
            commands.append("0.72 0.75 0.79 RG 0.35 w")
            commands.append(f"{x} {top-header_height} {sum(widths)} {header_height} re S")
            commands.append("0 0 0 rg")
            for index, label in enumerate(labels):
                commands.append(f"BT /F2 7 Tf 1 0 0 1 {x+4:.2f} {top-14:.2f} Tm {pdf_text(label)} Tj ET")
                x += widths[index]
                if index < len(widths) - 1:
                    commands.append(f"{x:.2f} {top-header_height:.2f} m {x:.2f} {top:.2f} l S")
            return top - header_height

        def start_page() -> None:
            nonlocal commands, y
            if commands:
                pages.append("\n".join(commands).encode("ascii"))
            commands = [
                "0 0 0 rg",
                f"BT /F2 16 Tf 1 0 0 1 {margin} {page_height-28} Tm {pdf_text('NexStock \u2014 Relat\u00f3rio de Movimenta\u00e7\u00f5es')} Tj ET",
            ]
            y = table_header(page_height - 48)

        def draw_row(cell_lines: list[list[str]], height: float) -> None:
            nonlocal y
            commands.append("1 1 1 rg")
            commands.append(f"{margin} {y-height:.2f} {sum(widths)} {height:.2f} re f")
            commands.append("0.82 0.84 0.87 RG 0.3 w")
            commands.append(f"{margin} {y-height:.2f} {sum(widths)} {height:.2f} re S")
            commands.append("0 0 0 rg")
            x = margin
            for col, (lines, width) in enumerate(zip(cell_lines, widths)):
                for line_index, line in enumerate(lines):
                    commands.append(f"BT /F1 {font_size} Tf 1 0 0 1 {x+4:.2f} {y-11-line_index*line_height:.2f} Tm {pdf_text(line)} Tj ET")
                x += width
                if col < len(widths) - 1:
                    commands.append(f"{x:.2f} {y-height:.2f} m {x:.2f} {y:.2f} l S")
            y -= height

        start_page()
        full_page_room = y - 24
        for row in rows:
            remaining = [wrap(row.get(key) or ("\u2014" if key == "fornecedor" else ""), width - 8) for key, width in zip(keys, widths)]
            while any(remaining):
                if y - 24 < 18:
                    start_page()
                required_height = max(18, max(map(len, remaining)) * line_height + 6)
                if required_height > y - 24 and required_height <= full_page_room:
                    start_page()
                lines_fit = max(1, int((y - 24 - 6) / line_height))
                segment = [lines[:lines_fit] for lines in remaining]
                segment_height = max(18, max(map(len, segment)) * line_height + 6)
                draw_row(segment, segment_height)
                remaining = [lines[lines_fit:] for lines in remaining]
                if any(remaining):
                    start_page()
        pages.append("\n".join(commands).encode("ascii"))

        objects: list[bytes] = [
            b"", b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        page_ids = []
        for content in pages:
            page_id = len(objects) + 1
            stream_id = page_id + 1
            page_ids.append(page_id)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>".encode("ascii")
            )
            objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream")
        kids = " ".join(f"{object_id} 0 R" for object_id in page_ids)
        objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{number} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_position = len(output)
        output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("ascii"))
        return bytes(output)


def _report_card(
    title: str,
    value: rx.Var,
    *,
    tone: str = "mint",
    value_color: str = SUCCESS_TEXT,
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, color=TEXT_MUTED, size="2"),
            rx.heading(value, size="6", color=value_color),
            align="start",
            spacing="1",
        ),
        flex="1",
        min_width="170px",
        padding="1rem",
        border=f"1px solid {SECTION_BANDS[tone]}",
        border_radius="0.5rem",
        background=SECTION_SURFACES[tone],
    )


REPORT_GRID = "150px 90px 100px minmax(160px, 1.3fr) 110px minmax(150px, 1fr) minmax(150px, 1fr) minmax(140px, 1fr)"


def _report_movement_row(movement: dict[str, str]) -> rx.Component:
    return rx.grid(
        *[
            rx.text(movement[key], padding_x="8px", white_space="nowrap", overflow="hidden", text_overflow="ellipsis")
            for key in ("data_hora", "tipo", "codigo", "produto", "quantidade", "usuario", "fornecedor", "motivo")
        ],
        columns="8",
        width="100%",
        column_gap="8px",
        style={"grid_template_columns": REPORT_GRID, "align_items": "center"},
        padding="0.75rem",
        border_bottom=f"1px solid {BORDER_SOFT}",
    )


def _report_table() -> rx.Component:
    labels = ["Data/Hora", "Tipo", "Código", "Produto", "Quantidade", "Usuário", "Fornecedor", "Motivo"]
    header = rx.grid(
        *[
            rx.text(label, weight="bold", padding_x="8px", white_space="nowrap")
            for label in labels
        ],
        columns="8",
        width="100%",
        column_gap="8px",
        style={"grid_template_columns": REPORT_GRID, "align_items": "center"},
        padding="0.75rem",
        background=TABLE_HEADER,
        border_bottom=f"1px solid {BORDER}",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(ReportState.movements, _report_movement_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border=f"1px solid {BORDER}",
        border_radius="0.4rem",
    )


def relatorios() -> rx.Component:
    return page(
        "Relatórios",
        rx.vstack(
            section(
                "Filtros",
                rx.vstack(
                    rx.hstack(
                        rx.vstack(rx.text("Data inicial"), rx.input(type="date", value=ReportState.start_date, on_change=ReportState.change_start_date, width="100%"), flex="1", min_width="220px", align="stretch", spacing="1"),
                        rx.vstack(rx.text("Data final"), rx.input(type="date", value=ReportState.end_date, on_change=ReportState.change_end_date, width="100%"), flex="1", min_width="220px", align="stretch", spacing="1"),
                        width="100%", wrap="wrap", align="end", spacing="3",
                    ),
                    rx.cond(
                        ReportState.product_options_loading | ReportState.supplier_options_loading,
                        rx.text("Carregando opções de filtro...", color=TEXT_MUTED),
                        rx.fragment(),
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Tipo"),
                            rx.select.root(
                                rx.select.trigger(placeholder="Todos"),
                                rx.select.content(
                                    rx.select.item("Todos", value="todos"),
                                    rx.select.item("Entrada", value="entrada"),
                                    rx.select.item("Saída", value="saida"),
                                ),
                                value=rx.cond(ReportState.filter_type == "", "todos", ReportState.filter_type),
                                on_change=ReportState.change_type,
                            ),
                            flex="1", min_width="180px", align="stretch", spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Produto"),
                            searchable_select(
                                query=ReportState.product_query,
                                options=ReportState.filtered_product_options,
                                is_open=ReportState.product_options_open,
                                on_search=ReportState.search_products,
                                on_open=ReportState.open_product_options,
                                on_close=ReportState.close_product_options,
                                on_escape=ReportState.close_product_options_on_escape,
                                on_select=ReportState.select_product,
                                has_more=ReportState.product_has_more,
                                is_loading_more=ReportState.product_loading_more,
                                on_load_more=ReportState.load_more_products,
                                placeholder="Todos os produtos",
                                placeholder_color=BORDER_SOFT,
                                empty_message=ReportState.product_options_empty_message,
                            ),
                            rx.cond(
                                ReportState.filter_options_error_kind == "product",
                                rx.vstack(
                                    rx.text(
                                        ReportState.filter_options_message,
                                        color=WARNING_TEXT,
                                        size="1",
                                    ),
                                    rx.button(
                                        "Tentar novamente",
                                        on_click=ReportState.retry_product_options,
                                        disabled=ReportState.product_options_loading,
                                        variant="ghost",
                                        size="1",
                                        style={"padding": "0 8px", "height": "26px"},
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                rx.fragment(),
                            ),
                            flex="1.5", min_width="220px", align="stretch", spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Fornecedor"),
                            searchable_select(
                                query=ReportState.supplier_query,
                                options=ReportState.filtered_supplier_options,
                                is_open=ReportState.supplier_options_open,
                                on_search=ReportState.search_suppliers,
                                on_open=ReportState.open_supplier_options,
                                on_close=ReportState.close_supplier_options,
                                on_escape=ReportState.close_supplier_options_on_escape,
                                on_select=ReportState.select_supplier,
                                has_more=ReportState.supplier_has_more,
                                is_loading_more=ReportState.supplier_loading_more,
                                on_load_more=ReportState.load_more_suppliers,
                                placeholder="Todos os fornecedores",
                                placeholder_color=BORDER_SOFT,
                                empty_message=ReportState.supplier_options_empty_message,
                            ),
                            rx.cond(
                                ReportState.filter_options_error_kind == "supplier",
                                rx.vstack(
                                    rx.text(
                                        ReportState.filter_options_message,
                                        color=WARNING_TEXT,
                                        size="1",
                                    ),
                                    rx.button(
                                        "Tentar novamente",
                                        on_click=ReportState.retry_supplier_options,
                                        disabled=ReportState.supplier_options_loading,
                                        variant="ghost",
                                        size="1",
                                        style={"padding": "0 8px", "height": "26px"},
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                rx.fragment(),
                            ),
                            flex="1.5", min_width="220px", align="stretch", spacing="1",
                        ),
                        width="100%", wrap="wrap", align="end", spacing="3",
                    ),
                    rx.hstack(
                        rx.button("Aplicar filtros", on_click=ReportState.apply_filters, disabled=ReportState.is_loading),
                        rx.button("Limpar", on_click=ReportState.clear_filters, variant="soft", disabled=ReportState.is_loading),
                        width="100%", justify="end",
                    ),
                    rx.cond(
                        ReportState.filters_dirty,
                        rx.text(
                            "Filtros alterados ainda não aplicados. Tabela e indicadores continuam mostrando os filtros aplicados anteriormente.",
                            color=TEXT_MUTED,
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    width="100%", align="stretch", spacing="3",
                ),
                tone="mint",
            ),
            rx.cond(ReportState.error_message != "", rx.text(ReportState.error_message, color=ERROR_TEXT)),
            rx.cond(
                ReportState.report_retry_available,
                rx.button(
                    "Tentar novamente",
                    on_click=ReportState.retry_report,
                    disabled=ReportState.is_loading,
                    variant="soft",
                ),
                rx.fragment(),
            ),
            rx.cond(
                ReportState.report_results_stale,
                rx.text(
                    "Os dados exibidos são da última consulta bem-sucedida e podem estar desatualizados.",
                    color=WARNING_TEXT,
                    size="2",
                ),
                rx.fragment(),
            ),
            rx.flex(
                _report_card("Movimentações", ReportState.movement_total, tone="mint", value_color=SUCCESS_TEXT),
                _report_card("Entradas (unidades)", ReportState.entry_quantity_total, tone="peach", value_color=WARNING_TEXT),
                _report_card("Saídas (unidades)", ReportState.exit_quantity_total, tone="rose", value_color=ROSE_TEXT),
                width="100%", wrap="wrap", gap="4",
            ),
            section(
                "Movimentações no período",
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.button("Exportar PDF", on_click=ReportState.export_pdf, disabled=ReportState.is_loading | ReportState.export_loading | ~ReportState.can_export),
                        rx.button("Exportar Excel", on_click=ReportState.export_excel, disabled=ReportState.is_loading | ReportState.export_loading | ~ReportState.can_export),
                        width="100%", align="center", wrap="wrap",
                    ),
                    rx.cond(
                        ReportState.is_loading,
                        rx.center(rx.spinner(), "Carregando relatório...", width="100%", padding="2rem"),
                        rx.cond(
                            ReportState.error_message != "",
                            rx.fragment(),
                            rx.cond(
                                ReportState.movements.length() > 0,
                                _report_table(),
                                rx.text("Nenhuma movimentação encontrada para os filtros selecionados.", color=TEXT_MUTED, padding="1rem"),
                            ),
                        ),
                    ),
                    width="100%", align="stretch", spacing="3",
                ),
                tone="rose",
            ),
            rx.hstack(
                rx.button("Anterior", on_click=ReportState.load_previous_page, disabled=ReportState.prev_page == None),
                rx.text("Página ", ReportState.current_page, " de ", ReportState.total_pages, " · ", ReportState.total_items, " movimentações"),
                rx.button("Próxima", on_click=ReportState.load_next_page, disabled=ReportState.next_page == None),
                width="100%", justify="between", align="center",
            ),
            width="100%", align="stretch", spacing="4",
        ),
    )
