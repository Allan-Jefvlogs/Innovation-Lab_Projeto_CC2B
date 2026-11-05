import reflex as rx
import math
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ..components.layout import mock_table, page, section
from ..components.searchable_select import normalize_search_text, searchable_select
from ..services.stock_alert import STATUS_ENVIADO, STATUS_FALHOU, enviar_alerta_estoque_minimo
from ..services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoError,
    XanoPermissionError,
    XanoRequestError,
    XanoServerError,
    auth_client,
)
from ..state import AuthState


logger = logging.getLogger(__name__)


def _log_history_failure(operation: str, exc: Exception) -> None:
    payload = getattr(exc, "payload", None)
    logger.exception(
        "Movement history request failed: operation=%s exception_type=%s status=%s error_code=%s payload_type=%s payload_keys=%s",
        operation,
        type(exc).__name__,
        getattr(exc, "status_code", None),
        getattr(exc, "error_code", None),
        type(payload).__name__ if payload is not None else None,
        sorted(payload.keys()) if isinstance(payload, dict) else None,
    )


class EntryState(rx.State):
    """Seleção, validação e envio de Entradas ao backend Xano."""

    products: list[dict[str, str]] = []
    product_query: str = ""
    product_id: str = ""
    product_code: str = ""
    product_name: str = ""
    product_default_supplier_id: str = ""
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False
    barcode_value: str = ""
    product_error: str = ""

    suppliers: list[dict[str, str]] = []
    supplier_query: str = ""
    supplier_id: str = ""
    supplier_options_open: bool = False
    supplier_page: int = 1
    supplier_has_more: bool = False
    supplier_loading_more: bool = False
    supplier_error: str = ""

    entry_date_time: str = ""
    quantidade: str = ""
    motivo: str = "Compra"
    observacao: str = ""
    is_loading: bool = False
    is_submitting: bool = False
    error_message: str = ""
    success_message: str = ""

    @rx.var
    def filtered_products(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.product_query)
        if not query:
            return self.products
        return [
            item for item in self.products
            if query in normalize_search_text(item.get("label", ""))
        ]

    @rx.var
    def filtered_suppliers(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.supplier_query)
        if not query:
            return self.suppliers
        return [
            item for item in self.suppliers
            if query in normalize_search_text(item.get("label", ""))
        ]

    def load_entry_page(self):
        return [AuthState.require_auth(), EntryState.load_entry_data()]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
        if not auth_state.is_authenticated or not auth_state.has_permission("stock.entry"):
            return ""
        return str(auth_state.auth_token or "").strip()

    @staticmethod
    def _product_option(item: dict) -> dict[str, str]:
        product_id = str(item.get("id", ""))
        code = str(item.get("codigo") or "")
        name = str(item.get("nome") or "")
        return {
            "id": product_id,
            "label": f"{code} - {name}".strip(" -"),
            "codigo": code,
            "nome": name,
            "fornecedor_padrao_id": str(item.get("fornecedor_padrao_id") or ""),
        }

    @staticmethod
    def _supplier_option(item: dict) -> dict[str, str]:
        supplier_id = str(item.get("id", ""))
        label = str(item.get("nome_razao_social") or f"Fornecedor (ID {supplier_id})")
        return {"id": supplier_id, "label": label, "disabled": "false"}

    async def load_entry_data(self):
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        self.product_error = ""
        self.supplier_error = ""
        self._clear_entry_fields()
        self.products = []
        self.suppliers = [{"id": "none", "label": "Sem fornecedor", "disabled": "false"}]
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            return
        try:
            products_response = await auth_client.list_products(token, page=1, per_page=100)
            self.products = [
                self._product_option(item)
                for item in products_response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            ]
            self.product_page = 1
            self.product_has_more = len(products_response["items"]) == 100

            suppliers_response = await auth_client.list_suppliers(
                token, page=1, per_page=100
            )
            self.suppliers.extend(
                self._supplier_option(item)
                for item in suppliers_response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            )
            self.supplier_page = 1
            self.supplier_has_more = len(suppliers_response["items"]) == 100
        except XanoAuthError as exc:
            self.error_message = exc.message
            yield rx.redirect("/")
        except (XanoPermissionError, XanoConnectionError, XanoServerError, XanoRequestError) as exc:
            self.error_message = exc.message
        except Exception:
            self.error_message = "Não foi possível carregar os dados para a entrada. Tente novamente."
        finally:
            self.is_loading = False

    def search_products(self, value: str):
        self.product_query = value
        self.barcode_value = ""
        self.product_id = ""
        self.product_code = ""
        self.product_name = ""
        self.product_default_supplier_id = ""
        self.product_query = ""
        self.product_options_open = False
        self.supplier_id = ""
        self.supplier_query = ""
        self.supplier_options_open = False
        self.product_error = ""
        self.product_options_open = True
        self.supplier_options_open = False

    def open_product_options(self):
        self.product_options_open = True
        self.supplier_options_open = False

    def close_product_options(self, value: str = ""):
        self.product_options_open = False

    def close_product_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.product_options_open = False

    def search_suppliers(self, value: str):
        self.supplier_query = value
        self.supplier_id = ""
        self.supplier_error = ""
        self.supplier_options_open = True
        self.product_options_open = False

    def open_supplier_options(self):
        self.supplier_options_open = True
        self.product_options_open = False

    def close_supplier_options(self, value: str = ""):
        self.supplier_options_open = False

    def close_supplier_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.supplier_options_open = False

    def change_barcode(self, value: str):
        self.barcode_value = value
        self.product_error = ""
        if normalize_search_text(value.strip()) != normalize_search_text(self.product_code):
            self.product_id = ""
            self.product_code = ""
            self.product_name = ""
            self.product_default_supplier_id = ""
            self.product_query = ""
            self.product_options_open = False
            self.supplier_id = ""
            self.supplier_query = ""
            self.supplier_options_open = False

    async def _apply_selected_product(self, product: dict[str, str], token: str):
        self.product_id = product["id"]
        self.product_code = product["codigo"]
        self.product_name = product["nome"]
        self.product_query = product["label"]
        self.barcode_value = product["codigo"]
        self.product_default_supplier_id = product.get("fornecedor_padrao_id", "")
        self.product_options_open = False
        self.supplier_options_open = False
        self.product_error = ""
        self.supplier_error = ""

        default_supplier_id = self.product_default_supplier_id
        if not default_supplier_id:
            self.supplier_id = ""
            self.supplier_query = "Sem fornecedor"
            return

        existing_supplier = next(
            (item for item in self.suppliers if item["id"] == default_supplier_id),
            None,
        )
        if existing_supplier is None:
            try:
                supplier = await auth_client.get_supplier(token, int(default_supplier_id))
                existing_supplier = self._supplier_option(supplier)
                self.suppliers.append(existing_supplier)
            except XanoError as exc:
                self.supplier_error = (
                    "Não foi possível carregar o fornecedor padrão do produto. "
                    "Você ainda pode escolher outro fornecedor."
                )
                self.supplier_id = ""
                self.supplier_query = ""
                return

        self.supplier_id = default_supplier_id
        self.supplier_query = existing_supplier["label"]

    async def select_product(self, product_id: str):
        product = next((item for item in self.products if item["id"] == product_id), None)
        if product is None:
            return
        token = await self._session_token()
        await self._apply_selected_product(product, token)
        self.barcode_value = product["codigo"]

    def select_supplier(self, supplier_id: str):
        if supplier_id == "none":
            self.supplier_id = ""
            self.supplier_query = "Sem fornecedor"
            self.supplier_error = ""
            self.supplier_options_open = False
            return
        supplier = next((item for item in self.suppliers if item["id"] == supplier_id), None)
        if supplier is None or supplier.get("disabled") == "true":
            return
        self.supplier_id = supplier_id
        self.supplier_query = supplier["label"]
        self.supplier_error = ""
        self.supplier_options_open = False

    async def on_barcode_key_down(self, key: str):
        if key == "Enter":
            await self.find_product_by_barcode()

    async def find_product_by_barcode(self):
        code = normalize_search_text(self.barcode_value.strip())
        if not code:
            self.product_error = "Informe ou leia o código do produto."
            return
        token = await self._session_token()
        if not token:
            self.product_error = "Sua sessão não está ativa. Faça login novamente."
            return

        product = next(
            (item for item in self.products if normalize_search_text(item["codigo"]) == code),
            None,
        )
        if product is not None:
            await self._apply_selected_product(product, token)
            return

        page_number = self.product_page + 1
        while self.product_has_more:
            try:
                response = await auth_client.list_products(token, page=page_number, per_page=100)
            except XanoAuthError as exc:
                self.product_error = exc.message
                return
            except XanoError as exc:
                self.product_error = exc.message
                return
            page_items = [
                self._product_option(item)
                for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            ]
            self.products.extend(
                item for item in page_items
                if not any(existing["id"] == item["id"] for existing in self.products)
            )
            self.product_page = page_number
            self.product_has_more = len(response["items"]) == 100
            product = next(
                (item for item in page_items if normalize_search_text(item["codigo"]) == code),
                None,
            )
            if product is not None:
                await self._apply_selected_product(product, token)
                return
            page_number += 1

        self.product_id = ""
        self.product_code = ""
        self.product_name = ""
        self.product_default_supplier_id = ""
        self.supplier_id = ""
        self.supplier_query = ""
        self.product_error = "Produto não encontrado."

    async def load_more_products(self):
        if self.product_loading_more or not self.product_has_more:
            return
        token = await self._session_token()
        self.product_loading_more = True
        try:
            page_number = self.product_page + 1
            response = await auth_client.list_products(token, page=page_number, per_page=100)
            known = {item["id"] for item in self.products}
            self.products.extend(
                self._product_option(item) for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None and str(item["id"]) not in known
            )
            self.product_page = page_number
            self.product_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.product_error = exc.message
        finally:
            self.product_loading_more = False

    async def load_more_suppliers(self):
        if self.supplier_loading_more or not self.supplier_has_more:
            return
        token = await self._session_token()
        self.supplier_loading_more = True
        try:
            page_number = self.supplier_page + 1
            response = await auth_client.list_suppliers(
                token, page=page_number, per_page=100
            )
            known = {item["id"] for item in self.suppliers}
            self.suppliers.extend(
                self._supplier_option(item) for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None and str(item["id"]) not in known
            )
            self.supplier_page = page_number
            self.supplier_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.supplier_error = exc.message
        finally:
            self.supplier_loading_more = False

    def change_entry_date_time(self, value: str):
        self.entry_date_time = value

    def change_quantity(self, value: str):
        self.quantidade = value

    def change_reason(self, value: str):
        self.motivo = value

    def change_observation(self, value: str):
        self.observacao = value

    def _clear_entry_fields(self):
        self.product_query = ""
        self.product_id = ""
        self.product_code = ""
        self.product_name = ""
        self.product_default_supplier_id = ""
        self.product_options_open = False
        self.barcode_value = ""
        self.supplier_id = ""
        self.supplier_query = ""
        self.supplier_options_open = False
        self.entry_date_time = ""
        self.quantidade = ""
        self.motivo = ""
        self.observacao = ""

    @staticmethod
    def _entry_error_message(error_code: str) -> str:
        messages = {
            "INVALID_INPUT": "Verifique os dados informados.",
            "PRODUCT_NOT_FOUND": "Produto não encontrado.",
            "PRODUCT_INACTIVE": "Não é possível registrar entrada para um produto inativo.",
            "SUPPLIER_NOT_FOUND": "Fornecedor não encontrado.",
            "SUPPLIER_INACTIVE": "O fornecedor selecionado está inativo.",
            "STOCK_BALANCE_NOT_FOUND": "Não foi encontrado saldo de estoque para este produto.",
            "PERMISSION_DENIED": "Você não possui permissão para registrar entradas de estoque.",
            "STOCK_UPDATE_FAILED": "Não foi possível atualizar o estoque. Tente novamente.",
            "STOCK_CONCURRENCY_CONFLICT": "Houve um conflito ao atualizar o estoque. Tente novamente.",
        }
        return messages.get(
            error_code,
            "Não foi possível registrar a entrada. Verifique os dados e tente novamente.",
        )

    async def register_entry(self):
        if self.is_submitting:
            return

        self.error_message = ""
        self.success_message = ""

        try:
            product_id = int(self.product_id)
        except (TypeError, ValueError):
            self.error_message = "Selecione ou leia um produto válido antes de registrar a entrada."
            return
        if product_id <= 0:
            self.error_message = "Selecione ou leia um produto válido antes de registrar a entrada."
            return

        try:
            quantity_decimal = Decimal(self.quantidade.strip().replace(",", "."))
            if not quantity_decimal.is_finite() or quantity_decimal <= 0:
                raise InvalidOperation
            quantity = float(quantity_decimal)
            if not math.isfinite(quantity):
                raise InvalidOperation
        except (InvalidOperation, ValueError, OverflowError):
            self.error_message = "Informe uma quantidade maior que zero."
            return

        reason = self.motivo.strip()
        if not reason:
            self.error_message = "Informe o motivo da entrada."
            return

        supplier_id = None
        if self.supplier_id not in ("", "none"):
            try:
                supplier_id = int(self.supplier_id)
            except (TypeError, ValueError):
                self.error_message = "Selecione um fornecedor válido ou deixe sem fornecedor."
                return
            if supplier_id <= 0:
                self.error_message = "Selecione um fornecedor válido ou deixe sem fornecedor."
                return

        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        if not auth_state.session_is_valid:
            if auth_state.session_validation in {"temporarily_unavailable", "forbidden", "validating"}:
                self.error_message = auth_state.session_status_message
                return
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
            return
        if not token or not auth_state.has_permission("stock.entry"):
            self.error_message = "Vocé não possui permissão para registrar entradas."
            return

        self.is_submitting = True
        yield
        try:
            result = await auth_client.create_stock_entry(
                token,
                product_id=product_id,
                quantidade=quantity,
                motivo=reason,
                supplier_id=supplier_id,
                data_hora=self.entry_date_time.strip() or None,
                observacao=self.observacao.strip() or None,
            )
            saldo_atual = result.get("saldo_atual")
            self.success_message = "Entrada registrada com sucesso."
            if saldo_atual is not None:
                self.success_message += f" Saldo atualizado: {saldo_atual}."
            self._clear_entry_fields()
            self.product_error = ""
            self.supplier_error = ""
        except XanoAuthError as exc:
            self.error_message = exc.message
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para registrar entradas de estoque."
        except XanoRequestError as exc:
            self.error_message = self._entry_error_message(exc.error_code)
        except XanoConnectionError:
            self.error_message = "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
        except (XanoServerError, XanoError):
            self.error_message = "Não foi possível registrar a entrada. Verifique os dados e tente novamente."
        except Exception:
            self.error_message = "Não foi possível registrar a entrada. Tente novamente."
        finally:
            self.is_submitting = False


class ExitState(rx.State):
    """Seleção, saldo, validação e envio independente de Saídas de estoque."""

    products: list[dict[str, str]] = []
    product_query: str = ""
    product_id: str = ""
    product_code: str = ""
    product_name: str = ""
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False
    barcode_value: str = ""
    product_error: str = ""
    stock_by_product: dict[str, dict[str, str]] = {}
    saldo_disponivel: str = ""
    stock_balance_found: bool = False
    has_available_stock: bool = False

    exit_date_time: str = ""
    quantidade: str = ""
    motivo: str = ""
    observacao: str = ""
    is_loading: bool = False
    is_submitting: bool = False
    error_message: str = ""
    success_message: str = ""
    alert_message: str = ""
    alert_error: str = ""

    @rx.var
    def filtered_products(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.product_query)
        if not query:
            return self.products
        return [
            item for item in self.products
            if query in normalize_search_text(item.get("label", ""))
        ]

    def load_exit_page(self):
        return [AuthState.require_auth(), ExitState.load_exit_data()]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
        if not auth_state.is_authenticated or not auth_state.has_permission("stock.exit"):
            return ""
        return str(auth_state.auth_token or "").strip()

    @staticmethod
    def _product_option(item: dict) -> dict[str, str]:
        product_id = str(item.get("id", ""))
        code = str(item.get("codigo") or "")
        name = str(item.get("nome") or "")
        return {"id": product_id, "label": f"{code} - {name}".strip(" -"), "codigo": code, "nome": name}

    async def load_exit_data(self):
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        self.alert_message = ""
        self.alert_error = ""
        self.product_error = ""
        self._clear_exit_fields()
        self.products = []
        self.stock_by_product = {}
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            return
        try:
            products_response = await auth_client.list_products(token, page=1, per_page=100)
            self.products = [
                self._product_option(item)
                for item in products_response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            ]
            self.product_page = 1
            self.product_has_more = len(products_response["items"]) == 100

            stock_items = []
            stock_page = 1
            while True:
                stock_response = await auth_client.list_stock(token, page=stock_page, per_page=100)
                page_items = stock_response["items"]
                stock_items.extend(page_items)
                if len(page_items) < 100:
                    break
                stock_page += 1
            self.stock_by_product = {
                str(item["product_id"]): {
                    "quantidade_disponivel": str(item.get("quantidade_disponivel", "")),
                    "codigo": str(item.get("codigo") or ""),
                    "nome": str(item.get("nome") or ""),
                    "estoque_minimo": str(item.get("estoque_minimo", "")),
                }
                for item in stock_items
                if isinstance(item, dict) and item.get("product_id") is not None
            }
        except XanoAuthError as exc:
            self.error_message = exc.message
            yield rx.redirect("/")
        except (XanoPermissionError, XanoConnectionError, XanoServerError, XanoRequestError) as exc:
            self.error_message = exc.message
        except Exception:
            self.error_message = "Não foi possível carregar os dados para a saída. Tente novamente."
        finally:
            self.is_loading = False

    def search_products(self, value: str):
        self._clear_selected_product()
        self.product_query = value
        self.product_options_open = True
        self.product_error = ""
        self.error_message = ""

    def open_product_options(self):
        self.product_options_open = True

    def close_product_options(self, value: str = ""):
        self.product_options_open = False

    def close_product_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.product_options_open = False

    def change_barcode(self, value: str):
        self.barcode_value = value
        self.product_error = ""
        if normalize_search_text(value.strip()) != normalize_search_text(self.product_code):
            self._clear_selected_product(keep_barcode=True)

    def _apply_selected_product(self, product: dict[str, str]):
        self.product_id = product["id"]
        self.product_code = product["codigo"]
        self.product_name = product["nome"]
        self.product_query = product["label"]
        self.barcode_value = product["codigo"]
        self.product_options_open = False
        self.product_error = ""
        self.error_message = ""
        stock = self.stock_by_product.get(self.product_id)
        self.stock_balance_found = stock is not None
        self.saldo_disponivel = stock.get("quantidade_disponivel", "") if stock else ""
        try:
            available = Decimal(self.saldo_disponivel)
            self.has_available_stock = stock is not None and available.is_finite() and available > 0
        except (InvalidOperation, ValueError):
            self.has_available_stock = False

    def select_product(self, product_id: str):
        product = next((item for item in self.products if item["id"] == product_id), None)
        if product is not None:
            self._apply_selected_product(product)

    async def on_barcode_key_down(self, key: str):
        if key == "Enter":
            await self.find_product_by_barcode()

    async def find_product_by_barcode(self):
        code = normalize_search_text(self.barcode_value.strip())
        if not code:
            self.product_error = "Informe ou leia o código do produto."
            return
        self._clear_selected_product(keep_barcode=True)
        token = await self._session_token()
        if not token:
            self.product_error = "Sua sessão não está ativa. Faça login novamente."
            return

        product = next((item for item in self.products if normalize_search_text(item["codigo"]) == code), None)
        if product is not None:
            self._apply_selected_product(product)
            return

        page_number = self.product_page + 1
        while self.product_has_more:
            try:
                response = await auth_client.list_products(token, page=page_number, per_page=100)
            except XanoAuthError as exc:
                self.product_error = exc.message
                return
            except XanoError as exc:
                self.product_error = exc.message
                return
            page_items = [
                self._product_option(item)
                for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            ]
            known = {item["id"] for item in self.products}
            self.products.extend(item for item in page_items if item["id"] not in known)
            self.product_page = page_number
            self.product_has_more = len(response["items"]) == 100
            product = next((item for item in page_items if normalize_search_text(item["codigo"]) == code), None)
            if product is not None:
                self._apply_selected_product(product)
                return
            page_number += 1

        self._clear_selected_product(keep_barcode=True)
        self.product_error = "Produto não encontrado."

    async def load_more_products(self):
        if self.product_loading_more or not self.product_has_more:
            return
        token = await self._session_token()
        self.product_loading_more = True
        try:
            page_number = self.product_page + 1
            response = await auth_client.list_products(token, page=page_number, per_page=100)
            known = {item["id"] for item in self.products}
            self.products.extend(
                self._product_option(item) for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None and str(item["id"]) not in known
            )
            self.product_page = page_number
            self.product_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.product_error = exc.message
        finally:
            self.product_loading_more = False

    def change_exit_date_time(self, value: str):
        self.exit_date_time = value

    def change_quantity(self, value: str):
        self.quantidade = value

    def change_reason(self, value: str):
        self.motivo = value

    def change_observation(self, value: str):
        self.observacao = value

    def _clear_selected_product(self, *, keep_barcode: bool = False):
        self.product_id = ""
        self.product_code = ""
        self.product_name = ""
        self.product_query = ""
        self.stock_balance_found = False
        self.saldo_disponivel = ""
        self.has_available_stock = False
        self.product_options_open = False
        if not keep_barcode:
            self.barcode_value = ""

    def _clear_exit_fields(self):
        self._clear_selected_product()
        self.exit_date_time = ""
        self.quantidade = ""
        self.motivo = ""
        self.observacao = ""

    @staticmethod
    def _exit_error_message(error_code: str) -> str:
        messages = {
            "INVALID_INPUT": "Verifique os dados informados.",
            "PRODUCT_NOT_FOUND": "Produto não encontrado.",
            "PRODUCT_INACTIVE": "Não é possível registrar saída para um produto inativo.",
            "STOCK_BALANCE_NOT_FOUND": "Não foi encontrado saldo de estoque para este produto.",
            "INSUFFICIENT_STOCK": "Estoque insuficiente para esta saída.",
            "PERMISSION_DENIED": "Você não possui permissão para registrar saídas de estoque.",
            "STOCK_UPDATE_FAILED": "Não foi possível atualizar o estoque. Tente novamente.",
            "STOCK_CONCURRENCY_CONFLICT": "Houve um conflito ao atualizar o estoque. Tente novamente.",
        }
        return messages.get(error_code, "Não foi possível registrar a saída. Verifique os dados e tente novamente.")

    async def register_exit(self):
        if self.is_submitting:
            return
        self.error_message = ""
        self.success_message = ""
        self.alert_message = ""
        self.alert_error = ""
        try:
            product_id = int(self.product_id)
        except (TypeError, ValueError):
            self.error_message = "Selecione ou leia um produto válido antes de registrar a saída."
            return
        if product_id <= 0:
            self.error_message = "Selecione ou leia um produto válido antes de registrar a saída."
            return
        if not self.stock_balance_found:
            self.error_message = "Não foi encontrado saldo de estoque para este produto."
            return
        if not self.has_available_stock:
            self.error_message = "Este produto não possui estoque disponível."
            return
        try:
            quantity_decimal = Decimal(self.quantidade.strip().replace(",", "."))
            if not quantity_decimal.is_finite() or quantity_decimal <= 0:
                raise InvalidOperation
            stock_decimal = Decimal(self.saldo_disponivel)
            if not stock_decimal.is_finite() or quantity_decimal > stock_decimal:
                self.error_message = "Quantidade maior que o estoque disponível."
                return
            quantity = float(quantity_decimal)
            if not math.isfinite(quantity):
                raise InvalidOperation
        except (InvalidOperation, ValueError, OverflowError):
            self.error_message = "Informe uma quantidade maior que zero."
            return
        reason = self.motivo.strip()
        if not reason:
            self.error_message = "Informe o motivo da saída."
            return

        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        if not auth_state.session_is_valid:
            if auth_state.session_validation in {"temporarily_unavailable", "forbidden", "validating"}:
                self.error_message = auth_state.session_status_message
                return
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
            return
        if not token or not auth_state.has_permission("stock.exit"):
            self.error_message = "Vocé não possui permissão para registrar saídas."
            return

        self.is_submitting = True
        yield
        alert_context = None
        try:
            result = await auth_client.create_stock_exit(
                token,
                product_id=product_id,
                quantidade=quantity,
                motivo=reason,
                data_hora=self.exit_date_time.strip() or None,
                observacao=self.observacao.strip() or None,
            )
            saldo_atual = result.get("saldo_atual")
            alert_context = {
                "destinatario": auth_state.user_email,
                "movement_id": result.get("movement_id"),
                "codigo": self.product_code,
                "nome": self.product_name,
                "saldo_atual": saldo_atual,
                "estoque_minimo": self.stock_by_product.get(str(product_id), {}).get("estoque_minimo"),
                "quantidade": str(quantity_decimal),
                "usuario": auth_state.user_name,
                "data_hora": result.get("data_hora"),
            }
            self.success_message = "Saída registrada com sucesso."
            if saldo_atual is not None:
                self.success_message += f" Saldo atualizado: {saldo_atual}."
                self.stock_by_product = {
                    **self.stock_by_product,
                    str(product_id): {
                        **self.stock_by_product.get(str(product_id), {}),
                        "quantidade_disponivel": str(saldo_atual),
                    },
                }
            self._clear_exit_fields()
            self.product_error = ""
        except XanoAuthError as exc:
            self.error_message = exc.message
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para registrar saídas de estoque."
        except XanoRequestError as exc:
            self.error_message = self._exit_error_message(exc.error_code)
        except XanoConnectionError:
            self.error_message = "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
        except (XanoServerError, XanoError):
            self.error_message = "Não foi possível registrar a saída. Verifique os dados e tente novamente."
        except Exception:
            self.error_message = "Não foi possível registrar a saída. Tente novamente."
        finally:
            self.is_submitting = False

        if alert_context is not None:
            yield
            await self._send_minimum_stock_alert(alert_context)

    async def _send_minimum_stock_alert(self, context: dict):
        """Envia o alerta depois da Saída confirmada, sem afetar o resultado dela."""
        try:
            status = await enviar_alerta_estoque_minimo(**context)
        except Exception:
            logger.exception("Minimum stock alert failed unexpectedly")
            status = STATUS_FALHOU
        if status == STATUS_ENVIADO:
            self.alert_message = f"Alerta de estoque mínimo enviado para {context['destinatario']}."
        elif status == STATUS_FALHOU:
            self.alert_error = "Saída registrada, mas o alerta por e-mail não foi enviado."


class MovementHistoryState(rx.State):
    """Consulta paginada do histórico com filtros independentes das operações."""

    movements: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    product_filter_error: str = ""
    user_filter_error: str = ""

    current_page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 1
    next_page: int | None = None
    prev_page: int | None = None

    filter_type: str = "Todos"
    filter_product_id: str = ""
    filter_user_id: str = ""
    product_options: list[dict[str, str]] = []
    product_query: str = ""
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False
    user_options: list[dict[str, str]] = [{"id": "", "label": "Todos os usuários"}]
    user_query: str = ""
    user_options_open: bool = False
    user_page: int = 1
    user_has_more: bool = False
    user_loading_more: bool = False

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
    def filtered_user_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.user_query)
        if not query:
            return self.user_options
        return [
            item for item in self.user_options
            if query in normalize_search_text(item.get("label", ""))
        ]

    def load_page(self):
        return [
            AuthState.require_auth(),
            MovementHistoryState.load_products(),
            MovementHistoryState.load_users(),
            MovementHistoryState.load_movements(self.current_page),
        ]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
        if not auth_state.is_authenticated or not auth_state.has_permission("movement.read"):
            return ""
        return str(auth_state.auth_token or "").strip()

    @staticmethod
    def _product_option(item: dict) -> dict[str, str]:
        product_id = str(item.get("id", ""))
        code = str(item.get("codigo") or "")
        name = str(item.get("nome") or "")
        return {
            "id": product_id,
            "label": f"{code} - {name}".strip(" -"),
        }

    async def load_products(self):
        self.product_filter_error = ""
        self.product_options = [{"id": "", "label": "Todos os produtos"}]
        self.product_page = 1
        self.product_has_more = False
        token = await self._session_token()
        if not token:
            return
        try:
            response = await auth_client.list_products(token, page=1, per_page=100)
            self.product_options.extend(
                self._product_option(item)
                for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            )
            self.product_has_more = len(response["items"]) == 100
        except XanoAuthError as exc:
            _log_history_failure("products", exc)
            return rx.redirect("/")
        except XanoError as exc:
            _log_history_failure("products", exc)
            self.product_filter_error = "Não foi possível carregar Produtos para o filtro."
        except Exception as exc:
            _log_history_failure("products", exc)
            self.product_filter_error = "Não foi possível carregar Produtos para o filtro."

    @staticmethod
    def _user_option(item: dict) -> dict[str, str]:
        return {
            "id": str(item.get("id", "")),
            "label": str(item.get("name") or "Usuário não encontrado"),
        }

    async def load_users(self):
        self.user_filter_error = ""
        self.user_options = [{"id": "", "label": "Todos os usuários"}]
        self.user_page = 1
        self.user_has_more = False
        token = await self._session_token()
        if not token:
            return
        try:
            response = await auth_client.list_movement_users(token, page=1, per_page=100)
            self.user_options.extend(
                self._user_option(item)
                for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None
            )
            self.user_has_more = len(response["items"]) == 100
        except XanoAuthError as exc:
            _log_history_failure("movement_users", exc)
            return rx.redirect("/")
        except XanoError as exc:
            _log_history_failure("movement_users", exc)
            self.user_filter_error = "Não foi possível carregar usuários para o filtro."
        except Exception as exc:
            _log_history_failure("movement_users", exc)
            self.user_filter_error = "Não foi possível carregar usuários para o filtro."

    async def load_more_users(self):
        if self.user_loading_more or not self.user_has_more:
            return
        token = await self._session_token()
        if not token:
            return
        self.user_loading_more = True
        try:
            page = self.user_page + 1
            response = await auth_client.list_movement_users(token, page=page, per_page=100)
            known = {item["id"] for item in self.user_options}
            self.user_options.extend(
                self._user_option(item)
                for item in response["items"]
                if isinstance(item, dict)
                and item.get("id") is not None
                and str(item["id"]) not in known
            )
            self.user_page = page
            self.user_has_more = len(response["items"]) == 100
        except XanoAuthError:
            return rx.redirect("/")
        except XanoError:
            self.user_filter_error = "Não foi possível carregar mais usuários para o filtro."
        finally:
            self.user_loading_more = False

    def search_products(self, value: str):
        self.product_query = value
        self.product_options_open = True

    def open_product_options(self):
        self.product_options_open = True

    def close_product_options(self, value: str = ""):
        self.product_options_open = False

    def close_product_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.product_options_open = False

    def search_users(self, value: str):
        self.user_query = value
        self.user_options_open = True

    def open_user_options(self):
        self.user_options_open = True

    def close_user_options(self, value: str = ""):
        self.user_options_open = False

    def close_user_options_on_escape(self, key: str, modifiers: dict | None = None):
        if key == "Escape":
            self.user_options_open = False

    def select_user_filter(self, user_id: str):
        self.filter_user_id = "" if user_id in (None, "", "0", 0) else str(user_id)
        selected = next(
            (item for item in self.user_options if item["id"] == user_id),
            None,
        )
        self.user_query = selected["label"] if selected else ""
        self.user_options_open = False
        self.current_page = 1
        return [MovementHistoryState.load_movements(1)]

    def select_product_filter(self, product_id: str):
        self.filter_product_id = "" if product_id in (None, "", "0", 0) else str(product_id)
        selected = next(
            (item for item in self.product_options if item["id"] == product_id),
            None,
        )
        self.product_query = selected["label"] if selected else ""
        self.product_options_open = False
        self.current_page = 1
        return [MovementHistoryState.load_movements(1)]

    async def load_more_products(self):
        if self.product_loading_more or not self.product_has_more:
            return
        token = await self._session_token()
        if not token:
            return
        self.product_loading_more = True
        try:
            page = self.product_page + 1
            response = await auth_client.list_products(token, page=page, per_page=100)
            known = {item["id"] for item in self.product_options}
            self.product_options.extend(
                self._product_option(item)
                for item in response["items"]
                if isinstance(item, dict)
                and item.get("id") is not None
                and str(item["id"]) not in known
            )
            self.product_page = page
            self.product_has_more = len(response["items"]) == 100
        except XanoAuthError:
            return rx.redirect("/")
        except XanoError:
            self.product_filter_error = "Não foi possível carregar mais Produtos para o filtro."
        finally:
            self.product_loading_more = False

    def change_filter_type(self, value: str):
        self.filter_type = value
        self.current_page = 1
        return [MovementHistoryState.load_movements(1)]

    def clear_filters(self):
        self.filter_type = "Todos"
        self.filter_product_id = ""
        self.filter_user_id = ""
        self.product_query = ""
        self.user_query = ""
        self.product_options_open = False
        self.user_options_open = False
        self.current_page = 1
        return [MovementHistoryState.load_movements(1)]

    def load_previous_page(self):
        if self.prev_page is None:
            return
        return [MovementHistoryState.load_movements(self.prev_page)]

    def load_next_page(self):
        if self.next_page is None:
            return
        return [MovementHistoryState.load_movements(self.next_page)]

    @staticmethod
    def _format_datetime(value: object) -> str:
        if value is None or value == "":
            return "—"
        try:
            timestamp_ms = float(value)
            return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError, OverflowError, OSError):
            return "—"

    @staticmethod
    def _format_quantity(value: object) -> str:
        try:
            quantity = Decimal(str(value))
            if not quantity.is_finite():
                return "—"
            formatted = format(quantity.normalize(), "f")
            if "." in formatted:
                formatted = formatted.rstrip("0").rstrip(".")
            return formatted.replace(".", ",")
        except (InvalidOperation, TypeError, ValueError):
            return "—"

    async def load_movements(self, page: int):
        if self.is_loading:
            return
        self.is_loading = True
        self.error_message = ""
        self.movements = []
        yield

        token = await self._session_token()
        if not token:
            self.is_loading = False
            return

        tipo = {
            "Entrada": "entrada",
            "Saída": "saida",
        }.get(self.filter_type)
        try:
            product_value = str(self.filter_product_id or "").strip()
            user_value = str(self.filter_user_id or "").strip()
            product_id = int(product_value) if product_value and product_value != "0" else None
            user_id = int(user_value) if user_value and user_value != "0" else None
            if (product_id is not None and product_id < 0) or (user_id is not None and user_id < 0):
                raise ValueError("IDs de filtro não podem ser negativos.")
        except (TypeError, ValueError):
            self.error_message = "Os filtros informados são inválidos."
            self.is_loading = False
            return

        try:
            response = await auth_client.list_movements(
                token,
                page=page,
                per_page=self.per_page,
                tipo=tipo,
                product_id=product_id,
                user_id=user_id,
            )
            self.movements = [
                {
                    **{
                        key: "" if value is None else str(value)
                        for key, value in item.items()
                    },
                    "data_hora_display": self._format_datetime(item.get("data_hora")),
                    "tipo_display": "Entrada" if item.get("tipo") == "entrada" else "Saída",
                    "quantidade_display": self._format_quantity(item.get("quantidade")),
                    "product_code_display": str(item.get("product_code") or "—"),
                    "product_name_display": str(item.get("product_name") or "Produto não encontrado"),
                    "user_name_display": str(item.get("user_name") or "Usuário não encontrado"),
                    "supplier_name_display": str(item.get("supplier_name") or "—"),
                    "motivo_display": str(item.get("motivo") or "—"),
                    "observacao_display": str(item.get("observacao") or "—"),
                }
                for item in response["items"]
                if isinstance(item, dict)
            ]
            self.current_page = int(response.get("curPage") or page)
            self.total_items = int(response.get("itemsTotal") or 0)
            self.total_pages = max(1, int(response.get("pageTotal") or 0))
            self.next_page = int(response["nextPage"]) if response.get("nextPage") is not None else None
            self.prev_page = int(response["prevPage"]) if response.get("prevPage") is not None else None
        except XanoAuthError as exc:
            _log_history_failure("movements", exc)
            self.error_message = exc.message
            yield rx.redirect("/")
        except XanoPermissionError as exc:
            _log_history_failure("movements", exc)
            self.error_message = "Você não possui permissão para visualizar o histórico de movimentações."
        except XanoRequestError as exc:
            _log_history_failure("movements", exc)
            if exc.error_code == "PERMISSION_DENIED":
                self.error_message = "Você não possui permissão para visualizar o histórico de movimentações."
            elif exc.error_code == "INVALID_INPUT":
                self.error_message = "Os filtros informados são inválidos."
            else:
                self.error_message = "Não foi possível carregar o histórico de movimentações. Tente novamente."
        except XanoConnectionError as exc:
            _log_history_failure("movements", exc)
            self.error_message = "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente."
        except XanoError as exc:
            _log_history_failure("movements", exc)
            self.error_message = "Não foi possível carregar o histórico de movimentações. Tente novamente."
        except Exception as exc:
            _log_history_failure("movements", exc)
            self.error_message = "Não foi possível carregar o histórico de movimentações. Tente novamente."
        finally:
            self.is_loading = False


MOVEMENT_GRID_COLUMNS = "150px 80px 90px minmax(140px, 1fr) 110px minmax(140px, 1fr) 130px minmax(130px, 0.9fr) minmax(170px, 1.3fr)"
MOVEMENT_GRID_COLUMN_GAP = "8px"
MOVEMENT_GRID_CELL_PADDING_X = "6px"


def _movement_row(movement: dict[str, str]) -> rx.Component:
    return rx.box(
        rx.grid(
        rx.text(movement["data_hora_display"], white_space="nowrap", padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        rx.cond(
            movement["tipo"] == "entrada",
            rx.center(rx.badge("Entrada", color_scheme="green"), padding_x=MOVEMENT_GRID_CELL_PADDING_X),
            rx.center(rx.badge("Saída", color_scheme="red"), padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        ),
        rx.text(movement["product_code_display"], padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        rx.text(movement["product_name_display"], overflow="hidden", text_overflow="ellipsis", white_space="nowrap", padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        rx.text(
            movement["quantidade_display"],
            display="flex",
            justify_content="center",
            align_items="center",
            text_align="center",
            width="100%",
            white_space="nowrap",
            padding_x=MOVEMENT_GRID_CELL_PADDING_X,
        ),
        rx.text(movement["user_name_display"], overflow="hidden", text_overflow="ellipsis", white_space="nowrap", padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        rx.text(
            movement["supplier_name_display"],
            display="flex",
            justify_content="center",
            align_items="center",
            text_align="center",
            width="100%",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
            padding_x=MOVEMENT_GRID_CELL_PADDING_X,
        ),
        rx.text(movement["motivo_display"], overflow="hidden", text_overflow="ellipsis", white_space="nowrap", padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        rx.text(movement["observacao_display"], overflow="hidden", text_overflow="ellipsis", white_space="nowrap", padding_x=MOVEMENT_GRID_CELL_PADDING_X),
        columns="9",
        width="100%",
        column_gap=MOVEMENT_GRID_COLUMN_GAP,
        style={"grid_template_columns": MOVEMENT_GRID_COLUMNS, "align_items": "center"},
        padding_y="0.75rem",
        ),
        width="100%",
        border_bottom="1px solid #eee",
    )


def _movement_table() -> rx.Component:
    def header_cell(label: str) -> rx.Component:
        if label in {"Quantidade", "Fornecedor"}:
            return rx.text(
                label,
                weight="bold",
                white_space="nowrap",
                display="flex",
                justify_content="center",
                align_items="center",
                text_align="center",
                width="100%",
                padding_x=MOVEMENT_GRID_CELL_PADDING_X,
            )
        return rx.text(
            label,
            weight="bold",
            white_space="nowrap",
            text_align="center" if label == "Tipo" else "left",
            padding_x=MOVEMENT_GRID_CELL_PADDING_X,
        )

    header = rx.grid(
        *[
            header_cell(label)
            for label in ["Data/Hora", "Tipo", "Código", "Produto", "Quantidade", "Usuário", "Fornecedor", "Motivo", "Observação"]
        ],
        columns="9",
        width="100%",
        column_gap=MOVEMENT_GRID_COLUMN_GAP,
        style={"grid_template_columns": MOVEMENT_GRID_COLUMNS, "align_items": "center"},
        padding_y="0.75rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(MovementHistoryState.movements, _movement_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
        border_radius="0.4rem",
    )


def historico() -> rx.Component:
    return page(
        "Histórico de movimentações",
        rx.vstack(
            rx.vstack(
                rx.text("Filtros", weight="bold", size="4"),
                rx.hstack(
                rx.vstack(
                    rx.text("Tipo"),
                    rx.select(
                        ["Todos", "Entrada", "Saída"],
                        value=MovementHistoryState.filter_type,
                        on_change=MovementHistoryState.change_filter_type,
                    ),
                    align="stretch",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Usuário"),
                    searchable_select(
                        query=MovementHistoryState.user_query,
                        options=MovementHistoryState.filtered_user_options,
                        is_open=MovementHistoryState.user_options_open,
                        on_search=MovementHistoryState.search_users,
                        on_open=MovementHistoryState.open_user_options,
                        on_close=MovementHistoryState.close_user_options,
                        on_escape=MovementHistoryState.close_user_options_on_escape,
                        on_select=MovementHistoryState.select_user_filter,
                        has_more=MovementHistoryState.user_has_more,
                        is_loading_more=MovementHistoryState.user_loading_more,
                        on_load_more=MovementHistoryState.load_more_users,
                        placeholder="Todos os usuários",
                        empty_message="Nenhum usuário encontrado.",
                    ),
                    align="stretch",
                    spacing="1",
                    min_width="220px",
                ),
                rx.vstack(
                    rx.text("Produto"),
                    searchable_select(
                        query=MovementHistoryState.product_query,
                        options=MovementHistoryState.filtered_product_options,
                        is_open=MovementHistoryState.product_options_open,
                        on_search=MovementHistoryState.search_products,
                        on_open=MovementHistoryState.open_product_options,
                        on_close=MovementHistoryState.close_product_options,
                        on_escape=MovementHistoryState.close_product_options_on_escape,
                        on_select=MovementHistoryState.select_product_filter,
                        has_more=MovementHistoryState.product_has_more,
                        is_loading_more=MovementHistoryState.product_loading_more,
                        on_load_more=MovementHistoryState.load_more_products,
                        placeholder="Todos os produtos",
                        empty_message="Nenhum Produto encontrado.",
                    ),
                    align="stretch",
                    spacing="1",
                    min_width="260px",
                ),
                rx.button("Limpar filtros", on_click=MovementHistoryState.clear_filters),
                width="100%",
                wrap="wrap",
                align="end",
                spacing="4",
                ),
                width="100%",
                align="stretch",
                spacing="2",
            ),
            rx.cond(
                MovementHistoryState.product_filter_error != "",
                rx.text(MovementHistoryState.product_filter_error, color="#b45309"),
            ),
            rx.cond(
                MovementHistoryState.user_filter_error != "",
                rx.text(MovementHistoryState.user_filter_error, color="#b45309"),
            ),
            section(
                "Movimentações",
                rx.cond(
                    MovementHistoryState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando histórico..."), width="100%", padding="2rem"),
                    rx.cond(
                        MovementHistoryState.error_message != "",
                        rx.text(MovementHistoryState.error_message, color="#b91c1c"),
                        rx.cond(
                            MovementHistoryState.movements.length() > 0,
                            _movement_table(),
                            rx.text("Nenhuma movimentação encontrada.", color="#64748b", padding="1rem"),
                        ),
                    ),
                ),
            ),
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=MovementHistoryState.load_previous_page,
                    disabled=MovementHistoryState.prev_page == None,
                    variant="soft",
                ),
                rx.text(
                    "Página ",
                    MovementHistoryState.current_page,
                    " de ",
                    MovementHistoryState.total_pages,
                    " · ",
                    MovementHistoryState.total_items,
                    " movimentações",
                ),
                rx.button(
                    "Próxima",
                    on_click=MovementHistoryState.load_next_page,
                    disabled=MovementHistoryState.next_page == None,
                    variant="soft",
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )


def entrada() -> rx.Component:
    return page(
        "Registrar entrada de estoque",
        rx.vstack(
            rx.cond(EntryState.is_loading, rx.center(rx.spinner(), "Carregando dados...")),
            rx.cond(EntryState.error_message != "", rx.text(EntryState.error_message, color="#b91c1c")),
            rx.cond(EntryState.success_message != "", rx.text(EntryState.success_message, color="#15803d")),
            section(
                "Dados da entrada",
                rx.vstack(
                    rx.text("Código do produto"),
                    rx.input(
                        value=EntryState.barcode_value,
                        on_change=EntryState.change_barcode,
                        on_key_down=EntryState.on_barcode_key_down,
                        placeholder="Leia ou digite o código e pressione Enter",
                        auto_complete=False,
                    ),
                    rx.cond(EntryState.product_error != "", rx.text(EntryState.product_error, color="#b91c1c")),
                    rx.vstack(
                        rx.text("Produto"),
                        searchable_select(
                            query=EntryState.product_query,
                            options=EntryState.filtered_products,
                            is_open=EntryState.product_options_open,
                            on_search=EntryState.search_products,
                            on_open=EntryState.open_product_options,
                            on_close=EntryState.close_product_options,
                            on_escape=EntryState.close_product_options_on_escape,
                            on_select=EntryState.select_product,
                            has_more=EntryState.product_has_more,
                            is_loading_more=EntryState.product_loading_more,
                            on_load_more=EntryState.load_more_products,
                            placeholder="Buscar por código ou nome...",
                        ),
                        width="100%", align="stretch", spacing="1",
                    ),
                    rx.input(
                        placeholder="Quantidade",
                        type="number",
                        min="0",
                        step="any",
                        value=EntryState.quantidade,
                        on_change=EntryState.change_quantity,
                    ),
                    rx.vstack(
                        rx.text("Fornecedor"),
                        searchable_select(
                            query=EntryState.supplier_query,
                            options=EntryState.filtered_suppliers,
                            is_open=EntryState.supplier_options_open,
                            on_search=EntryState.search_suppliers,
                            on_open=EntryState.open_supplier_options,
                            on_close=EntryState.close_supplier_options,
                            on_escape=EntryState.close_supplier_options_on_escape,
                            on_select=EntryState.select_supplier,
                            has_more=EntryState.supplier_has_more,
                            is_loading_more=EntryState.supplier_loading_more,
                            on_load_more=EntryState.load_more_suppliers,
                            placeholder="Buscar fornecedor...",
                        ),
                        width="100%", align="stretch", spacing="1",
                    ),
                    rx.cond(EntryState.supplier_error != "", rx.text(EntryState.supplier_error, color="#b45309")),
                    rx.vstack(
                        rx.text("Data e hora (opcional)"),
                        rx.input(
                            type="datetime-local",
                            value=EntryState.entry_date_time,
                            on_change=EntryState.change_entry_date_time,
                        ),
                        rx.text(
                            "Se nenhuma data for informada, será utilizada automaticamente a data e hora do registro da entrada.",
                            color="#64748b",
                            font_size="0.875rem",
                        ),
                        width="100%", align="stretch", spacing="1",
                    ),
                    rx.input(
                        placeholder="Motivo",
                        value=EntryState.motivo,
                        on_change=EntryState.change_reason,
                    ),
                    rx.text_area(
                        placeholder="Observação",
                        value=EntryState.observacao,
                        on_change=EntryState.change_observation,
                    ),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button(
                            rx.cond(EntryState.is_submitting, "Registrando...", "Registrar entrada"),
                            on_click=EntryState.register_entry,
                            disabled=EntryState.is_submitting | EntryState.is_loading,
                        ),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )

def saida() -> rx.Component:
    return page(
        "Registrar saída de estoque",
        rx.vstack(
            rx.cond(ExitState.is_loading, rx.center(rx.spinner(), "Carregando dados...")),
            rx.cond(ExitState.error_message != "", rx.text(ExitState.error_message, color="#b91c1c")),
            rx.cond(ExitState.success_message != "", rx.text(ExitState.success_message, color="#15803d")),
            rx.cond(ExitState.alert_message != "", rx.text(ExitState.alert_message, color="#15803d")),
            rx.cond(ExitState.alert_error != "", rx.text(ExitState.alert_error, color="#b45309")),
            section(
                "Dados da saída",
                rx.vstack(
                    rx.text("Código do produto"),
                    rx.input(
                        value=ExitState.barcode_value,
                        on_change=ExitState.change_barcode,
                        on_key_down=ExitState.on_barcode_key_down,
                        placeholder="Leia ou digite o código e pressione Enter",
                        auto_complete=False,
                    ),
                    rx.cond(ExitState.product_error != "", rx.text(ExitState.product_error, color="#b91c1c")),
                    rx.vstack(
                        rx.text("Produto"),
                        searchable_select(
                            query=ExitState.product_query,
                            options=ExitState.filtered_products,
                            is_open=ExitState.product_options_open,
                            on_search=ExitState.search_products,
                            on_open=ExitState.open_product_options,
                            on_close=ExitState.close_product_options,
                            on_escape=ExitState.close_product_options_on_escape,
                            on_select=ExitState.select_product,
                            has_more=ExitState.product_has_more,
                            is_loading_more=ExitState.product_loading_more,
                            on_load_more=ExitState.load_more_products,
                            placeholder="Buscar por código ou nome...",
                        ),
                        width="100%", align="stretch", spacing="1",
                    ),
                    rx.cond(
                        ExitState.product_id != "",
                        rx.cond(
                            ExitState.stock_balance_found,
                            rx.text(f"Saldo disponível: {ExitState.saldo_disponivel}"),
                            rx.text("Não foi encontrado saldo de estoque para este produto.", color="#b45309"),
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        (ExitState.product_id != "") & ExitState.stock_balance_found & ~ExitState.has_available_stock,
                        rx.text("Este produto não possui estoque disponível.", color="#b45309"),
                        rx.fragment(),
                    ),
                    rx.input(
                        placeholder="Quantidade",
                        type="number",
                        min="0",
                        step="any",
                        value=ExitState.quantidade,
                        on_change=ExitState.change_quantity,
                    ),
                    rx.vstack(
                        rx.text("Data e hora (opcional)"),
                        rx.input(
                            type="datetime-local",
                            value=ExitState.exit_date_time,
                            on_change=ExitState.change_exit_date_time,
                        ),
                        rx.text(
                            "Se nenhuma data for informada, o Xano utilizará a data e hora do registro da saída.",
                            color="#64748b",
                            font_size="0.875rem",
                        ),
                        width="100%", align="stretch", spacing="1",
                    ),
                    rx.input(
                        placeholder="Motivo",
                        value=ExitState.motivo,
                        on_change=ExitState.change_reason,
                    ),
                    rx.text_area(
                        placeholder="Observação",
                        value=ExitState.observacao,
                        on_change=ExitState.change_observation,
                    ),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button(
                            rx.cond(ExitState.is_submitting, "Registrando...", "Registrar saída"),
                            on_click=ExitState.register_exit,
                            disabled=ExitState.is_submitting | ExitState.is_loading | ~ExitState.has_available_stock,
                        ),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )
