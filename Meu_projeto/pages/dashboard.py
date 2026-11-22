"""Dashboard com resumos reais fornecidos pelos endpoints existentes do Xano."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import reflex as rx

from ..components.theme import (
    BORDER,
    BORDER_SOFT,
    DASHBOARD_GAP,
    MINT_SOFT,
    PEACH,
    PEACH_SOFT,
    PEACH_TINT,
    PANEL_RADIUS,
    ROSE_TEXT,
    SAGE_DARK,
    SECTION_BANDS,
    SECTION_SURFACES,
    SUCCESS_TEXT,
    SURFACE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING_TEXT,
)

from ..components.layout import page
from ..components.stock_movement_chart import stock_movement_chart
from ..services.session_read_cache import CACHE_MISS, session_read_cache
from ..services.session_read_cache import clear_session_read_cache
from ..services.dashboard_periods import PERIODS, period_bounds
from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestError,
    XanoServerError,
    auth_client,
)
from ..state import AuthState


logger = logging.getLogger(__name__)


def _cache_ttl(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


DASHBOARD_PRODUCT_TTL = _cache_ttl("NEXSTOCK_DASHBOARD_PRODUCTS_TTL_SECONDS", 30.0)
DASHBOARD_REFERENCE_TTL = _cache_ttl("NEXSTOCK_DASHBOARD_REFERENCE_TTL_SECONDS", 120.0)
DASHBOARD_OPERATIONAL_TTL = _cache_ttl("NEXSTOCK_DASHBOARD_OPERATIONAL_TTL_SECONDS", 15.0)
DASHBOARD_READ_TIMEOUT_SECONDS = 30.0
DASHBOARD_ALERT_LIMIT = 5
DASHBOARD_MOVEMENT_LIMIT = 5
DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED = os.getenv(
    "NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", "false"
).strip().lower() in {"1", "true", "yes", "on"}
_INSUFFICIENT_SUMMARY_ENDPOINT = "GET /stock/insufficient_summary"
REAL_DASHBOARD_MOVEMENTS_ENABLED = os.getenv("NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
_SAO_PAULO = ZoneInfo("America/Sao_Paulo")
_MOVEMENT_GRID_COLUMNS = rx.breakpoints(
    initial="minmax(0, 1fr) minmax(0, 1fr)",
    md="17fr 22fr 17fr 22fr 22fr",
)
_MOVEMENT_GRID_COLUMN_GAP = rx.breakpoints(initial="12px", md="16px")
_MOVEMENT_GRID_ROW_GAP = rx.breakpoints(initial="10px", md="12px")

_DASHBOARD_ENDPOINTS = {
    "products": "GET /dashboard/products",
    "stock": "GET /dashboard/stock",
    "movements": "GET /dashboard/movements",
    "purchase_requests": "GET /purchase_requests/summary",
}
_DASHBOARD_SCOPES = {
    "products": "dashboard:product.read",
    "stock": "dashboard:stock.read",
    "movements": "dashboard:movement.read-or-report.read",
    "purchase_requests": "dashboard:purchase_request.read",
}


def _cache_key(source: str, token: str, params: dict[str, Any]):
    return session_read_cache.key(
        _DASHBOARD_SCOPES[source], _dashboard_endpoint(source), token, params
    )


def _dashboard_endpoint(source: str) -> str:
    if source == "movements" and REAL_DASHBOARD_MOVEMENTS_ENABLED:
        return "GET /movements/dashboard"
    if source == "stock" and DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED:
        return _INSUFFICIENT_SUMMARY_ENDPOINT
    return _DASHBOARD_ENDPOINTS[source]


def _greeting_for_hour(hour: int) -> str:
    return "Bom dia" if 5 <= hour < 12 else "Boa tarde" if 12 <= hour < 18 else "Boa noite"


def _items_total(response: dict[str, Any], source: str) -> int:
    try:
        total = int(response["itemsTotal"])
    except (KeyError, TypeError, ValueError) as exc:
        raise XanoServerError(
            f"A resposta não incluiu a contagem paginada de {source}.", status_code=200
        ) from exc
    if total < 0:
        raise XanoServerError(
            f"A resposta incluiu uma contagem inválida de {source}.", status_code=200
        )
    return total


def _format_quantity(value: object) -> str:
    try:
        quantity = Decimal(str(value))
        if not quantity.is_finite():
            return "—"
        return format(quantity.normalize(), "f").replace(".", ",")
    except (InvalidOperation, TypeError, ValueError):
        return "—"


def _format_datetime(value: object) -> str:
    try:
        # Xano retorna timestamps em milissegundos, como no Histórico.
        return datetime.fromtimestamp(float(value) / 1000).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return "—"


def _is_temporary_failure(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    return isinstance(error, XanoConnectionError) or (
        isinstance(status_code, int) and (status_code == 429 or status_code >= 500)
    )


async def _cached_dashboard_read(
    source: str,
    token: str,
    params: dict[str, Any],
    ttl: float,
    loader: Callable[[], Any],
    *,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], bool, Exception | None]:
    key = _cache_key(source, token, params)
    cached, fresh = session_read_cache.get(key, ttl, allow_stale=True)
    if fresh and not force_refresh:
        return cached, False, None

    try:
        result = await asyncio.wait_for(loader(), timeout=DASHBOARD_READ_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        error = XanoConnectionError("Tempo limite ao consultar os dados do Dashboard.")
        if cached is not CACHE_MISS:
            return cached, True, error
        raise error from exc
    except (XanoAuthError, XanoPermissionError):
        session_read_cache.invalidate(endpoint=_dashboard_endpoint(source), token=token)
        raise
    except XanoError as exc:
        if cached is not CACHE_MISS and _is_temporary_failure(exc):
            return cached, True, exc
        raise

    session_read_cache.set(key, result, ttl)
    return result, False, None


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
    return max(20.0, float(getattr(getattr(auth_client, "coordinator", None), "window_seconds", 20.0)))


def _error_origin(error: Exception) -> str:
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
    return "server_or_contract"


def _project_count(response: dict[str, Any], source: str) -> dict[str, Any]:
    return {"count": _items_total(response, source)}


def _project_insufficient_stock(response: dict[str, Any]) -> dict[str, Any]:
    items = response.get("items")
    total = response.get("itemsTotal")
    if (
        not isinstance(items, list)
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
        or total < len(items)
    ):
        raise XanoServerError(
            "O resumo de estoque recebido está incompleto ou em formato inesperado.",
            status_code=200,
        )

    alerts: list[dict[str, str]] = []
    seen_product_ids: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            raise XanoServerError("A resposta incluiu um alerta de estoque inválido.", status_code=200)
        product_id = item.get("product_id")
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            raise XanoServerError("A resposta incluiu um identificador de produto inválido.", status_code=200)
        if product_id in seen_product_ids:
            raise XanoServerError("O resumo de estoque contém produtos duplicados.", status_code=200)
        seen_product_ids.add(product_id)

        code = item.get("codigo")
        name = item.get("nome")
        unit = item.get("unidade_medida")
        if not all(isinstance(value, str) and value.strip() for value in (code, name, unit)):
            raise XanoServerError("A resposta contém dados de produto inválidos.", status_code=200)
        try:
            quantity = Decimal(str(item["quantidade_disponivel"]))
            minimum = Decimal(str(item["estoque_minimo"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise XanoServerError("A resposta contém quantidades de estoque inválidas.", status_code=200) from exc
        if not quantity.is_finite() or not minimum.is_finite() or quantity < 0 or minimum < 0:
            raise XanoServerError("A resposta contém quantidades de estoque inválidas.", status_code=200)

        situation = item.get("situacao_estoque")
        if quantity == 0:
            expected_situation = "sem_estoque"
        elif quantity < minimum:
            expected_situation = "abaixo_minimo"
        else:
            raise XanoServerError("O resumo inclui um produto sem necessidade de reposição.", status_code=200)
        if situation != expected_situation:
            raise XanoServerError("O resumo contém uma situação de estoque incompatível.", status_code=200)

        alerts.append(
            {
                "codigo": code.strip(),
                "nome": name.strip(),
                "atual": _format_quantity(quantity),
                "minimo": _format_quantity(minimum),
                "unidade_medida": unit.strip(),
                "situacao_estoque": situation,
            }
        )
    return {"count": total, "items": alerts}


class DashboardState(rx.State):
    """Dados gerenciais do Dashboard, sempre limitados pelos grants atuais."""

    is_loading: bool = False
    has_loaded: bool = False
    error_message: str = ""
    retry_sources: list[str] = []
    retry_after_epoch: float = 0.0
    session_fingerprint: str = ""

    products_accessible: bool = False
    products_count: int | None = None
    products_error: str = ""
    products_stale: bool = False

    stock_accessible: bool = False
    below_minimum_count: int | None = None
    stock_alerts: list[dict[str, str]] = []
    stock_error: str = ""
    stock_stale: bool = False

    movements_accessible: bool = False
    recent_movements: list[dict[str, str]] = []
    movements_error: str = ""
    movements_stale: bool = False
    replenishment_accessible: bool = False

    purchase_requests_accessible: bool = False
    purchase_requests_count: int | None = None
    purchase_requests_error: str = ""
    purchase_requests_stale: bool = False
    chart_data: list[dict[str, str | int]] = []
    chart_error: str = ""
    chart_enabled: bool = REAL_DASHBOARD_MOVEMENTS_ENABLED
    chart_period: str = "7d"
    chart_loading: bool = False

    async def change_chart_period(self, value: str):
        if value not in PERIODS or value == self.chart_period or self.chart_loading or self.is_loading or not self.chart_enabled:
            return
        if self.retry_after_epoch > time.time():
            self.chart_error = "Aguarde o intervalo de recuperação antes de trocar o período."
            return
        token, grants = await self._session()
        if not token or not grants.get("movements"):
            self.chart_error = "Sem acesso aos dados de movimentação."
            self.chart_data = []
            self.recent_movements = []
            self.movements_accessible = False
            return
        self.chart_loading = True
        self.chart_period = value
        self.chart_data = []
        self.chart_error = "Carregando movimentações..."
        yield
        start, end = period_bounds(value)
        params = {"date_from": start, "date_to": end, "period": value}
        try:
            payload, stale, error = await _cached_dashboard_read(
                "movements", token, params, DASHBOARD_OPERATIONAL_TTL,
                lambda: _project_after(
                    lambda: auth_client.get_dashboard_movements(token, **params),
                    lambda data: _project_dashboard_movements(data, value),
                ),
            )
            latest_token, latest_grants = await self._session()
            if latest_token != token or not latest_grants.get("movements"):
                self.chart_data = []
                self.recent_movements = []
                self.movements_accessible = False
                self.chart_error = "Sessão ou permissão alterada."
                return
            self.chart_data = payload["serie"]
            self.recent_movements = payload["items"]
            self.chart_error = "Dados anteriores podem estar desatualizados." if stale else ""
            if error and getattr(error, "status_code", None) == 429:
                self.retry_after_epoch = time.time() + _retry_delay_seconds(error)
        except XanoAuthError:
            self.chart_data = []
            yield AuthState.logout
        except XanoError as exc:
            self.chart_error = "Não foi possível carregar o período. Use a recuperação manual."
            if getattr(exc, "status_code", None) == 429:
                self.retry_after_epoch = time.time() + _retry_delay_seconds(exc)
            if "movements" not in self.retry_sources:
                self.retry_sources.append("movements")
        finally:
            self.chart_loading = False

    @rx.var
    def greeting(self) -> str:
        hour = datetime.now(_SAO_PAULO).hour
        return _greeting_for_hour(hour)

    @rx.var
    def first_name(self) -> str:
        return (self._auth_user_name or "").split(" ")[0]

    _auth_user_name: str = ""

    @rx.var
    def has_errors(self) -> bool:
        return bool(
            self.products_error
            or self.stock_error
            or self.movements_error
            or self.purchase_requests_error
        )

    @rx.var
    def products_value(self) -> str:
        return self._metric_value(self.products_accessible, self.products_count, self.products_error)

    @rx.var
    def stock_value(self) -> str:
        return self._metric_value(self.stock_accessible, self.below_minimum_count, self.stock_error)

    @rx.var
    def purchase_requests_value(self) -> str:
        return self._metric_value(
            self.purchase_requests_accessible,
            self.purchase_requests_count,
            self.purchase_requests_error,
        )

    @rx.var
    def purchase_requests_detail(self) -> str:
        if self.is_loading and self.purchase_requests_count is None and not self.purchase_requests_error:
            return "Carregando solicitações..."
        if not self.purchase_requests_accessible:
            return "Permissão de leitura não concedida"
        if self.purchase_requests_error == "forbidden":
            return "O servidor não autorizou esta consulta"
        if self.purchase_requests_error:
            return (
                "Dado em cache; pode estar desatualizado"
                if self.purchase_requests_stale
                else "Não foi possível carregar este indicador"
            )
        return "Solicitações em andamento"

    @staticmethod
    def _metric_value(accessible: bool, value: int | None, error: str) -> str:
        if not accessible:
            return "Sem acesso"
        if error and value is None:
            return "Indisponível"
        return "—" if value is None else str(value)

    @staticmethod
    def _metric_detail(accessible: bool, error: str, stale: bool, normal: str) -> str:
        if not accessible:
            return "Permissão de leitura não concedida"
        if error:
            return (
                "Dado em cache; pode estar desatualizado"
                if stale
                else "Não foi possível carregar este indicador"
            )
        return normal

    @rx.var
    def products_detail(self) -> str:
        return self._metric_detail(self.products_accessible, self.products_error, self.products_stale, "Produtos ativos")

    @rx.var
    def stock_detail(self) -> str:
        detail = (
            "Produtos zerados ou abaixo do mínimo"
            if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
            else "Produtos com saldo positivo abaixo do mínimo"
        )
        return self._metric_detail(self.stock_accessible, self.stock_error, self.stock_stale, detail)

    @rx.var
    def stock_message(self) -> str:
        if not self.stock_accessible:
            return "Sem permissão para consultar o estoque."
        if self.stock_error:
            return "Não foi possível atualizar os alertas; os itens anteriores podem estar desatualizados." if self.stock_stale else "Não foi possível carregar os alertas de estoque."
        if not self.stock_alerts:
            return (
                "Nenhum produto com estoque insuficiente."
                if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
                else "Nenhum produto abaixo do estoque mínimo."
            )
        return ""

    @rx.var
    def movements_message(self) -> str:
        if not self.movements_accessible:
            return "Sem permissão para consultar movimentações."
        if self.movements_error:
            return "Os dados anteriores podem estar desatualizados." if self.movements_stale else "Não foi possível carregar as movimentações."
        if not self.recent_movements:
            return "Nenhuma movimentação registrada."
        return ""

    async def load_page(self):
        auth_state = await self.get_state(AuthState)
        auth_result = await auth_state.require_auth()
        if auth_result is not None:
            yield auth_result
            return
        auth_state = await self.get_state(AuthState)
        if not auth_state.session_is_valid:
            return
        self._auth_user_name = auth_state.user_name or ""
        async for event in self.load_dashboard():
            yield event
        from ..state.dashboard_notifications import DashboardNotificationsState
        yield DashboardNotificationsState.load_page

    async def _session(self) -> tuple[str, dict[str, bool]]:
        auth_state = await self.get_state(AuthState)
        if not auth_state.session_is_valid:
            return "", {}
        return (
            str(auth_state.auth_token or "").strip(),
            {
                "products": auth_state.has_permission("product.read"),
                "stock": auth_state.has_permission("stock.read"),
                "movements": auth_state.has_permission("movement.read")
                or auth_state.has_permission("report.read"),
                "purchase_requests": auth_state.has_permission("purchase_request.read"),
                "replenishment": auth_state.has_permission("stock.read")
                and auth_state.has_permission("purchase_request.read"),
            },
        )

    async def open_replenishment(self):
        """Navigate only with a currently validated session and both read grants."""
        auth_state = await self.get_state(AuthState)
        if not auth_state.session_is_valid:
            return
        if not (
            auth_state.has_permission("stock.read")
            and auth_state.has_permission("purchase_request.read")
        ):
            return rx.redirect("/dashboard")
        return rx.redirect("/reposicao")

    @staticmethod
    def _project_stock(response: dict[str, Any]) -> dict[str, Any]:
        items = response.get("items")
        if not isinstance(items, list):
            raise XanoServerError("Os alertas de estoque chegaram em formato inesperado.")
        alerts = []
        for item in items:
            if not isinstance(item, dict):
                continue
            alerts.append(
                {
                    "codigo": str(item.get("codigo") or "—"),
                    "nome": str(item.get("nome") or "Produto sem nome"),
                    "atual": _format_quantity(item.get("quantidade_disponivel")),
                    "minimo": _format_quantity(item.get("estoque_minimo")),
                }
            )
        return {"count": _items_total(response, "produtos abaixo do mínimo"), "items": alerts}

    @staticmethod
    def _project_movements(response: dict[str, Any]) -> dict[str, Any]:
        items = response.get("items")
        if not isinstance(items, list):
            raise XanoServerError("As movimentações chegaram em formato inesperado.")
        movements = []
        for item in items:
            if not isinstance(item, dict):
                raise XanoServerError("A lista contém um registro de movimentação inválido.", status_code=200)
            movement_type = str(item.get("tipo") or "").lower()
            movements.append(
                {
                    "tipo": "Entrada" if movement_type == "entrada" else "Saída" if movement_type == "saida" else "—",
                    "produto": str(item.get("product_name") or item.get("product_code") or "Produto não encontrado"),
                    "quantidade": _format_quantity(item.get("quantidade")),
                    "data": _format_datetime(item.get("data_hora")),
                    "usuario": str(item.get("user_name") or "Usuário não encontrado"),
                }
            )
        return {"items": movements}

    async def load_dashboard(self, retry_failed_only: bool = False):
        try:
            async for event in self._load_dashboard_impl(retry_failed_only):
                yield event
        except Exception as exc:
            logger.warning("Dashboard load interrupted: exception_type=%s", type(exc).__name__)
            self.is_loading = False
            self.error_message = "Não foi possível atualizar o Dashboard. Tente novamente."
            self.retry_sources = list(_DASHBOARD_ENDPOINTS)
            yield
        finally:
            self.is_loading = False

    async def _load_dashboard_impl(self, retry_failed_only: bool = False):
        if self.is_loading or self.chart_loading:
            return
        if retry_failed_only and self.retry_after_epoch > time.time():
            remaining = int(self.retry_after_epoch - time.time() + 0.999)
            self.error_message = f"Aguarde {remaining} segundo(s) antes de tentar novamente."
            return
        self.is_loading = True
        yield

        token, grants = await self._session()
        if not token:
            self.replenishment_accessible = False
            self.is_loading = False
            return

        fingerprint = session_read_cache.session_fingerprint(token)
        if self.session_fingerprint and self.session_fingerprint != fingerprint:
            self._clear_dashboard_data()
        self.session_fingerprint = fingerprint
        self.replenishment_accessible = grants.get("replenishment", False)
        self.purchase_requests_accessible = grants.get("purchase_requests", False)

        # on_load pode ser reenviado ao voltar para a rota. Depois de uma falha,
        # a recuperação deve ser explícita para evitar novas reservas locais.
        if self.has_loaded and self.retry_sources and not retry_failed_only:
            self.is_loading = False
            return

        previous_retry_sources = set(self.retry_sources) if retry_failed_only else set()
        self.retry_sources = []
        self.error_message = ""

        for source, access_attr, value_attr, error_attr, stale_attr in (
            ("products", "products_accessible", "products_count", "products_error", "products_stale"),
            ("stock", "stock_accessible", "below_minimum_count", "stock_error", "stock_stale"),
            ("movements", "movements_accessible", "recent_movements", "movements_error", "movements_stale"),
            (
                "purchase_requests",
                "purchase_requests_accessible",
                "purchase_requests_count",
                "purchase_requests_error",
                "purchase_requests_stale",
            ),
        ):
            permitted = grants.get(source, False)
            setattr(self, access_attr, permitted)
            if not permitted:
                self._clear_source(source)
                session_read_cache.invalidate(endpoint=_dashboard_endpoint(source), token=token)
                setattr(self, error_attr, "")
                setattr(self, stale_attr, False)

        stock_read = (
            (
                {"page": 1, "per_page": DASHBOARD_ALERT_LIMIT},
                DASHBOARD_OPERATIONAL_TTL,
                lambda: auth_client.get_stock_insufficient_summary(
                    token, page=1, per_page=DASHBOARD_ALERT_LIMIT
                ),
                _project_insufficient_stock,
            )
            if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
            else (
                {"situacao": "abaixo_minimo", "page": 1, "per_page": DASHBOARD_ALERT_LIMIT},
                DASHBOARD_OPERATIONAL_TTL,
                lambda: auth_client.list_stock(
                    token,
                    page=1,
                    per_page=DASHBOARD_ALERT_LIMIT,
                    situacao="abaixo_minimo",
                ),
                self._project_stock,
            )
        )
        movement_start, movement_end = period_bounds(self.chart_period)
        movement_params = {"date_from": movement_start, "date_to": movement_end, "period": self.chart_period}
        specs: dict[str, tuple[dict[str, Any], float, Callable[[], Any], Callable[[dict[str, Any]], dict[str, Any]]]] = {
            "products": (
                {"status": "ativo", "page": 1, "per_page": 1},
                DASHBOARD_PRODUCT_TTL,
                lambda: auth_client.list_products(token, page=1, per_page=1, status="ativo"),
                lambda response: _project_count(response, "Produtos ativos"),
            ),
            "stock": stock_read,
            "movements": (
                (movement_params if REAL_DASHBOARD_MOVEMENTS_ENABLED else {"page": 1, "per_page": DASHBOARD_MOVEMENT_LIMIT}),
                DASHBOARD_OPERATIONAL_TTL,
                (lambda: auth_client.get_dashboard_movements(token, **movement_params)) if REAL_DASHBOARD_MOVEMENTS_ENABLED else (lambda: auth_client.list_movements(token, page=1, per_page=DASHBOARD_MOVEMENT_LIMIT)),
                (lambda data: _project_dashboard_movements(data, self.chart_period)) if REAL_DASHBOARD_MOVEMENTS_ENABLED else self._project_movements,
            ),
            "purchase_requests": (
                {},
                DASHBOARD_OPERATIONAL_TTL,
                lambda: auth_client.get_purchase_requests_summary(token),
                _project_purchase_requests_summary,
            ),
        }

        requests: dict[str, asyncio.Task] = {}
        for source, (params, ttl, loader, projector) in specs.items():
            if grants.get(source) and not (
                source == "purchase_requests"
                and self.purchase_requests_error == "forbidden"
            ) and (
                not retry_failed_only or source in previous_retry_sources
            ):
                requests[source] = asyncio.create_task(
                    _cached_dashboard_read(
                        source,
                        token,
                        params,
                        ttl,
                        lambda loader=loader, projector=projector: _project_after(loader, projector),
                        force_refresh=source in previous_retry_sources,
                    )
                )

        results = await asyncio.gather(*requests.values(), return_exceptions=True)
        unauthorized = next((result for result in results if isinstance(result, XanoAuthError)), None)
        if unauthorized is not None:
            self._clear_dashboard_data()
            self.session_fingerprint = ""
            clear_session_read_cache(token)
            self.error_message = "Sua sessão expirou. Entre novamente."
            self.is_loading = False
            yield rx.redirect("/")
            return

        for source, result in zip(requests, results):
            _params, _ttl, _loader, _projector = specs[source]
            value_attr = {
                "products": "products_count",
                "stock": "below_minimum_count",
                "movements": "recent_movements",
                "purchase_requests": "purchase_requests_count",
            }[source]
            error_attr = {
                "products": "products_error",
                "stock": "stock_error",
                "movements": "movements_error",
                "purchase_requests": "purchase_requests_error",
            }[source]
            stale_attr = {
                "products": "products_stale",
                "stock": "stock_stale",
                "movements": "movements_stale",
                "purchase_requests": "purchase_requests_stale",
            }[source]

            if isinstance(result, XanoPermissionError):
                self._clear_source(source)
                if source == "movements":
                    self.chart_error = "Sem acesso aos dados de movimentação."
                setattr(
                    self,
                    error_attr,
                    "forbidden"
                    if source == "purchase_requests"
                    else "A permissão para consultar estes dados não foi autorizada pelo servidor.",
                )
                setattr(self, stale_attr, False)
                if source != "purchase_requests":
                    self.retry_sources.append(source)
                continue
            if isinstance(result, Exception):
                logger.warning(
                    "Dashboard data unavailable: source=%s exception_type=%s status=%s origin=%s",
                    source,
                    type(result).__name__,
                    getattr(result, "status_code", None),
                    _error_origin(result),
                )
                if getattr(result, "status_code", None) == 429:
                    self.retry_after_epoch = max(
                        self.retry_after_epoch, time.time() + _retry_delay_seconds(result)
                    )
                setattr(self, error_attr, "Não foi possível atualizar estes dados. Tente novamente mais tarde.")
                if source == "movements":
                    self.chart_error = (
                        "Dados anteriores podem estar desatualizados."
                        if self.chart_data
                        else "Não foi possível carregar os dados do gráfico."
                    )
                has_previous_data = self._source_has_value(source)
                setattr(self, stale_attr, has_previous_data)
                self.retry_sources.append(source)
                continue

            payload, is_stale, read_error = result
            if source == "products":
                setattr(self, value_attr, payload["count"])
            elif source == "stock":
                self.below_minimum_count = payload["count"]
                self.stock_alerts = payload["items"]
            elif source == "movements":
                self.recent_movements = payload["items"]
                self.chart_data = payload.get("serie", [])
                self.chart_error = "" if REAL_DASHBOARD_MOVEMENTS_ENABLED else "O gráfico de movimentações não está disponível neste ambiente."
            else:
                self.purchase_requests_count = payload["count"]
            setattr(self, error_attr, "" if not is_stale else "Consulta temporariamente indisponível")
            setattr(self, stale_attr, is_stale)
            if is_stale:
                self.retry_sources.append(source)
                if read_error is not None:
                    logger.info(
                        "Dashboard using stale cache: source=%s exception_type=%s status=%s origin=%s",
                        source,
                        type(read_error).__name__,
                        getattr(read_error, "status_code", None),
                        _error_origin(read_error),
                    )
                    if getattr(read_error, "status_code", None) == 429:
                        self.retry_after_epoch = max(
                            self.retry_after_epoch,
                            time.time() + _retry_delay_seconds(read_error),
                        )

        self.has_loaded = True
        if self.retry_sources:
            source_labels = {
                "products": "Produtos",
                "stock": "estoque",
                "movements": "movimentações",
                "purchase_requests": "solicitações de compras",
            }
            failed = ", ".join(source_labels[source] for source in self.retry_sources)
            self.error_message = f"Não foi possível atualizar: {failed}. Confira os dados marcados e tente novamente."
        self.is_loading = False
        if not self.retry_sources:
            self.retry_after_epoch = 0.0
        yield

    def _clear_source(self, source: str) -> None:
        if source == "products":
            self.products_count = None
        elif source == "stock":
            self.below_minimum_count = None
            self.stock_alerts = []
        elif source == "movements":
            self.recent_movements = []
            self.chart_data = []
            self.chart_error = ""
        elif source == "purchase_requests":
            self.purchase_requests_count = None

    def _source_has_value(self, source: str) -> bool:
        if source == "products":
            return self.products_count is not None
        if source == "stock":
            return self.below_minimum_count is not None
        if source == "movements":
            return bool(self.recent_movements)
        return self.purchase_requests_count is not None

    def _clear_dashboard_data(self) -> None:
        for source in _DASHBOARD_ENDPOINTS:
            self._clear_source(source)
        self.products_error = ""
        self.stock_error = ""
        self.movements_error = ""
        self.purchase_requests_error = ""
        self.products_stale = False
        self.stock_stale = False
        self.movements_stale = False
        self.purchase_requests_stale = False
        self.retry_sources = []
        self.replenishment_accessible = False
        self.has_loaded = False

    def retry_dashboard(self):
        if self.is_loading or not self.retry_sources:
            return
        return DashboardState.load_dashboard(True)


async def _project_after(loader: Callable[[], Any], projector: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    response = await loader()
    return projector(response)


def _project_purchase_requests_summary(response: dict[str, Any]) -> dict[str, int]:
    count = response.get("solicitacoes_abertas")
    if type(count) is not int or count < 0:
        raise XanoServerError(
            "A resposta contém uma contagem inválida de solicitações abertas.",
            status_code=200,
        )
    return {"count": count}


def _dashboard_period(now: datetime | None = None) -> tuple[str, str]:
    return period_bounds("7d", now)


def _project_dashboard_movements(response: dict[str, Any], period: str = "7d") -> dict[str, Any]:
    series = response.get("serie")
    recent = response.get("recentes")
    if not isinstance(series, list) or not isinstance(recent, dict) or not isinstance(recent.get("items"), list):
        raise XanoServerError("O resumo diário de movimentações chegou em formato inesperado.", status_code=200)
    projected = DashboardState._project_movements(recent)
    points = []
    for item in series:
        if not isinstance(item, dict) or not isinstance(item.get("dia"), str):
            raise XanoServerError("O resumo contém uma data diária inválida.", status_code=200)
        if type(item.get("entradas")) is not int or item["entradas"] < 0 or type(item.get("saidas")) is not int or item["saidas"] < 0:
            raise XanoServerError("O resumo contém totais diários inválidos.", status_code=200)
        day = datetime.strptime(item["dia"], "%Y-%m" if period == "12m" else "%Y-%m-%d").strftime("%m/%Y" if period == "12m" else "%d/%m")
        points.append({"dia": day, "entradas": item["entradas"], "saidas": item["saidas"]})
    if len(points) != {"7d": 7, "30d": 30, "12m": 12}[period]:
        raise XanoServerError("O resumo não inclui todo o período solicitado.", status_code=200)
    return {"items": projected["items"], "serie": points}


def _metric_card(
    title: str,
    icon: str,
    value: rx.Var,
    detail: rx.Var,
    *,
    on_click=None,
    actionable: rx.Var | bool = False,
    tone: str = "mint",
    icon_color: str = SAGE_DARK,
) -> rx.Component:
    interaction_props = {}
    if on_click is not None:
        interaction_props = {
            "on_click": on_click,
            "cursor": rx.cond(actionable, "pointer", "default"),
            "role": "link",
            "tab_index": rx.cond(actionable, 0, -1),
            "aria_disabled": ~actionable,
        }
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(title, color=TEXT_SECONDARY, font_size="12px", font_weight="620"),
                rx.box(
                    rx.icon(tag=icon, size=17, color=icon_color),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    width="34px",
                    height="34px",
                    border_radius="11px",
                    background="rgba(255,255,255,0.66)",
                    flex_shrink="0",
                ),
                width="100%",
                align="center",
                justify="between",
            ),
            rx.heading(value, font_size="27px", font_weight="760", letter_spacing="-0.8px", line_height="1.2", color="#384A40", margin="10px 0 2px", overflow_wrap="anywhere"),
            rx.text(detail, color=TEXT_MUTED, font_size="11px"),
            align="start",
            spacing="0",
            width="100%",
        ),
        border="1px solid #E9EFEB",
        border_radius=PANEL_RADIUS,
        padding="17px 18px",
        background=SECTION_SURFACES[tone],
        min_height="131px",
        height="100%",
        width="100%",
        min_width="0",
        **interaction_props,
    )


def _purchase_requests_card() -> rx.Component:
    return _metric_card(
        "Solicitações de Compras",
        "clipboard-list",
        DashboardState.purchase_requests_value,
        DashboardState.purchase_requests_detail,
        tone="rose",
        icon_color=ROSE_TEXT,
    )


def _movement_grid_row(*cells: rx.Component, header: bool = False) -> rx.Component:
    """Use shared responsive tracks so headers and records stay aligned."""
    return rx.box(
        *cells,
        display="grid",
        grid_template_columns=_MOVEMENT_GRID_COLUMNS,
        column_gap=_MOVEMENT_GRID_COLUMN_GAP,
        row_gap=_MOVEMENT_GRID_ROW_GAP,
        align_items="center",
        width="100%",
        min_width="0",
        box_sizing="border-box",
        padding="11px 12px" if header else "12px",
        font_size="9px" if header else "12px",
        text_transform="uppercase" if header else "none",
        letter_spacing="0.8px" if header else "normal",
        background="#F8FAF8" if header else "transparent",
        border_bottom=f"1px solid {BORDER_SOFT}",
        role="row",
    )


def _movement_header() -> rx.Component:
    return _movement_grid_row(
        rx.text("Tipo", weight="bold", color=TEXT_SECONDARY, text_align="left", min_width="0", role="columnheader"),
        rx.text("Produto", weight="bold", color=TEXT_SECONDARY, text_align="left", min_width="0", role="columnheader"),
        rx.text("Qtde.", weight="bold", color=TEXT_SECONDARY, text_align="left", min_width="0", role="columnheader"),
        rx.text("Data", weight="bold", color=TEXT_SECONDARY, text_align="left", min_width="0", role="columnheader"),
        rx.text("Usuário", weight="bold", color=TEXT_SECONDARY, text_align="left", min_width="0", role="columnheader"),
        header=True,
    )


def _movement_row(item: dict[str, str]) -> rx.Component:
    movement_color = rx.cond(item["tipo"] == "Entrada", SUCCESS_TEXT, ROSE_TEXT)
    return _movement_grid_row(
        rx.text(
            item["tipo"],
            color=movement_color,
            weight="medium",
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
        rx.text(
            item["produto"],
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
        rx.text(
            item["quantidade"],
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            font_variant_numeric="tabular-nums",
            role="cell",
        ),
        rx.text(
            item["data"],
            color=TEXT_MUTED,
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
        rx.text(
            item["usuario"],
            color=TEXT_SECONDARY,
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
    )


def _stock_alert_progress(current: str | rx.Var, minimum_value: str | rx.Var) -> tuple[rx.Var, rx.Var]:
    """Proporção visual dos valores exibidos, sem autoridade sobre operações de estoque."""
    minimum = rx.Var.create(minimum_value)
    quantity = rx.Var.create(current)
    has_ratio = (minimum != "0") & (minimum != "—") & (quantity != "—")
    ratio = quantity.replace(",", ".").to(float) / minimum.replace(",", ".").to(float) * 100
    percentage = rx.cond(has_ratio, rx.cond(ratio > 100, 100, ratio), 0)
    return has_ratio, percentage


def _stock_alert(item: dict[str, str]) -> rx.Component:
    has_ratio, percentage = _stock_alert_progress(item["atual"], item["minimo"])
    situation = (
        rx.text(
            rx.cond(item["situacao_estoque"] == "sem_estoque", "Sem estoque", "Abaixo do mínimo"),
            font_size="10px",
            color=WARNING_TEXT,
        )
        if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
        else rx.fragment()
    )
    unit = item["unidade_medida"] if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED else ""
    return rx.vstack(
        rx.hstack(
            rx.text(item["nome"], font_size="12px", font_weight="650", color=TEXT_PRIMARY, overflow_wrap="anywhere", min_width="0"),
            rx.text(item["atual"], " ", unit, font_size="12px", font_weight="730", color=TEXT_PRIMARY, white_space="nowrap"),
            width="100%",
            justify="between",
            align="center",
            gap="10px",
        ),
        rx.hstack(
            rx.text("Mínimo: ", item["minimo"], " ", unit, " · Código ", item["codigo"], font_size="10px", color=TEXT_MUTED),
            situation,
            width="100%",
            justify="between",
            align="start",
            gap="10px",
        ),
        rx.cond(
            has_ratio,
            rx.box(
                rx.box(width=percentage.to_string() + "%", height="100%", border_radius="6px", background=PEACH),
                width="100%",
                height="7px",
                border_radius="6px",
                background="#F0F2EF",
                role="progressbar",
                aria_label="Saldo atual em relação ao estoque mínimo",
                aria_valuenow=percentage,
                aria_valuemin=0,
                aria_valuemax=100,
            ),
            rx.fragment(),
        ),
        width="100%",
        align="stretch",
        gap="4px",
    )


def _dashboard_panel(title: str, body: rx.Component, *, attention: bool = False) -> rx.Component:
    return rx.box(
        rx.vstack(
            *([rx.heading(title, font_size="15px", font_weight="650", letter_spacing="-0.2px", line_height="1.3")] if title else []),
            body,
            width="100%",
            align="stretch",
            gap="15px",
        ),
        width="100%",
        min_width="0",
        height="100%",
        padding=rx.breakpoints({"0px": "15px", "701px": "19px"}),
        border=f"1px solid {BORDER_SOFT}",
        border_radius=PANEL_RADIUS,
        background=SURFACE,
        box_shadow="0 3px 12px rgba(45,65,54,0.025)",
    )


def _recent_movements_panel() -> rx.Component:
    return _dashboard_panel(
        "Movimentações recentes",
        rx.vstack(
            rx.cond(
                DashboardState.movements_accessible & (DashboardState.recent_movements.length() > 0),
                rx.box(
                    _movement_header(),
                    rx.foreach(DashboardState.recent_movements, _movement_row),
                    display="block",
                    width="100%",
                    min_width="0",
                    role="table",
                    aria_label="Movimentações recentes",
                ),
                rx.fragment(),
            ),
            rx.cond(
                DashboardState.movements_message != "",
                rx.text(DashboardState.movements_message, color=TEXT_MUTED, size="2"),
                rx.fragment(),
            ),
            width="100%",
            align="stretch",
            spacing="2",
        ),
    )


def _stock_alerts_panel() -> rx.Component:
    return _dashboard_panel(
        "",
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Atenção ao estoque", font_size="15px", font_weight="650", letter_spacing="-0.2px"),
                    rx.text("Produtos abaixo do mínimo ou sem estoque" if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED else "Produtos abaixo do mínimo", font_size="11px", color=TEXT_MUTED),
                    align="start",
                    spacing="1",
                ),
                rx.cond(
                    DashboardState.replenishment_accessible,
                    rx.link("Ver todos →", href="/reposicao", font_size="11px", weight="bold", color=SAGE_DARK, text_decoration="none"),
                    rx.fragment(),
                ),
                width="100%",
                justify="between",
                align="center",
                gap="12px",
            ),
            rx.cond(
                DashboardState.stock_accessible & (DashboardState.stock_alerts.length() > 0),
                rx.vstack(rx.foreach(DashboardState.stock_alerts, _stock_alert), width="100%", align="stretch", gap="14px", aria_label="Alertas de estoque"),
                rx.fragment(),
            ),
            rx.cond(
                DashboardState.stock_message != "",
                rx.text(DashboardState.stock_message, color=TEXT_MUTED, size="2"),
                rx.fragment(),
            ),
            width="100%",
            align="stretch",
            gap="15px",
        ),
        attention=True,
    )


def _dashboard_heading() -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.hstack(
                rx.cond(
                    DashboardState.first_name != "",
                    rx.heading(DashboardState.greeting, ", ", DashboardState.first_name, font_size="27px", letter_spacing="-0.8px", color="#35423C"),
                    rx.heading(DashboardState.greeting, font_size="27px", letter_spacing="-0.8px", color="#35423C"),
                ),
                gap="8px",
                align="center",
            ),
            align="start",
            spacing="1",
        ),
        width="100%",
        justify="between",
        align="end",
        wrap="wrap",
        gap="18px",
        margin_bottom="7px",
    )


def dashboard() -> rx.Component:
    return page(
        "Dashboard",
        rx.vstack(
            _dashboard_heading(),
            rx.cond(
                DashboardState.is_loading,
                rx.hstack(rx.spinner(size="1"), rx.text("Atualizando dados...", size="2", color=TEXT_MUTED), align="center", spacing="2"),
                rx.fragment(),
            ),
            rx.cond(
                DashboardState.error_message != "",
                rx.hstack(
                    rx.text(DashboardState.error_message, color=WARNING_TEXT, size="2"),
                    rx.button(
                        "Tentar novamente",
                        on_click=DashboardState.retry_dashboard,
                        disabled=DashboardState.is_loading,
                        variant="soft",
                        size="1",
                    ),
                    align="center",
                    wrap="wrap",
                    spacing="2",
                ),
                rx.fragment(),
            ),
            rx.grid(
                _metric_card(
                    "Produtos ativos",
                    "package",
                    DashboardState.products_value,
                    DashboardState.products_detail,
                    tone="mint",
                    icon_color=SAGE_DARK,
                ),
                _purchase_requests_card(),
                _metric_card(
                    "Estoque insuficiente" if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED else "Abaixo do mínimo",
                    "triangle-alert",
                    DashboardState.stock_value,
                    DashboardState.stock_detail,
                    on_click=DashboardState.open_replenishment,
                    actionable=DashboardState.replenishment_accessible,
                    tone="peach",
                    icon_color=WARNING_TEXT,
                ),
                width="100%",
                grid_template_columns=rx.breakpoints({"0px": "repeat(2, minmax(0, 1fr))", "1051px": "repeat(3, minmax(0, 1fr))"}),
                gap=DASHBOARD_GAP,
                align_items="stretch",
            ),
            rx.grid(
                _dashboard_panel(
                    "",
                    stock_movement_chart(DashboardState.chart_data, status_message=DashboardState.chart_error,
                                         period=DashboardState.chart_period, on_period_change=DashboardState.change_chart_period,
                                         loading=DashboardState.chart_loading | DashboardState.is_loading, enabled=DashboardState.chart_enabled),
                ),
                _stock_alerts_panel(),
                grid_template_columns=rx.breakpoints(
                    {"0px": "minmax(0, 1fr)", "1051px": "minmax(0, 1.5fr) minmax(280px, 0.9fr)"},
                ),
                width="100%",
                min_width="0",
                align_items="stretch",
                gap=DASHBOARD_GAP,
            ),
            _recent_movements_panel(),
            width="100%",
            align="stretch",
            gap="18px",
        ),
    )
