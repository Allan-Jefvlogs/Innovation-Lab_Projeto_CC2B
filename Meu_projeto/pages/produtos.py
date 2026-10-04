import math
from typing import Any

import reflex as rx

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


def _normalize_product_unit(value: object) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in PRODUCT_UNIT_CODES else ""


def _map_product_to_list_item(
    item: dict[str, Any],
    category_names: dict[str, str],
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
        "abaixo_minimo": "Abaixo do mínimo",
        "normal": "Normal",
    }
    if stock is None:
        stock_situation = "Saldo não encontrado"
    else:
        stock_situation = situation_labels.get(
            str(stock.get("situacao_estoque") or ""), "Situação desconhecida"
        )

    category_id = item.get("categoria_id")
    if category_id is None:
        category_name = "Sem categoria"
    else:
        category_name = category_names.get(
            str(category_id), "Categoria não encontrada"
        )

    return {
        "id": product_id,
        "codigo": str(item.get("codigo") or "—"),
        "nome": str(item.get("nome") or "—"),
        "categoria": category_name,
        "unidade_medida": _normalize_product_unit(item.get("unidade_medida"))
        or str(item.get("unidade_medida") or "—"),
        "quantidade_disponivel": (
            str(stock_quantity) if stock_quantity is not None else "—"
        ),
        "estoque_minimo": str(stock_minimum) if stock_minimum is not None else "—",
        "status": str(item.get("status") or "—"),
        "situacao_estoque": stock_situation,
    }


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
    can_manage_products: bool = False
    has_loaded_product: bool = False
    has_products: bool = False
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
        if option and option.get("disabled") != "true":
            self.supplier_selection = selected_id
            self.supplier_search_query = option["label"]
            self.supplier_dropdown_open = False

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

    async def _session(self):
        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        return token, auth_state.inventory_profile_id, auth_state.is_authenticated

    @staticmethod
    def _category_option(item: dict[str, Any], *, disabled: bool = False) -> dict[str, str]:
        category_id = str(item.get("id", ""))
        label = str(item.get("nome") or f"Categoria (ID {category_id})")
        if disabled:
            label = f"{label} (inativa — vínculo atual)"
        return {"id": category_id, "label": label, "disabled": "true" if disabled else "false"}

    @staticmethod
    def _supplier_option(item: dict[str, Any]) -> dict[str, str]:
        supplier_id = str(item.get("id", ""))
        label = str(item.get("nome_razao_social") or f"Fornecedor (ID {supplier_id})")
        return {"id": supplier_id, "label": label, "disabled": "false"}

    async def _load_categories(self, token: str, current_category_id: int | None = None):
        response = await auth_client.list_categories(token, page=1, per_page=100, status="ativo")
        items = [item for item in response["items"] if isinstance(item, dict) and item.get("id") is not None]
        self.category_options = [self._category_option(item) for item in items]
        self.category_page = 1
        self.category_has_more = len(response["items"]) == 100
        if current_category_id is not None and not any(
            option["id"] == str(current_category_id) for option in self.category_options
        ):
            try:
                current = await auth_client.get_category(token, current_category_id)
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
        response = await auth_client.list_suppliers(token, page=1, per_page=100)
        items = [item for item in response["items"] if isinstance(item, dict) and item.get("id") is not None]
        self.supplier_options = [
            {"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"},
            *(self._supplier_option(item) for item in items),
        ]
        self.supplier_page = 1
        self.supplier_has_more = len(response["items"]) == 100
        if current_supplier_id is not None and not any(
            option["id"] == str(current_supplier_id) for option in self.supplier_options
        ):
            try:
                current = await auth_client.get_supplier(token, current_supplier_id)
                self.supplier_options.append(self._supplier_option(current))
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
        token, _, authenticated = await self._session()
        if not token or not authenticated:
            return
        self.category_loading_more = True
        try:
            page = self.category_page + 1
            response = await auth_client.list_categories(token, page=page, per_page=100, status="ativo")
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
        token, _, authenticated = await self._session()
        if not token or not authenticated:
            return
        self.supplier_loading_more = True
        try:
            page = self.supplier_page + 1
            response = await auth_client.list_suppliers(token, page=page, per_page=100)
            known = {option["id"] for option in self.supplier_options}
            new_items = [
                self._supplier_option(item) for item in response["items"]
                if isinstance(item, dict) and item.get("id") is not None and str(item["id"]) not in known
            ]
            self.supplier_options.extend(new_items)
            self.supplier_page = page
            self.supplier_has_more = len(response["items"]) == 100
        except XanoError as exc:
            self.supplier_error_message = exc.message
        finally:
            self.supplier_loading_more = False

    async def load_products(self):
        self.is_loading = True
        self.can_manage_products = False
        self.error_message = ""
        self.has_products = False
        self.products = []
        yield
        token, profile_id, is_authenticated = await self._session()
        if not token or not is_authenticated:
            self.is_loading = False
            return
        self.can_manage_products = profile_id in (1, 2)
        try:
            response = await auth_client.list_products(token, page=1, per_page=100)
            categories = []
            category_page = 1
            while True:
                categories_response = await auth_client.list_categories(
                    token, page=category_page, per_page=100
                )
                category_items = categories_response["items"]
                categories.extend(category_items)
                if len(category_items) < 100:
                    break
                category_page += 1

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

            category_names = {
                str(category["id"]): str(category["nome"])
                for category in categories
                if isinstance(category, dict)
                and category.get("id") is not None
                and category.get("nome")
            }
            stock_by_product = {
                str(stock["product_id"]): stock
                for stock in stock_items
                if isinstance(stock, dict) and stock.get("product_id") is not None
            }
            self.products = [
                _map_product_to_list_item(item, category_names, stock_by_product)
                for item in response["items"]
                if isinstance(item, dict)
            ]
            self.has_products = bool(self.products)
        except XanoAuthError as exc:
            self.error_message = exc.message
            yield rx.redirect("/")
        except (XanoPermissionError, XanoConnectionError, XanoServerError, XanoRequestError) as exc:
            self.error_message = exc.message
        except Exception:
            self.error_message = "Não foi possível carregar os produtos. Tente novamente."
        finally:
            self.is_loading = False

    async def load_create_form(self):
        self.is_loading = True
        self.error_message = ""
        self.category_error_message = ""
        self.supplier_error_message = ""
        self.success_message = ""
        self.can_manage_products = False
        yield
        token, profile_id, is_authenticated = await self._session()
        if not token or not is_authenticated or profile_id not in (1, 2):
            self.is_loading = False
            self.error_message = "Seu perfil não está autorizado a criar produtos."
            return
        self.can_manage_products = True
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
        token, profile_id, is_authenticated = await self._session()
        if not token or not is_authenticated:
            self.error_message = "Sua sessão não está ativa. Faça login novamente."
            return
        if profile_id not in (1, 2):
            self.error_message = "Seu perfil não está autorizado a criar produtos."
            return
        category_id = _selected_category_id(self.category_selection)
        minimum = _parse_minimum(self.estoque_minimo)
        if not self.codigo.strip() or not self.nome.strip() or category_id is None or self.unidade_medida not in PRODUCT_UNIT_CODES or minimum is None:
            self.error_message = "Preencha código, nome, categoria, unidade de medida e estoque mínimo válido (maior ou igual a zero)."
            return
        available_supplier_ids = {
            option["id"]
            for option in self.supplier_options
            if option.get("id") != "none" and option.get("disabled") == "false"
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
            await auth_client.create_product(token, payload)
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
        self.is_loading = True
        self.can_manage_products = False
        self.has_loaded_product = False
        self.error_message = ""
        self.category_error_message = ""
        self.supplier_error_message = ""
        self.success_message = ""
        self.original_product = {}
        yield
        token, profile_id, is_authenticated = await self._session()
        if not token or not is_authenticated or profile_id not in (1, 2):
            self.is_loading = False
            self.error_message = "Seu perfil não está autorizado a editar produtos."
            return
        self.can_manage_products = True
        route_parts = str(self.router.url.path).strip("/").split("/")
        if len(route_parts) != 3 or route_parts[0] != "produtos" or route_parts[2] != "editar":
            self.is_loading = False
            self.error_message = "A rota do produto é inválida."
            return
        try:
            product_id = int(route_parts[1])
        except ValueError:
            self.is_loading = False
            self.error_message = "O identificador do produto é inválido."
            return

        try:
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
            try:
                await self._load_categories(token, current_category_id)
            except (XanoError, XanoRequestError) as exc:
                self.category_error_message = exc.message
                self.category_options = [{
                    "id": str(current_category_id),
                    "label": f"Categoria atual (ID {current_category_id})",
                    "disabled": "true",
                }]
                self.category_has_more = False
            try:
                await self._load_suppliers(token, current_supplier_id)
            except (XanoError, XanoRequestError) as exc:
                self.supplier_error_message = exc.message
                self.supplier_options = [
                    {"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"}
                ]
                if current_supplier_id is not None:
                    self.supplier_options.append({
                        "id": str(current_supplier_id),
                        "label": f"Fornecedor atual (ID {current_supplier_id})",
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
        except (KeyError, TypeError, ValueError):
            self.error_message = "O Xano retornou dados de produto em formato inesperado."
        except Exception:
            self.error_message = "Não foi possível carregar o produto. Tente novamente."
        finally:
            self.is_loading = False

    async def update_product(self):
        self.error_message = ""
        self.success_message = ""
        token, profile_id, is_authenticated = await self._session()
        if not token or not is_authenticated or not self.has_loaded_product:
            self.error_message = "Sua sessão não está ativa. Faça login novamente."
            return
        if profile_id not in (1, 2):
            self.error_message = "Seu perfil não está autorizado a editar produtos."
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
                if option.get("id") != "none" and option.get("disabled") == "false"
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

        self.is_saving = True
        yield
        fields_update_completed = False
        try:
            if payload:
                await auth_client.update_product(token, self.product_id, payload)
                fields_update_completed = True

            if status_changed:
                if self.original_product_status == "ativo" and self.current_product_status == "inativo":
                    await auth_client.inactivate_product(token, self.product_id)
                elif self.original_product_status == "inativo" and self.current_product_status == "ativo":
                    await auth_client.activate_product(token, self.product_id)
                else:
                    self.error_message = "O status selecionado não é válido para este produto."
                    return
                self.original_product_status = self.current_product_status
                self.original_product["status"] = self.original_product_status

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
        if not self.has_loaded_product:
            self.error_message = "Carregue um produto antes de alterar o status."
            return
        if not self.can_manage_products:
            self.error_message = "Seu perfil não está autorizado a alterar o status do produto."
            return
        if self.current_product_status == "ativo":
            self.current_product_status = "inativo"
        elif self.current_product_status == "inativo":
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
    return rx.grid(
        rx.text(product["codigo"], padding_x="12px"),
        rx.text(product["nome"], padding_x="12px"),
        rx.text(product["categoria"], padding_x="12px"),
        rx.text(product["unidade_medida"], padding_x="12px", text_align="center"),
        rx.text(product["estoque_minimo"], padding_x="12px", text_align="center"),
        rx.text(product["status"], padding_x="12px", text_align="center"),
        rx.center(
            rx.cond(
                ProductsState.can_manage_products,
                rx.link("Editar", href=f"/produtos/{product['id']}/editar"),
                rx.text("—"),
            ),
            padding_x="12px",
        ),
        columns="7",
        width="100%",
        column_gap="4px",
        style={"grid_template_columns": PRODUCT_GRID, "align_items": "center"},
        padding="0.75rem",
        border_bottom="1px solid #eee",
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
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(ProductsState.filtered_products, _product_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
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
        rx.cond(ProductsState.error_message != "", rx.text(ProductsState.error_message, color="#b91c1c")),
        rx.cond(ProductsState.category_error_message != "", rx.text(ProductsState.category_error_message, color="#b91c1c")),
        rx.cond(ProductsState.supplier_error_message != "", rx.text(ProductsState.supplier_error_message, color="#b91c1c")),
        rx.cond(ProductsState.success_message != "", rx.text(ProductsState.success_message, color="#15803d")),
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
                    rx.icon(tag="search", size=18, color="#64748B"),
                    rx.input(
                        value=ProductsState.search_query,
                        on_change=ProductsState.change_search_query,
                        placeholder="Buscar por código, nome ou categoria...",
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
                    border="1px solid #CBD5E1",
                    border_radius="8px",
                    background="white",
                ),
                rx.spacer(),
                rx.cond(ProductsState.can_manage_products, rx.link(rx.button("Novo produto"), href="/produtos/novo"), rx.text("")),
                width="100%",
            ),
            section(
                "Produtos cadastrados",
                rx.cond(
                    ProductsState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando produtos..."), spacing="3", padding="2rem"),
                    rx.cond(
                        ProductsState.error_message != "",
                        _feedback(),
                        rx.cond(
                            ProductsState.has_products,
                            rx.cond(
                                ProductsState.has_filtered_products,
                                rx.vstack(
                                    _products_table(),
                                    width="100%",
                                    align="stretch",
                                    spacing="2",
                                ),
                                rx.text("Nenhum produto encontrado."),
                            ),
                            rx.text("Nenhum produto cadastrado."),
                        ),
                    ),
                ),
            ),
        ),
    )


def _product_form(is_edit: bool) -> rx.Component:
    save_button = rx.button(
        rx.cond(
            ProductsState.is_saving,
            "Salvando...",
            "Salvar alterações" if is_edit else "Salvar produto",
        ),
        on_click=ProductsState.update_product if is_edit else ProductsState.create_product,
        loading=ProductsState.is_saving,
        disabled=ProductsState.is_saving,
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
    form_content = (
        rx.cond(ProductsState.has_loaded_product, form_fields, _feedback())
        if is_edit
        else form_fields
    )
    return rx.vstack(
        _feedback(),
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
        section("Dados do produto", _product_form(is_edit=False)),
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
                rx.cond(ProductsState.can_manage_products & ProductsState.has_loaded_product, _status_action(), rx.text("")),
                _product_form(is_edit=True),
                width="100%",
                align="stretch",
                spacing="4",
            ),
        ),
    )
