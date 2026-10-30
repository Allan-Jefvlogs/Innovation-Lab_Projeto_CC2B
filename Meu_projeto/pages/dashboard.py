"""Dashboard com resumos reais fornecidos pelos endpoints existentes do Xano."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import reflex as rx

from ..components.layout import page, section
from ..services.session_read_cache import CACHE_MISS, session_read_cache
from ..services.session_read_cache import clear_session_read_cache
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
DASHBOARD_ALERT_LIMIT = 5
DASHBOARD_MOVEMENT_LIMIT = 5
DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED = os.getenv(
    "NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", "false"
).strip().lower() in {"1", "true", "yes", "on"}
_INSUFFICIENT_SUMMARY_ENDPOINT = "GET /stock/insufficient_summary"
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
    if source == "stock" and DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED:
        return _INSUFFICIENT_SUMMARY_ENDPOINT
    return _DASHBOARD_ENDPOINTS[source]


def _items_total(response: dict[str, Any], source: str) -> int:
    try:
        total = int(response["itemsTotal"])
    except (KeyError, TypeError, ValueError) as exc:
        raise XanoServerError(
            f"O Xano não retornou a contagem paginada de {source}.", status_code=200
        ) from exc
    if total < 0:
        raise XanoServerError(
            f"O Xano retornou uma contagem inválida de {source}.", status_code=200
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
        result = await loader()
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
            "O Xano retornou um resumo de estoque insuficiente em formato inesperado.",
            status_code=200,
        )

    alerts: list[dict[str, str]] = []
    seen_product_ids: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            raise XanoServerError("O Xano retornou um alerta de estoque inválido.", status_code=200)
        product_id = item.get("product_id")
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            raise XanoServerError("O Xano retornou um ID de Produto inválido.", status_code=200)
        if product_id in seen_product_ids:
            raise XanoServerError("O Xano retornou Produtos duplicados no resumo.", status_code=200)
        seen_product_ids.add(product_id)

        code = item.get("codigo")
        name = item.get("nome")
        unit = item.get("unidade_medida")
        if not all(isinstance(value, str) and value.strip() for value in (code, name, unit)):
            raise XanoServerError("O Xano retornou campos de Produto inválidos.", status_code=200)
        try:
            quantity = Decimal(str(item["quantidade_disponivel"]))
            minimum = Decimal(str(item["estoque_minimo"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise XanoServerError("O Xano retornou quantidades de estoque inválidas.", status_code=200) from exc
        if not quantity.is_finite() or not minimum.is_finite() or quantity < 0 or minimum < 0:
            raise XanoServerError("O Xano retornou quantidades de estoque inválidas.", status_code=200)

        situation = item.get("situacao_estoque")
        if quantity == 0:
            expected_situation = "sem_estoque"
        elif quantity < minimum:
            expected_situation = "abaixo_minimo"
        else:
            raise XanoServerError("O Xano incluiu um Produto sem necessidade de reposição.", status_code=200)
        if situation != expected_situation:
            raise XanoServerError("O Xano retornou uma situação de estoque incompatível.", status_code=200)

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
        async for event in self.load_dashboard():
            yield event

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
            raise XanoServerError("O Xano retornou alertas de estoque em formato inesperado.")
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
            raise XanoServerError("O Xano retornou movimentações em formato inesperado.")
        movements = []
        for item in items:
            if not isinstance(item, dict):
                continue
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
        if self.is_loading:
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
        specs: dict[str, tuple[dict[str, Any], float, Callable[[], Any], Callable[[dict[str, Any]], dict[str, Any]]]] = {
            "products": (
                {"status": "ativo", "page": 1, "per_page": 1},
                DASHBOARD_PRODUCT_TTL,
                lambda: auth_client.list_products(token, page=1, per_page=1, status="ativo"),
                lambda response: _project_count(response, "Produtos ativos"),
            ),
            "stock": stock_read,
            "movements": (
                {"page": 1, "per_page": DASHBOARD_MOVEMENT_LIMIT},
                DASHBOARD_OPERATIONAL_TTL,
                lambda: auth_client.list_movements(token, page=1, per_page=DASHBOARD_MOVEMENT_LIMIT),
                self._project_movements,
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
                setattr(self, error_attr, "Falha ao consultar o Xano.")
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
            "O Xano retornou uma contagem de solicitações abertas inválida.",
            status_code=200,
        )
    return {"count": count}


def _metric_card(
    title: str,
    icon: str,
    value: rx.Var,
    detail: rx.Var,
    *,
    on_click=None,
    actionable: rx.Var | bool = False,
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
                rx.icon(tag=icon, size=18, color="#2563EB"),
                rx.text(title, color="#475569", size="2", weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.heading(value, size="7", color="#0F172A"),
            rx.text(detail, color="#64748B", size="1"),
            align="start",
            spacing="2",
        ),
        border="1px solid #DBEAFE",
        border_radius="12px",
        padding="20px",
        background="white",
        box_shadow="0 1px 3px rgba(15, 23, 42, 0.05)",
        flex="1",
        min_width="190px",
        **interaction_props,
    )


def _purchase_requests_card() -> rx.Component:
    return _metric_card(
        "Solicitações de Compras",
        "clipboard-list",
        DashboardState.purchase_requests_value,
        DashboardState.purchase_requests_detail,
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
        padding="0.7rem 0.5rem" if header else "0.8rem 0.5rem",
        border_bottom="1px solid #CBD5E1" if header else "1px solid #E2E8F0",
        role="row",
    )


def _movement_header() -> rx.Component:
    return _movement_grid_row(
        rx.text("Tipo", weight="bold", color="#475569", text_align="left", min_width="0", role="columnheader"),
        rx.text("Produto", weight="bold", color="#475569", text_align="left", min_width="0", role="columnheader"),
        rx.text("Qtde.", weight="bold", color="#475569", text_align="left", min_width="0", role="columnheader"),
        rx.text("Data", weight="bold", color="#475569", text_align="left", min_width="0", role="columnheader"),
        rx.text("Usuário", weight="bold", color="#475569", text_align="left", min_width="0", role="columnheader"),
        header=True,
    )


def _movement_row(item: dict[str, str]) -> rx.Component:
    movement_color = rx.cond(item["tipo"] == "Entrada", "#15803D", "#1D4ED8")
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
            color="#64748B",
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
        rx.text(
            item["usuario"],
            color="#475569",
            text_align="left",
            white_space="normal",
            overflow_wrap="anywhere",
            min_width="0",
            role="cell",
        ),
    )


def _stock_alert(item: dict[str, str]) -> rx.Component:
    summary_detail = (
        rx.text(
            rx.cond(item["situacao_estoque"] == "sem_estoque", "Sem estoque", "Abaixo do mínimo"),
            " · ",
            item["unidade_medida"],
            size="1",
            color="#64748B",
        )
        if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED
        else rx.fragment()
    )
    return rx.hstack(
        rx.icon(tag="triangle-alert", size=16, color="#B45309"),
        rx.vstack(
            rx.text(item["nome"], weight="medium", color="#334155"),
            rx.text("Código ", item["codigo"], size="1", color="#64748B"),
            summary_detail,
            align="start",
            spacing="0",
            flex="1",
        ),
        rx.text(item["atual"], " / ", item["minimo"], color="#92400E", weight="medium", white_space="nowrap"),
        width="100%",
        align="center",
        padding="0.55rem 0",
        border_bottom="1px solid #FEF3C7",
    )


def dashboard() -> rx.Component:
    return page(
        "Dashboard",
        rx.vstack(
            rx.text("Visão geral do estoque e das movimentações recentes.", color="#64748B"),
            rx.cond(
                DashboardState.is_loading,
                rx.hstack(rx.spinner(size="1"), rx.text("Atualizando dados do Xano...", size="2", color="#64748B"), align="center", spacing="2"),
                rx.fragment(),
            ),
            rx.cond(
                DashboardState.error_message != "",
                rx.hstack(
                    rx.text(DashboardState.error_message, color="#92400E", size="2"),
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
            rx.flex(
                _metric_card("Produtos ativos", "package", DashboardState.products_value, DashboardState.products_detail),
                _purchase_requests_card(),
                _metric_card(
                    "Estoque insuficiente" if DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED else "Abaixo do mínimo",
                    "triangle-alert",
                    DashboardState.stock_value,
                    DashboardState.stock_detail,
                    on_click=DashboardState.open_replenishment,
                    actionable=DashboardState.replenishment_accessible,
                ),
                width="100%",
                gap="16px",
                margin_bottom="4px",
                wrap="wrap",
            ),
            rx.flex(
                rx.box(
                    section(
                        "Movimentações recentes",
                        rx.vstack(
                            rx.cond(
                                DashboardState.movements_accessible
                                & (DashboardState.recent_movements.length() > 0),
                                rx.box(
                                    rx.box(
                                        _movement_header(),
                                        rx.foreach(DashboardState.recent_movements, _movement_row),
                                        display="block",
                                        width="100%",
                                            min_width="0",
                                        role="table",
                                        aria_label="Movimentações recentes",
                                    ),
                                    width="100%",
                                    min_width="0",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                DashboardState.movements_message != "",
                                rx.text(DashboardState.movements_message, color="#64748B", size="2"),
                                rx.fragment(),
                            ),
                            width="100%",
                            align="stretch",
                            spacing="2",
                        ),
                    ),
                    width="100%",
                    flex="1.5",
                    min_width="360px",
                ),
                rx.box(
                    section(
                        "Alertas de estoque",
                        rx.vstack(
                            rx.cond(
                                DashboardState.stock_accessible & (DashboardState.stock_alerts.length() > 0),
                                rx.vstack(rx.foreach(DashboardState.stock_alerts, _stock_alert), width="100%", align="stretch", spacing="0"),
                                rx.fragment(),
                            ),
                            rx.cond(
                                DashboardState.stock_message != "",
                                rx.text(DashboardState.stock_message, color="#64748B", size="2"),
                                rx.fragment(),
                            ),
                            width="100%",
                            align="stretch",
                            spacing="2",
                        ),
                    ),
                    width="100%",
                    flex="1",
                    min_width="300px",
                ),
                width="100%",
                align="start",
                gap="16px",
                wrap="wrap",
            ),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
