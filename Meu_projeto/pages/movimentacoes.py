import reflex as rx
import math
from decimal import Decimal, InvalidOperation

from ..components.layout import mock_table, page, section
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
from ..state import AuthState


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
    def _supplier_option(item: dict, *, disabled: bool = False) -> dict[str, str]:
        supplier_id = str(item.get("id", ""))
        label = str(item.get("nome_razao_social") or f"Fornecedor (ID {supplier_id})")
        if disabled:
            label = f"{label} (inativo — vínculo atual)"
        return {"id": supplier_id, "label": label, "disabled": "true" if disabled else "false"}

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
                token, page=1, per_page=100, status="ativo"
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
                existing_supplier = self._supplier_option(
                    supplier, disabled=supplier.get("status") != "ativo"
                )
                self.suppliers.append(existing_supplier)
            except XanoError as exc:
                self.supplier_error = (
                    "Não foi possível carregar o fornecedor padrão do produto. "
                    "Você ainda pode escolher outro fornecedor."
                )
                self.supplier_id = ""
                self.supplier_query = ""
                return

        if existing_supplier.get("disabled") == "true":
            self.supplier_id = ""
            self.supplier_query = "Sem fornecedor"
            self.supplier_error = (
                "O fornecedor padrão está inativo. Escolha um fornecedor ativo "
                "ou deixe a entrada sem fornecedor."
            )
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
                token, page=page_number, per_page=100, status="ativo"
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
        if not token or not auth_state.is_authenticated:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
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
        if not token or not auth_state.is_authenticated:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
            return

        self.is_submitting = True
        yield
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


def historico() -> rx.Component:
    return page(
        "Histórico de movimentações",
        rx.vstack(
            rx.hstack(
                rx.select(["Todos", "Entrada", "Saída"], placeholder="Tipo"),
                rx.input(placeholder="Produto"),
                rx.input(type="date"),
                rx.input(type="date"),
                rx.button("Filtrar"),
                width="100%",
                wrap="wrap",
            ),
            section(
                "Movimentações",
                mock_table(
                    ["ID", "Tipo", "Produto", "Qtd.", "Data/hora", "Usuário", "Motivo"],
                    [
                        ["MOV-104", "Entrada", "Arroz 5kg", "50", "22/09/2026 14:32", "Ana", "Compra"],
                        ["MOV-103", "Saída", "Café 500g", "8", "22/09/2026 13:10", "Carlos", "Consumo interno"],
                        ["MOV-102", "Entrada", "Detergente", "30", "22/09/2026 11:45", "Ana", "Compra"],
                        ["MOV-101", "Saída", "Papel A4", "5", "22/09/2026 09:20", "Carlos", "Uso administrativo"],
                    ],
                ),
            ),
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
