import math
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import reflex as rx

from ..components.theme import BORDER, BORDER_SOFT, ERROR_TEXT, SUCCESS_TEXT, SURFACE, SURFACE_ALT, TABLE_HEADER, TEXT_MUTED, WARNING_TEXT

from ..components.layout import page, section
from ..components.searchable_select import normalize_search_text, searchable_select
from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoError,
    XanoPermissionError,
    XanoServerError,
    XanoRequestError,
    auth_client,
)
from ..services.session_read_cache import CACHE_MISS, session_read_cache
from ..state import AuthState

PRODUCT_UNITS = (
    ("UN", "Unidade"),
    ("CX", "Caixa"),
    ("RL", "Rolo"),
    ("PCT", "Pacote"),
    ("PAR", "Par"),
    ("KG", "Quilograma"),
    ("L", "Litro"),
    ("MT", "Metro"),
)
PRODUCT_UNIT_CODES = tuple(code for code, _label in PRODUCT_UNITS)


def _cache_ttl(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(0.0, value)


PRODUCTS_CACHE_TTL_SECONDS = _cache_ttl("NEXSTOCK_PRODUCTS_CACHE_TTL_SECONDS", 30.0)
REFERENCE_CACHE_TTL_SECONDS = _cache_ttl("NEXSTOCK_REFERENCE_CACHE_TTL_SECONDS", 120.0)
_CACHE_MISS = CACHE_MISS


_CACHE_SCOPES = {
    "products": "product_catalog_read",
    "categories": "product_reference_read",
    "category_by_id": "product_reference_read",
    "suppliers": "product_reference_read",
    "supplier_by_id": "product_reference_read",
}
_CACHE_ENDPOINTS = {
    "products": "GET /products",
    "categories": "GET /categories",
    "category_by_id": "GET /categories/by_id/{category_id}",
    "suppliers": "GET /suppliers",
    "supplier_by_id": "GET /suppliers/by_id/{supplier_id}",
}


def _session_fingerprint(token: str) -> str:
    return session_read_cache.session_fingerprint(token)


def _cache_key(
    namespace: str, token: str, params: dict[str, Any]
) -> tuple[str, str, str, str]:
    return session_read_cache.key(
        _CACHE_SCOPES[namespace], _CACHE_ENDPOINTS[namespace], token, params
    )


def _cache_get(
    key: tuple[str, str, str, str], ttl: float, *, allow_stale: bool = False
) -> tuple[Any, bool]:
    return session_read_cache.get(key, ttl, allow_stale=allow_stale)


def _cache_set(key: tuple[str, str, str, str], value: Any) -> None:
    ttl = (
        PRODUCTS_CACHE_TTL_SECONDS
        if key[1] == _CACHE_ENDPOINTS["products"]
        else REFERENCE_CACHE_TTL_SECONDS
    )
    session_read_cache.set(key, value, ttl)


def _cache_clear() -> None:
    """Clear the in-process cache; also used to isolate cache tests."""
    session_read_cache.clear()


async def _cached_reference_call(
    namespace: str,
    token: str,
    params: dict[str, Any],
    loader,
    *,
    cache_allowed: bool = True,
    cache_fields: tuple[str, ...],
) -> Any:
    if not cache_allowed:
        return await loader()
    key = _cache_key(namespace, token, params)
    cached, fresh = _cache_get(key, REFERENCE_CACHE_TTL_SECONDS)
    if fresh:
        return cached
    result = await loader()
    if isinstance(result, dict):
        if isinstance(result.get("items"), list):
            cached_result = {
                name: result[name]
                for name in ("itemsReceived", "itemsTotal", "page", "perPage")
                if name in result
            }
            cached_result["items"] = [
                {field: item[field] for field in cache_fields if field in item}
                for item in result["items"]
                if isinstance(item, dict)
            ]
        else:
            cached_result = {
                field: result[field] for field in cache_fields if field in result
            }
        _cache_set(key, cached_result)
    return result


def _normalize_product_unit(value: object) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in PRODUCT_UNIT_CODES else ""


def _is_temporary_xano_failure(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    return isinstance(error, XanoConnectionError) or status_code == 429 or (
        isinstance(status_code, int) and status_code >= 500
    )


def _map_product_to_list_item(
    item: dict[str, Any],
    stock_by_product: dict[str, dict[str, Any]],
) -> dict[str, str]:
    product_id = str(item.get("id", ""))
    stock = stock_by_product.get(product_id)
    stock_quantity = stock.get("quantidade_disponivel") if stock else None
    stock_minimum = stock.get("estoque_minimo") if stock else None
    if stock_minimum is None:
        stock_minimum = item.get("estoque_minimo")

    situation_labels = {
        "sem_estoque": "Sem estoque",
        "abaixo_minimo": "Abaixo do m\u00ednimo",
        "normal": "Normal",
    }
    if stock is None:
        stock_situation = "Saldo n\u00e3o encontrado"
    else:
        stock_situation = situation_labels.get(
            str(stock.get("situacao_estoque") or ""), "Situa\u00e7\u00e3o desconhecida"
        )

    category_id = item.get("categoria_id")
    if category_id is None:
        category_name = "Sem categoria"
    else:
        category_name = str(item.get("categoria_nome") or "Categoria n\u00e3o encontrada")

    return {
        "id": product_id,
        "codigo": str(item.get("codigo") or "\u2014"),
        "nome": str(item.get("nome") or "\u2014"),
        "categoria": category_name,
        "unidade_medida": _normalize_product_unit(item.get("unidade_medida"))
        or str(item.get("unidade_medida") or "\u2014"),
        "quantidade_disponivel": (
            str(stock_quantity) if stock_quantity is not None else "\u2014"
        ),
        "estoque_minimo": str(stock_minimum) if stock_minimum is not None else "\u2014",
        "status": str(item.get("status") or "\u2014"),
        "situacao_estoque": stock_situation,
    }


_PRODUCT_LIST_PARAMS = {"page": 1, "per_page": 100, "stock_per_page": 100}
_EDIT_PRODUCT_FIELDS = (
    "id",
    "codigo",
    "nome",
    "descricao",
    "categoria_id",
    "fornecedor_padrao_id",
    "unidade_medida",
    "estoque_minimo",
    "status",
)


def _products_listing_key(token: str) -> tuple[str, str, str, str]:
    return _cache_key("products", token, _PRODUCT_LIST_PARAMS)


def _invalidate_products_cache(token: str) -> None:
    session_read_cache.invalidate(endpoint=_CACHE_ENDPOINTS["products"], token=token)


def _cached_product_detail(token: str, product_id: int) -> dict[str, Any] | None:
    cached, fresh = _cache_get(_products_listing_key(token), PRODUCTS_CACHE_TTL_SECONDS)
    if not fresh or not isinstance(cached, dict):
        return None
    record = next(
        (
            item
            for item in cached.get("records", [])
            if isinstance(item, dict) and str(item.get("id")) == str(product_id)
        ),
        None,
    )
    if record is None or not set(_EDIT_PRODUCT_FIELDS).issubset(record):
        return None
    return record


def _update_cached_product(
    token: str,
    product_id: int,
    fields: dict[str, Any],
    record_fields: dict[str, Any] | None = None,
) -> None:
    key = _products_listing_key(token)
    cached, fresh = _cache_get(key, PRODUCTS_CACHE_TTL_SECONDS, allow_stale=True)
    if cached is _CACHE_MISS or not isinstance(cached, dict):
        return
    found = False
    for product in cached.get("items", []):
        if product.get("id") != str(product_id):
            continue
        product.update({name: str(value) for name, value in fields.items()})
        if "estoque_minimo" in fields:
            try:
                quantity = Decimal(str(product.get("quantidade_disponivel", "")))
                minimum = Decimal(str(fields["estoque_minimo"]))
                if quantity <= 0:
                    product["situacao_estoque"] = "Sem estoque"
                elif minimum > 0 and quantity < minimum:
                    product["situacao_estoque"] = "Abaixo do m\u00ednimo"
                else:
                    product["situacao_estoque"] = "Normal"
            except (InvalidOperation, TypeError, ValueError):
                # Sem uma quantidade verific\u00e1vel, preserva a situa\u00e7\u00e3o atual.
                pass
        found = True
        break
    if not found:
        return
    for record in cached.get("records", []):
        if isinstance(record, dict) and str(record.get("id")) == str(product_id):
            record.update(record_fields or fields)
            break
    if fresh:
        _cache_set(key, cached)
        return
    # A escrita atualiza o item editado, mas n\u00e3o torna novamente confi\u00e1vel
    # uma listagem que j\u00e1 havia expirado.
    session_read_cache.update_preserving_age(key, cached)


class ProductsState(rx.State):
    """Estado da listagem e dos formulários reais de Produto."""

    products: list[dict[str, str]] = []
    search_query: str = ""
    category_options: list[dict[str, str]] = []
    category_selection: str = ""
    category_search_query: str = ""
    category_dropdown_open: bool = False
    category_page: int = 1
    category_has_more: bool = False
    category_loading_more: bool = False
    supplier_options: list[dict[str, str]] = []
    supplier_selection: str = "none"
    supplier_search_query: str = "Sem fornecedor padrão"
    supplier_dropdown_open: bool = False
    supplier_page: int = 1
    supplier_has_more: bool = False
    supplier_loading_more: bool = False
    codigo: str = ""
    nome: str = ""
    descricao: str = ""
    unidade_medida: str = ""
    estoque_minimo: str = ""
    product_id: int = 0
    original_product_status: str = ""
    current_product_status: str = ""
    original_product: dict[str, str] = {}
    is_loading: bool = False
    is_saving: bool = False
    is_status_loading: bool = False
    can_read_products: bool = False
    can_read_categories: bool = False
    can_read_suppliers: bool = False
    can_create_products: bool = False
    can_update_products: bool = False
    can_activate_products: bool = False
    can_inactivate_products: bool = False
    has_loaded_product: bool = False
    edit_load_failed: bool = False
    can_retry_edit_load: bool = False
    has_products: bool = False
    products_stale: bool = False
    products_status_message: str = ""
    products_session_fingerprint: str = ""
    error_message: str = ""
    category_error_message: str = ""
    supplier_error_message: str = ""
    success_message: str = ""

    @rx.var
    def filtered_products(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.search_query)
        if not query:
            return self.products
        searchable_fields = ("codigo", "nome", "categoria")
        return [
            product
            for product in self.products
            if any(
                query in normalize_search_text(product.get(field, ""))
                for field in searchable_fields
            )
        ]

    @rx.var
    def has_filtered_products(self) -> bool:
        return bool(self.filtered_products)

    @rx.var
    def filtered_category_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.category_search_query)
        return [
            option for option in self.category_options
            if not query or query in normalize_search_text(option.get("label", ""))
        ]

    @rx.var
    def filtered_supplier_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.supplier_search_query)
        return [
            option for option in self.supplier_options
            if not query or query in normalize_search_text(option.get("label", ""))
        ]

    @rx.var
    def status_action_label(self) -> str:
        return "Inativar produto" if self.current_product_status == "ativo" else "Ativar produto"

    @rx.var
    def can_change_product_status(self) -> bool:
        if (
            not self.has_loaded_product
            or self.is_loading
            or self.edit_load_failed
            or self.category_error_message
            or self.supplier_error_message
        ):
            return False
        if self.current_product_status != self.original_product_status:
            # A ação desfaz a alteração local pendente; não persiste status.
            return True
        if self.current_product_status == "ativo":
            return self.can_inactivate_products
        if self.current_product_status == "inativo":
            return self.can_activate_products
        return False

    @rx.var
    def is_product_active(self) -> bool:
        return self.current_product_status == "ativo"

    def load_page(self):
        return [AuthState.require_auth(), ProductsState.load_products()]

    def load_create_page(self):
        return [AuthState.require_auth(), ProductsState.load_create_form()]

    def load_edit_page(self):
        return [AuthState.require_auth(), ProductsState.load_edit_form()]

    def change_search_query(self, value: str):
        self.search_query = value

    def change_codigo(self, value: str):
        self.codigo = value

    def change_nome(self, value: str):
        self.nome = value

    def change_descricao(self, value: str):
        self.descricao = value

    def search_categories(self, value: str):
        self.category_search_query = value
        self.category_dropdown_open = True
        self.supplier_dropdown_open = False

    def search_suppliers(self, value: str):
        self.supplier_search_query = value
        self.supplier_dropdown_open = True
        self.category_dropdown_open = False

    def open_category_options(self):
        self.category_dropdown_open = True
        self.supplier_dropdown_open = False
        self.category_search_query = ""

    def close_category_options(self, value: str = ""):
        self.category_dropdown_open = False
        selected = next(
            (item for item in self.category_options if item["id"] == str(self.category_selection)),
            None,
        )
        if selected is not None:
            self.category_search_query = selected["label"]

    def close_category_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.close_category_options()

    def open_supplier_options(self):
        self.supplier_dropdown_open = True
        self.category_dropdown_open = False
        self.supplier_search_query = ""

    def close_supplier_options(self, value: str = ""):
        self.supplier_dropdown_open = False
        if self.supplier_selection == "none":
            self.supplier_search_query = "Sem fornecedor padrão"
            return
        selected = next(
            (item for item in self.supplier_options if item["id"] == str(self.supplier_selection)),
            None,
        )
        if selected is not None:
            self.supplier_search_query = selected["label"]

    def close_supplier_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.close_supplier_options()

    def select_category(self, category_id: str):
        selected_id = str(category_id)
        option = next((item for item in self.category_options if item["id"] == selected_id), None)
        if option and option.get("disabled") != "true":
            self.category_selection = selected_id
            self.category_search_query = option["label"]
            self.category_dropdown_open = False

    def select_supplier(self, supplier_id: str):
        selected_id = str(supplier_id)
        option = next((item for item in self.supplier_options if item["id"] == selected_id), None)
        if (
            option
            and option.get("disabled") != "true"
            and (selected_id == "none" or option.get("status") == "ativo")
        ):
            self.supplier_selection = selected_id
            self.supplier_search_query = option["label"]
            self.supplier_dropdown_open = False

    async def _validate_active_supplier(self, token: str, supplier_id: int) -> bool:
        try:
            supplier = await auth_client.get_supplier(token, supplier_id)
        except XanoRequestError as exc:
            if exc.error_code == "NOT_FOUND":
                self.error_message = "O Fornecedor selecionado não existe. Escolha um Fornecedor ativo."
                return False
            raise
        if supplier.get("status") != "ativo":
            self.error_message = "O Fornecedor selecionado está inativo. Escolha um Fornecedor ativo."
            return False
        return True

    def change_unidade_medida(self, value: str):
        self.unidade_medida = _normalize_product_unit(value)

    def change_estoque_minimo(self, value: str):
        self.estoque_minimo = value

    async def _report_partial_status_failure(self, token: str, reason: str):
        try:
            remote_product = await auth_client.get_product(token, self.product_id)
            self.original_product = {
                key: str(value) if value is not None else ""
                for key, value in remote_product.items()
            }
            self.original_product_status = str(remote_product.get("status") or "")
            self.original_product["status"] = self.original_product_status
            status_note = (
                f"O Xano já está com o status escolhido ({self.current_product_status})."
                if self.original_product_status == self.current_product_status
                else "O status escolhido continua pendente; revise e salve novamente."
            )
            self.error_message = (
                "Os dados cadastrais foram salvos, mas a alteração de status falhou: "
                f"{reason} Status confirmado no Xano: {self.original_product_status}. "
                f"{status_note}"
            )
        except Exception:
            self.error_message = (
                "Os dados cadastrais podem ter sido salvos, mas a alteração de status falhou "
                "e não foi possível recarregar o produto. Os valores escolhidos foram mantidos; "
                "confira o estado no Xano antes de tentar novamente."
            )

    def _clear_edit_product_data(self):
        self.has_loaded_product = False
        self.edit_load_failed = False
        self.can_retry_edit_load = False
        self.category_error_message = ""
        self.supplier_error_message = ""
        self.product_id = 0
        self.original_product = {}
        self.codigo = ""
        self.nome = ""
        self.descricao = ""
        self.unidade_medida = ""
        self.estoque_minimo = ""
        self.original_product_status = ""
        self.current_product_status = ""
        self.category_options = []
        self.category_selection = ""
        self.category_search_query = ""
        self.category_has_more = False
        self.supplier_options = []
        self.supplier_selection = "none"
        self.supplier_search_query = "Sem fornecedor padrão"
        self.supplier_has_more = False

    async def _session(self):
        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        self.can_read_products = auth_state.has_permission("product.read")
        self.can_read_categories = auth_state.has_permission("category.read")
        self.can_read_suppliers = auth_state.has_permission("supplier.read")
        self.can_create_products = auth_state.has_permission("product.create")
        self.can_update_products = auth_state.has_permission("product.update")
        self.can_activate_products = self.can_update_products
        self.can_inactivate_products = auth_state.has_permission("product.inactivate")
        return token, auth_state.is_authenticated

    @staticmethod
    def _category_option(item: dict[str, Any], *, disabled: bool = False) -> dict[str, str]:
        category_id = str(item.get("id", ""))
        label = str(item.get("nome") or f"Categoria (ID {category_id})")
        if disabled:
            label = f"{label} (inativa — vínculo atual)"
        return {"id": category_id, "label": label, "disabled": "true" if disabled else "false"}

    @staticmethod
    def _supplier_option(
        item: dict[str, Any], *, current: bool = False
    ) -> dict[str, str]:
        supplier_id = str(item.get("id", ""))
        label = str(item.get("nome_razao_social") or f"Fornecedor (ID {supplier_id})")
        is_active = item.get("status") == "ativo"
        if not is_active:
            state_label = "inativo — vínculo atual" if current else "inativo"
            label = f"{label} ({state_label})"
        return {
            "id": supplier_id,
            "label": label,
            "disabled": "false" if is_active else "true",
            "status": "ativo" if is_active else "inativo",
        }

    async def _load_categories(self, token: str, current_category_id: int | None = None):
        response = await _cached_reference_call(
            "categories",
            token,
            {"page": 1, "per_page": 100, "status": "ativo"},
            lambda: auth_client.list_categories(
                token, page=1, per_page=100, status="ativo"
            ),
            cache_allowed=self.can_read_categories,
            cache_fields=("id", "nome", "status"),
        )
        items = [item for item in response["items"] if isinstance(item, dict) and item.get("id") is not None]
        self.category_options = [self._category_option(item) for item in items]
        self.category_page = 1
        self.category_has_more = len(response["items"]) == 100
        if current_category_id is not None and not any(
            option["id"] == str(current_category_id) for option in self.category_options
        ):
            try:
                current = await _cached_reference_call(
                    "category_by_id",
                    token,
                    {"category_id": current_category_id},
                    lambda: auth_client.get_category(token, current_category_id),
                    cache_allowed=self.can_read_categories,
                    cache_fields=("id", "nome", "status"),
                )
                self.category_options.append(
                    self._category_option(current, disabled=current.get("status") != "ativo")
                )
            except XanoRequestError as exc:
                if exc.error_code != "NOT_FOUND":
                    raise
                self.category_options.append({
                    "id": str(current_category_id),
                    "label": f"Categoria atual indisponível (ID {current_category_id})",
                    "disabled": "true",
                })
        return self.category_options

    async def _load_suppliers(self, token: str, current_supplier_id: int | None = None):
        response = await _cached_reference_call(
            "suppliers",
            token,
            {"page": 1, "per_page": 100, "status": "ativo"},
            lambda: auth_client.list_suppliers(
                token, page=1, per_page=100, status="ativo"
            ),
            cache_allowed=self.can_read_suppliers,
            cache_fields=("id", "nome_razao_social", "status"),
        )
        items = [
            item for item in response["items"]
            if isinstance(item, dict)
            and item.get("id") is not None
            and item.get("status") == "ativo"
        ]
        self.supplier_options = [
            {"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"},
            *(self._supplier_option(item) for item in items),
        ]
        self.supplier_page = 1
        self.supplier_has_more = len(response["items"]) == 100
        if current_supplier_id == 0:
            self.supplier_options.append({
                "id": "0",
                "label": "Fornecedor padrão inválido (ID 0)",
                "disabled": "true",
                "status": "inativo",
            })
        elif current_supplier_id is not None and current_supplier_id > 0 and not any(
            option["id"] == str(current_supplier_id) for option in self.supplier_options
        ):
            try:
                current = await _cached_reference_call(
                    "supplier_by_id",
                    token,
                    {"supplier_id": current_supplier_id},
                    lambda: auth_client.get_supplier(token, current_supplier_id),
                    cache_allowed=self.can_read_suppliers,
                    cache_fields=("id", "nome_razao_social", "status"),
                )
                self.supplier_options.append(
                    self._supplier_option(current, current=True)
                )
            except XanoRequestError as exc:
                if exc.error_code != "NOT_FOUND":
                    raise
                self.supplier_options.append({
                    "id": str(current_supplier_id),
                    "label": f"Fornecedor atual indisponível (ID {current_supplier_id})",
                    "disabled": "true",
                })
        return self.supplier_options

    async def load_more_categories(self):
        if self.category_loading_more or not self.category_has_more:
            return
        token, authenticated = await self._session()
        if not token or not authenticated:
            return
        self.category_loading_more = True
        try:
            page = self.category_page + 1
            response = await _cached_reference_call(
                "categories",
                token,
                {"page": page, "per_page": 100, "status": "ativo"},
                lambda: auth_client.list_categories(
                    token, page=page, per_page=100, status="ativo"
                ),
                cache_allowed=self.can_read_categories,
                cache_fields=("id", "nome", "status"),
            )
            known = {option["id"] for option in self.category_options}
            new_items = [
                self._category_option(item) for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None and str(item["id"]) not in known
            ]
            self.category_options.extend(new_items)
            self.category_page = page
            self.category_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.category_error_message = exc.message
        finally:
            self.category_loading_more = False

    async def load_more_suppliers(self):
        if self.supplier_loading_more or not self.supplier_has_more:
            return
        token, authenticated = await self._session()
        if not token or not authenticated:
            return
        self.supplier_loading_more = True
        try:
            page = self.supplier_page + 1
            response = await _cached_reference_call(
                "suppliers",
                token,
                {"page": page, "per_page": 100, "status": "ativo"},
                lambda: auth_client.list_suppliers(
                    token, page=page, per_page=100, status="ativo"
                ),
                cache_allowed=self.can_read_suppliers,
                cache_fields=("id", "nome_razao_social", "status"),
            )
            known = {option["id"] for option in self.supplier_options}
            new_items = [
                self._supplier_option(item) for item in response["items"]
                if isinstance(item, dict)
                and item.get("id") is not None
                and item.get("status") == "ativo"
                and str(item["id"]) not in known
            ]
            self.supplier_options.extend(new_items)
            self.supplier_page = page
            self.supplier_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.supplier_error_message = exc.message
        finally:
            self.supplier_loading_more = False

    async def load_products(self):
        async for event in self._load_products(force_refresh=False):
            yield event

    async def refresh_products(self):
        async for event in self._load_products(force_refresh=True):
            yield event

    async def _load_products(self, *, force_refresh: bool):
        if self.is_loading:
            return
        self.is_loading = True
        self.can_read_products = False
        self.can_create_products = False
        self.can_update_products = False
        self.error_message = ""
        self.products_status_message = ""
        yield
        token, is_authenticated = await self._session()
        if not token or not is_authenticated:
            self.products = []
            self.has_products = False
            self.products_stale = False
            self.products_session_fingerprint = ""
            self.is_loading = False
            return

        fingerprint = _session_fingerprint(token)
        if self.__dict__.get("products_session_fingerprint", "") != fingerprint:
            self.products = []
            self.has_products = False
            self.products_stale = False
            self.products_session_fingerprint = fingerprint
        if not self.can_read_products:
            self.products = []
            self.has_products = False
            self.products_stale = False
            self.products_status_message = ""
            self.error_message = "Voc\u00ea n\u00e3o tem permiss\u00e3o para consultar produtos."
            self.is_loading = False
            return

        cache_key = _products_listing_key(token)
        cached, cache_is_fresh = _cache_get(
            cache_key, PRODUCTS_CACHE_TTL_SECONDS, allow_stale=True
        )
        cached_products = (
            cached.get("items", []) if isinstance(cached, dict) else []
        )
        stale_fallback = (
            cached_products if cached is not _CACHE_MISS and isinstance(cached, dict) else None
        )
        if cache_is_fresh and not force_refresh:
            self.products = cached_products
            self.has_products = bool(cached_products)
            self.products_stale = False
            self.products_status_message = ""
            self.is_loading = False
            return

        try:
            response = await auth_client.list_products(token, page=1, per_page=100)
            stock_items = []
            stock_page = 1
            while True:
                stock_response = await auth_client.list_stock(
                    token, page=stock_page, per_page=100
                )
                page_items = stock_response["items"]
                stock_items.extend(page_items)
                if len(page_items) < 100:
                    break
                stock_page += 1

            stock_by_product = {
                str(stock["product_id"]): stock
                for stock in stock_items
                if isinstance(stock, dict) and stock.get("product_id") is not None
            }
            products = [
                _map_product_to_list_item(item, stock_by_product)
                for item in response["items"]
                if isinstance(item, dict)
            ]
            self.products = products
            self.has_products = bool(products)
            self.products_stale = False
            self.products_status_message = ""
            records = [
                {field: item[field] for field in _EDIT_PRODUCT_FIELDS if field in item}
                for item in response["items"]
                if isinstance(item, dict)
            ]
            _cache_set(cache_key, {"items": products, "records": records})
        except XanoAuthError as exc:
            self.products = []
            self.has_products = False
            self.products_stale = False
            self.products_status_message = ""
            self.products_session_fingerprint = ""
            self.error_message = exc.message
            yield rx.redirect("/")
        except (XanoPermissionError, XanoConnectionError, XanoServerError, XanoRequestError) as exc:
            if isinstance(exc, XanoPermissionError) or getattr(exc, "status_code", None) in {401, 403}:
                # Uma resposta de autoriza??o invalida a listagem privada em cache.
                self.products = []
                self.has_products = False
                self.products_stale = False
                self.products_status_message = ""
                self.products_session_fingerprint = ""
                self.error_message = exc.message
            else:
                if not self.products and stale_fallback is not None:
                    self.products = stale_fallback
                    self.has_products = bool(stale_fallback)
                if self.has_products:
                    self.products_stale = True
                    self.products_status_message = (
                        "A listagem exibida pode estar desatualizada. "
                        f"N\u00e3o foi poss\u00edvel atualiz\u00e1-la: {exc.message}"
                    )
                    self.error_message = ""
                else:
                    self.products_stale = False
                    self.error_message = exc.message
        except Exception:
            if not self.products and stale_fallback is not None:
                self.products = stale_fallback
                self.has_products = bool(stale_fallback)
            if self.has_products:
                self.products_stale = True
                self.products_status_message = (
                    "A listagem exibida pode estar desatualizada. "
                    "N\u00e3o foi poss\u00edvel atualiz\u00e1-la; tente novamente manualmente."
                )
                self.error_message = ""
            else:
                self.products_stale = False
                self.error_message = "N\u00e3o foi poss\u00edvel carregar os produtos. Tente novamente."
        finally:
            self.is_loading = False

    async def load_create_form(self):
        self.is_loading = True
        self.error_message = ""
        self.category_error_message = ""
        self.supplier_error_message = ""
        self.success_message = ""
        self.can_create_products = False
        yield
        token, is_authenticated = await self._session()
        if not token or not is_authenticated or not self.can_create_products:
            self.is_loading = False
            self.error_message = "Você não tem permissão para criar produtos."
            return
        try:
            await self._load_categories(token)
        except (XanoError, XanoRequestError) as exc:
            self.category_error_message = exc.message
        try:
            await self._load_suppliers(token)
        except (XanoError, XanoRequestError) as exc:
            self.supplier_options = [
                {"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"}
            ]
            self.supplier_error_message = exc.message
        self.codigo = ""
        self.nome = ""
        self.descricao = ""
        self.category_selection = ""
        self.category_search_query = ""
        self.category_dropdown_open = False
        self.supplier_selection = "none"
        self.supplier_search_query = "Sem fornecedor padrão"
        self.supplier_dropdown_open = False
        self.unidade_medida = ""
        self.estoque_minimo = ""
        self.is_loading = False

    async def create_product(self):
        self.error_message = ""
        self.success_message = ""
        token, is_authenticated = await self._session()
        if not token or not is_authenticated:
            self.error_message = "Sua sessão não está ativa. Faça login novamente."
            return
        if not self.can_create_products:
            self.error_message = "Você não tem permissão para criar produtos."
            return
        category_id = _selected_category_id(self.category_selection)
        minimum = _parse_minimum(self.estoque_minimo)
        if not self.codigo.strip() or not self.nome.strip() or category_id is None or self.unidade_medida not in PRODUCT_UNIT_CODES or minimum is None:
            self.error_message = "Preencha código, nome, categoria, unidade de medida e estoque mínimo válido (maior ou igual a zero)."
            return
        available_supplier_ids = {
            option["id"]
            for option in self.supplier_options
            if option.get("id") != "none"
            and option.get("disabled") == "false"
            and option.get("status") == "ativo"
        }
        if self.supplier_selection != "none" and self.supplier_selection not in available_supplier_ids:
            self.error_message = "Selecione um fornecedor disponível ou Sem fornecedor padrão."
            return

        payload = {
            "codigo": self.codigo,
            "nome": self.nome,
            "categoria_id": category_id,
            "unidade_medida": _normalize_product_unit(self.unidade_medida),
            "estoque_minimo": minimum,
        }
        if self.supplier_selection != "none":
            payload["fornecedor_padrao_id"] = int(self.supplier_selection)
        if self.descricao:
            payload["descricao"] = self.descricao

        self.is_saving = True
        yield
        try:
            if self.supplier_selection != "none" and not await self._validate_active_supplier(
                token, int(self.supplier_selection)
            ):
                return
            await auth_client.create_product(token, payload)
            _invalidate_products_cache(token)
            yield rx.redirect("/produtos")
        except XanoRequestError as exc:
            if exc.error_code == "DUPLICATE_VALUE":
                self.error_message = (
                    f"Já existe um produto cadastrado com o código {self.codigo}. Informe outro código."
                )
            elif exc.error_code == "BUSINESS_RULE_VIOLATION":
                self.error_message = (
                    "A Categoria ou o Fornecedor padrão selecionado não foi aceito. "
                    "Revise as associações informadas."
                )
            elif exc.error_code in {
                "INVALID_INPUT", "INPUT_ERROR", "INPUTERROR", "VALIDATION_ERROR"
            }:
                self.error_message = (
                    "Revise os campos obrigatórios e informe um estoque mínimo maior ou igual a zero."
                )
            else:
                self.error_message = (
                    "Não foi possível salvar o produto. Verifique os dados e tente novamente."
                )
        except XanoError as exc:
            self.error_message = exc.message
        except Exception:
            self.error_message = "Não foi possível salvar o produto. Tente novamente."
        finally:
            self.is_saving = False

    async def load_edit_form(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.can_update_products = False
        self.can_retry_edit_load = False
        self.error_message = ""
        self.category_error_message = ""
        self.supplier_error_message = ""
        self.success_message = ""
        yield
        token, is_authenticated = await self._session()
        if not token or not is_authenticated or not self.can_update_products:
            self._clear_edit_product_data()
            self.is_loading = False
            self.error_message = "Você não tem permissão para editar produtos."
            return
        route_parts = str(self.router.url.path).strip("/").split("/")
        if len(route_parts) != 3 or route_parts[0] != "produtos" or route_parts[2] != "editar":
            self._clear_edit_product_data()
            self.is_loading = False
            self.error_message = "A rota do produto é inválida."
            return
        try:
            product_id = int(route_parts[1])
        except ValueError:
            self._clear_edit_product_data()
            self.is_loading = False
            self.error_message = "O identificador do produto é inválido."
            return

        if not self.has_loaded_product or self.product_id != product_id:
            self._clear_edit_product_data()
            self.category_error_message = ""
            self.supplier_error_message = ""

        try:
            # O GET /products autorizado nos ?ltimos 30s j? traz os campos da
            # linha de Produto. Reaproveite esse registro somente se product.read
            # continua presente; caso contr?rio, deixe o endpoint aplicar o grant.
            product = (
                _cached_product_detail(token, product_id)
                if self.can_read_products
                else None
            )
            if product is None:
                product = await auth_client.get_product(token, product_id)
            self.product_id = int(product["id"])
            self.original_product = {key: str(value) if value is not None else "" for key, value in product.items()}
            self.codigo = str(product.get("codigo") or "")
            self.nome = str(product.get("nome") or "")
            self.descricao = str(product.get("descricao") or "")
            self.unidade_medida = _normalize_product_unit(product.get("unidade_medida"))
            self.estoque_minimo = str(product.get("estoque_minimo") if product.get("estoque_minimo") is not None else "")
            current_supplier_value = product.get("fornecedor_padrao_id")
            current_supplier_id = (
                int(current_supplier_value) if current_supplier_value is not None else None
            )
            self.supplier_selection = (
                str(current_supplier_id) if current_supplier_id is not None else "none"
            )
            self.original_product_status = str(product.get("status") or "")
            self.current_product_status = self.original_product_status
            current_category_id = int(product["categoria_id"])
            self.has_loaded_product = True
            self.edit_load_failed = False
            previous_category_options = list(self.category_options)
            category_rate_limited = False
            try:
                await self._load_categories(token, current_category_id)
                self.category_error_message = ""
            except (XanoError, XanoRequestError) as exc:
                self.category_error_message = exc.message
                category_rate_limited = getattr(exc, "status_code", None) == 429
                self.can_retry_edit_load = (
                    self.can_retry_edit_load or _is_temporary_xano_failure(exc)
                )
                if previous_category_options:
                    self.category_options = previous_category_options
                elif not self.category_options:
                    self.category_options = [{
                        "id": str(current_category_id),
                        "label": f"Categoria atual (ID {current_category_id})",
                        "disabled": "true",
                    }]
                    self.category_has_more = False
            if category_rate_limited:
                # Não provoque outra falha durante o cooldown e mantenha o único
                # aviso de limite visível para esta tentativa de carregamento.
                self.supplier_error_message = ""
            else:
                previous_supplier_options = list(self.supplier_options)
                try:
                    await self._load_suppliers(token, current_supplier_id)
                    self.supplier_error_message = ""
                except (XanoError, XanoRequestError) as exc:
                    self.supplier_error_message = exc.message
                    self.can_retry_edit_load = (
                        self.can_retry_edit_load or _is_temporary_xano_failure(exc)
                    )
                    if previous_supplier_options:
                        self.supplier_options = previous_supplier_options
                    elif not self.supplier_options:
                        self.supplier_options = [
                            {"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"}
                        ]
                        if current_supplier_id is not None:
                            self.supplier_options.append({
                                "id": str(current_supplier_id),
                                "label": (
                                    "Fornecedor padrão inválido (ID 0)"
                                    if current_supplier_id == 0
                                    else f"Fornecedor atual (ID {current_supplier_id})"
                                ),
                                "disabled": "true",
                            })
                        self.supplier_has_more = False
            current_category = next(
                (option for option in self.category_options if option["id"] == str(current_category_id)),
                None,
            )
            self.category_selection = str(current_category_id)
            self.category_search_query = (
                current_category["label"] if current_category else f"Categoria atual (ID {current_category_id})"
            )
            current_supplier = next(
                (option for option in self.supplier_options if option["id"] == str(current_supplier_id)),
                None,
            ) if current_supplier_id is not None else None
            self.supplier_search_query = (
                current_supplier["label"] if current_supplier else "Sem fornecedor padrão"
            )
            self.category_dropdown_open = False
            self.supplier_dropdown_open = False
        except (XanoError, XanoRequestError) as exc:
            self.error_message = exc.message
            self.edit_load_failed = True
            self.can_retry_edit_load = _is_temporary_xano_failure(exc)
            if getattr(exc, "status_code", None) in {401, 403}:
                self._clear_edit_product_data()
                self.can_update_products = False
        except (KeyError, TypeError, ValueError):
            self.error_message = "O Xano retornou dados de produto em formato inesperado."
            self.edit_load_failed = True
        except Exception:
            self.error_message = "Não foi possível carregar o produto. Tente novamente."
            self.edit_load_failed = True
        finally:
            self.is_loading = False

    async def update_product(self):
        self.error_message = ""
        self.success_message = ""
        token, is_authenticated = await self._session()
        if not token or not is_authenticated or not self.has_loaded_product:
            self.error_message = "Sua sessão não está ativa. Faça login novamente."
            return
        if not self.can_update_products:
            self.error_message = "Você não tem permissão para editar produtos."
            return
        if (
            self.is_loading
            or self.edit_load_failed
            or self.category_error_message
            or self.supplier_error_message
        ):
            self.error_message = (
                "Não foi possível confirmar os dados do produto e suas opções. "
                "Tente carregar novamente antes de salvar."
            )
            return
        category_id = _selected_category_id(self.category_selection)
        minimum = _parse_minimum(self.estoque_minimo)
        if not self.codigo.strip() or not self.nome.strip() or category_id is None or self.unidade_medida not in PRODUCT_UNIT_CODES or minimum is None:
            self.error_message = "Preencha código, nome, categoria, unidade de medida e estoque mínimo válido."
            return

        original = self.original_product
        payload: dict[str, object] = {}
        for field, value in (
            ("codigo", self.codigo),
            ("nome", self.nome),
            ("categoria_id", category_id),
            ("unidade_medida", _normalize_product_unit(self.unidade_medida)),
            ("estoque_minimo", minimum),
        ):
            if str(original.get(field, "")) != str(value):
                payload[field] = value

        original_supplier_id = str(original.get("fornecedor_padrao_id", "") or "")
        if self.supplier_selection == "none":
            if original_supplier_id:
                payload["limpar_fornecedor_padrao"] = True
        elif self.supplier_selection != original_supplier_id:
            available_supplier_ids = {
                option["id"]
                for option in self.supplier_options
                if option.get("id") != "none"
                and option.get("disabled") == "false"
                and option.get("status") == "ativo"
            }
            if self.supplier_selection not in available_supplier_ids:
                self.error_message = "Selecione um fornecedor disponível ou Sem fornecedor padrão."
                return
            payload["fornecedor_padrao_id"] = int(self.supplier_selection)
        try:
            if float(original.get("estoque_minimo", "")) == minimum:
                payload.pop("estoque_minimo", None)
        except (ValueError, TypeError):
            pass
        if self.descricao != str(original.get("descricao", "")):
            if self.descricao:
                payload["descricao"] = self.descricao
            else:
                payload["limpar_descricao"] = True
        status_changed = self.current_product_status != self.original_product_status
        if not payload and not status_changed:
            self.error_message = "Nenhuma alteração foi informada."
            return
        if status_changed:
            if self.original_product_status == "ativo" and self.current_product_status == "inativo":
                if not self.can_inactivate_products:
                    self.error_message = "Você não tem permissão para inativar produtos."
                    return
            elif self.original_product_status == "inativo" and self.current_product_status == "ativo":
                if not self.can_activate_products:
                    self.error_message = "Você não tem permissão para ativar produtos."
                    return
            else:
                self.error_message = "O status selecionado não é válido para este produto."
                return

        self.is_saving = True
        yield
        fields_update_completed = False
        try:
            if "fornecedor_padrao_id" in payload and not await self._validate_active_supplier(
                token, int(payload["fornecedor_padrao_id"])
            ):
                return
            if payload:
                patch_result = await auth_client.update_product(token, self.product_id, payload)
                fields_update_completed = True
                record_fields = {
                    field: patch_result[field]
                    for field in _EDIT_PRODUCT_FIELDS
                    if isinstance(patch_result, dict) and field in patch_result
                }
                for field in (
                    "codigo",
                    "nome",
                    "categoria_id",
                    "unidade_medida",
                    "estoque_minimo",
                    "fornecedor_padrao_id",
                    "descricao",
                ):
                    if field in payload and field not in record_fields:
                        record_fields[field] = payload[field]
                if payload.get("limpar_fornecedor_padrao") is True:
                    record_fields["fornecedor_padrao_id"] = None
                if payload.get("limpar_descricao") is True:
                    record_fields["descricao"] = None

                cached_fields: dict[str, Any] = {}
                for field in ("codigo", "nome", "unidade_medida", "estoque_minimo"):
                    if field in record_fields:
                        cached_fields[field] = record_fields[field]
                if "categoria_id" in record_fields:
                    selected_category = next(
                        (
                            option
                            for option in self.category_options
                            if option.get("id") == str(record_fields["categoria_id"])
                        ),
                        None,
                    )
                    cached_fields["categoria"] = (
                        selected_category.get("label")
                        if selected_category
                        else "Categoria n\u00e3o encontrada"
                    )
                _update_cached_product(
                    token, self.product_id, cached_fields, record_fields
                )

            if status_changed:
                if self.original_product_status == "ativo" and self.current_product_status == "inativo":
                    status_response = await auth_client.inactivate_product(token, self.product_id)
                elif self.original_product_status == "inativo" and self.current_product_status == "ativo":
                    status_response = await auth_client.activate_product(token, self.product_id)
                else:
                    self.error_message = "O status selecionado não é válido para este produto."
                    return
                status_value = (
                    status_response.get("status", self.current_product_status)
                    if isinstance(status_response, dict)
                    else self.current_product_status
                )
                self.original_product_status = str(status_value)
                self.original_product["status"] = self.original_product_status
                _update_cached_product(
                    token,
                    self.product_id,
                    {"status": self.original_product_status},
                    {"status": self.original_product_status},
                )

            yield rx.redirect("/produtos")
        except (XanoError, XanoRequestError) as exc:
            if fields_update_completed and status_changed:
                await self._report_partial_status_failure(token, exc.message)
            else:
                self.error_message = exc.message
        except Exception:
            if fields_update_completed and status_changed:
                await self._report_partial_status_failure(
                    token, "não foi possível confirmar a resposta do endpoint."
                )
            else:
                self.error_message = "Não foi possível atualizar o produto. Tente novamente."
        finally:
            self.is_saving = False

    async def change_product_status(self):
        self.error_message = ""
        self.success_message = ""
        token, is_authenticated = await self._session()
        if not token or not is_authenticated:
            self.error_message = "Sua sessão não está ativa. Faça login novamente."
            return
        if not self.has_loaded_product:
            self.error_message = "Carregue um produto antes de alterar o status."
            return
        if (
            self.is_loading
            or self.edit_load_failed
            or self.category_error_message
            or self.supplier_error_message
        ):
            self.error_message = "Carregue novamente os dados do produto antes de alterar o status."
            return
        if self.current_product_status == "ativo":
            if self.original_product_status == "ativo" and not self.can_inactivate_products:
                self.error_message = "Você não tem permissão para inativar produtos."
                return
            self.current_product_status = "inativo"
        elif self.current_product_status == "inativo":
            if self.original_product_status == "inativo" and not self.can_activate_products:
                self.error_message = "Você não tem permissão para ativar produtos."
                return
            self.current_product_status = "ativo"
        else:
            self.error_message = "O status atual do produto não é válido."


def _selected_category_id(selection: str) -> int | None:
    try:
        return int(selection.split(" · ", 1)[0].strip())
    except (ValueError, AttributeError):
        return None


def _parse_minimum(value: str) -> float | None:
    try:
        number = float(value.strip().replace(",", "."))
        return number if math.isfinite(number) and number >= 0 else None
    except (ValueError, AttributeError):
        return None


PRODUCT_GRID = "1fr 1.8fr 1.5fr 0.8fr 0.8fr 0.8fr 0.8fr"


def _product_row(product: dict[str, str]) -> rx.Component:
    edit_action = rx.cond(
        ProductsState.can_update_products,
        rx.link("Editar", href=f"/produtos/{product['id']}/editar"),
        rx.text("—"),
    )
    return rx.grid(
        rx.text(product["codigo"], padding_x="12px"),
        rx.text(product["nome"], padding_x="12px"),
        rx.text(product["categoria"], padding_x="12px"),
        rx.text(product["unidade_medida"], padding_x="12px", text_align="center"),
        rx.text(product["estoque_minimo"], padding_x="12px", text_align="center"),
        rx.text(product["status"], padding_x="12px", text_align="center"),
        rx.center(
            rx.cond(
                ProductsState.products_stale,
                rx.text("—"),
                edit_action,
            ),
            padding_x="12px",
        ),
        columns="7",
        width="100%",
        column_gap="4px",
        style={"grid_template_columns": PRODUCT_GRID, "align_items": "center"},
        padding="0.75rem",
        border_bottom=f"1px solid {BORDER_SOFT}",
    )


def _products_table() -> rx.Component:
    headers = ["Código", "Nome", "Categoria", "Unidade", "Mínimo", "Status", "Ações"]
    header = rx.grid(
        rx.text(headers[0], weight="bold", padding_x="12px"),
        rx.text(headers[1], weight="bold", padding_x="12px"),
        rx.text(headers[2], weight="bold", padding_x="12px"),
        rx.text(headers[3], weight="bold", padding_x="12px", text_align="center"),
        rx.text(headers[4], weight="bold", padding_x="12px", text_align="center"),
        rx.text(headers[5], weight="bold", padding_x="12px", text_align="center"),
        rx.text(headers[6], weight="bold", padding_x="12px", text_align="center"),
        columns="7",
        width="100%",
        column_gap="4px",
        style={"grid_template_columns": PRODUCT_GRID, "align_items": "center"},
        padding="0.75rem",
        background=TABLE_HEADER,
        border_bottom=f"1px solid {BORDER}",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(ProductsState.filtered_products, _product_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border=f"1px solid {BORDER}",
        border_radius="0.4rem",
    )


def _form_fields() -> rx.Component:
    return rx.vstack(
        rx.vstack(rx.text("Código"), rx.input(value=ProductsState.codigo, on_change=ProductsState.change_codigo, placeholder="Código"), width="100%", align="stretch", spacing="1"),
        rx.vstack(rx.text("Nome"), rx.input(value=ProductsState.nome, on_change=ProductsState.change_nome, placeholder="Nome"), width="100%", align="stretch", spacing="1"),
        rx.vstack(rx.text("Descrição"), rx.text_area(value=ProductsState.descricao, on_change=ProductsState.change_descricao, placeholder="Descrição (opcional)"), width="100%", align="stretch", spacing="1"),
        rx.vstack(
            rx.text("Categoria"),
            searchable_select(
                query=ProductsState.category_search_query,
                options=ProductsState.filtered_category_options,
                is_open=ProductsState.category_dropdown_open,
                on_search=ProductsState.search_categories,
                on_open=ProductsState.open_category_options,
                on_close=ProductsState.close_category_options,
                on_escape=ProductsState.close_category_options_on_escape,
                on_select=ProductsState.select_category,
                has_more=ProductsState.category_has_more,
                is_loading_more=ProductsState.category_loading_more,
                on_load_more=ProductsState.load_more_categories,
                placeholder="Buscar categoria...",
            ),
            width="100%", align="stretch", spacing="1",
        ),
        rx.vstack(
            rx.text("Fornecedor padrão"),
            searchable_select(
                query=ProductsState.supplier_search_query,
                options=ProductsState.filtered_supplier_options,
                is_open=ProductsState.supplier_dropdown_open,
                on_search=ProductsState.search_suppliers,
                on_open=ProductsState.open_supplier_options,
                on_close=ProductsState.close_supplier_options,
                on_escape=ProductsState.close_supplier_options_on_escape,
                on_select=ProductsState.select_supplier,
                has_more=ProductsState.supplier_has_more,
                is_loading_more=ProductsState.supplier_loading_more,
                on_load_more=ProductsState.load_more_suppliers,
                placeholder="Buscar fornecedor...",
            ),
            width="100%", align="stretch", spacing="1",
        ),
        rx.vstack(
            rx.text("Unidade de medida"),
            rx.select.root(
                rx.select.trigger(placeholder="Selecione uma unidade"),
                rx.select.content(
                    rx.select.group(
                        *[
                            rx.select.item(f"{code} - {label}", value=code)
                            for code, label in PRODUCT_UNITS
                        ]
                    )
                ),
                value=ProductsState.unidade_medida,
                on_change=ProductsState.change_unidade_medida,
            ),
            width="100%",
            align="stretch",
            spacing="1",
        ),
        rx.vstack(rx.text("Estoque mínimo"), rx.input(value=ProductsState.estoque_minimo, on_change=ProductsState.change_estoque_minimo, placeholder="0", type="number", step="0.01"), width="100%", align="stretch", spacing="1"),
        width="100%",
        align="stretch",
        spacing="3",
    )


def _feedback() -> rx.Component:
    return rx.vstack(
        rx.cond(ProductsState.error_message != "", rx.text(ProductsState.error_message, color=ERROR_TEXT)),
        rx.cond(ProductsState.category_error_message != "", rx.text(ProductsState.category_error_message, color=ERROR_TEXT)),
        rx.cond(ProductsState.supplier_error_message != "", rx.text(ProductsState.supplier_error_message, color=ERROR_TEXT)),
        rx.cond(ProductsState.success_message != "", rx.text(ProductsState.success_message, color=SUCCESS_TEXT)),
        width="100%",
        align="stretch",
        spacing="2",
    )


def produtos() -> rx.Component:
    return page(
        "Produtos",
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon(tag="search", size=18, color=TEXT_MUTED),
                    rx.input(
                        value=ProductsState.search_query,
                        on_change=ProductsState.change_search_query,
                        placeholder="Buscar por c\u00f3digo, nome ou categoria...",
                        width="100%",
                        border="none",
                        outline="none",
                        box_shadow="none",
                        padding="0",
                        background="transparent",
                    ),
                    align="center",
                    spacing="3",
                    width="430px",
                    max_width="100%",
                    flex_shrink="1",
                    height="40px",
                    padding_x="12px",
                    border=f"1px solid {BORDER_SOFT}",
                    border_radius="8px",
                    background=SURFACE,
                ),
                rx.spacer(),
                rx.cond(
                    ProductsState.can_create_products,
                    rx.link(rx.button("Novo produto"), href="/produtos/novo"),
                    rx.fragment(),
                ),
                width="100%",
            ),
            section(
                "Produtos cadastrados",
                rx.cond(
                    ProductsState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando produtos..."), spacing="3", padding="2rem"),
                    rx.vstack(
                        rx.cond(
                            ProductsState.products_stale,
                            rx.hstack(
                                rx.text(ProductsState.products_status_message, color=WARNING_TEXT),
                                rx.button(
                                    "Tentar atualizar",
                                    on_click=ProductsState.refresh_products,
                                    disabled=ProductsState.is_loading,
                                    variant="ghost",
                                    size="1",
                                    style={"padding": "0 8px", "height": "26px"},
                                ),
                                align="center",
                                spacing="2",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            ProductsState.has_products,
                            rx.cond(
                                ProductsState.has_filtered_products,
                                _products_table(),
                                rx.text("Nenhum produto encontrado."),
                            ),
                            rx.cond(
                                ProductsState.error_message != "",
                                rx.vstack(
                                    _feedback(),
                                    rx.button(
                                        "Tentar novamente",
                                        on_click=ProductsState.refresh_products,
                                        disabled=ProductsState.is_loading,
                                        variant="ghost",
                                        size="1",
                                        style={"padding": "0 8px", "height": "26px"},
                                    ),
                                    align="start",
                                    spacing="2",
                                ),
                                rx.text("Nenhum produto cadastrado."),
                            ),
                        ),
                        width="100%",
                        align="stretch",
                        spacing="3",
                    ),
                ),
                tone="mint",
            ),
        ),
    )


def _product_form(is_edit: bool) -> rx.Component:
    edit_save_blocked = rx.cond(
        is_edit,
        ProductsState.is_loading
        | ProductsState.edit_load_failed
        | (ProductsState.category_error_message != "")
        | (ProductsState.supplier_error_message != ""),
        False,
    )
    save_button = rx.button(
        rx.cond(
            ProductsState.is_saving,
            "Salvando...",
            "Salvar alterações" if is_edit else "Salvar produto",
        ),
        on_click=ProductsState.update_product if is_edit else ProductsState.create_product,
        loading=ProductsState.is_saving,
        disabled=ProductsState.is_saving | edit_save_blocked,
    )
    form_fields = rx.vstack(
        _form_fields(),
        rx.hstack(
            rx.link(rx.button("Cancelar"), href="/produtos"),
            save_button,
            spacing="3",
        ),
        width="100%",
        align="stretch",
        spacing="4",
    )
    retry_button = rx.button(
        "Tentar novamente",
        on_click=ProductsState.load_edit_form,
        disabled=ProductsState.is_loading,
        variant="soft",
    )
    if is_edit:
        form_content = rx.vstack(
            _feedback(),
            rx.cond(ProductsState.has_loaded_product, form_fields, rx.fragment()),
            rx.cond(ProductsState.can_retry_edit_load, retry_button, rx.fragment()),
            width="100%",
            align="stretch",
            spacing="3",
        )
    else:
        form_content = rx.vstack(_feedback(), form_fields, width="100%", align="stretch", spacing="3")
    return rx.vstack(
        rx.cond(
            ProductsState.is_loading,
            rx.center(rx.spinner(), rx.text("Carregando produto..."), spacing="3", padding="2rem"),
            form_content,
        ),
        width="100%",
        align="stretch",
        spacing="3",
    )


def novo_produto() -> rx.Component:
    return page(
        "Novo produto",
        section("Dados do produto", _product_form(is_edit=False), tone="rose"),
    )


def _status_action() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(ProductsState.status_action_label, loading=ProductsState.is_status_loading, disabled=ProductsState.is_status_loading)
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title(ProductsState.status_action_label),
            rx.alert_dialog.description(
                rx.cond(
                    ProductsState.is_product_active,
                    "Confirma a inativação deste produto? O registro será mantido.",
                    "Confirma a ativação deste produto?",
                )
            ),
            rx.hstack(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft")),
                rx.alert_dialog.action(rx.button("Confirmar", on_click=ProductsState.change_product_status)),
                justify="end",
                spacing="3",
            ),
            max_width="450px",
        ),
    )


def editar_produto() -> rx.Component:
    return page(
        "Editar produto",
        section(
            "Dados do produto",
            rx.vstack(
                rx.cond(ProductsState.is_loading, rx.text("Carregando produto..."), rx.text(f"Status atual: {ProductsState.current_product_status}")),
                rx.cond(ProductsState.can_change_product_status, _status_action(), rx.text("")),
                _product_form(is_edit=True),
                width="100%",
                align="stretch",
                spacing="4",
            ),
            tone="rose",
        ),
    )
