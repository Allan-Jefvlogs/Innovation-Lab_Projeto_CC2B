import math

import reflex as rx

from ..components.layout import page, section
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


class ProductsState(rx.State):
    """Estado da listagem e dos formulários reais de Produto."""

    products: list[dict[str, str]] = []
    category_options: list[str] = []
    category_selection: str = ""
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
    success_message: str = ""

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

    def change_codigo(self, value: str):
        self.codigo = value

    def change_nome(self, value: str):
        self.nome = value

    def change_descricao(self, value: str):
        self.descricao = value

    def change_category(self, value: str):
        self.category_selection = value

    def change_unidade_medida(self, value: str):
        self.unidade_medida = value

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

    async def _load_categories(self, token: str, current_category_id: int | None = None):
        response = await auth_client.list_categories(token, page=1, per_page=100, status="ativo")
        options = [
            f"{item['id']} · {item['nome']}"
            for item in response["items"]
            if isinstance(item, dict) and item.get("id") is not None and item.get("nome")
        ]
        if current_category_id is not None and not any(
            option.split(" · ", 1)[0] == str(current_category_id) for option in options
        ):
            options.append(f"{current_category_id} · Categoria atual (inativa ou não listada)")
        self.category_options = options
        return options

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
            self.products = [
                {
                    "id": str(item.get("id", "")),
                    "codigo": str(item.get("codigo") or "—"),
                    "nome": str(item.get("nome") or "—"),
                    "categoria_id": str(item.get("categoria_id") or ""),
                    "unidade_medida": str(item.get("unidade_medida") or "—"),
                    "estoque_minimo": str(item.get("estoque_minimo") if item.get("estoque_minimo") is not None else "—"),
                    "status": str(item.get("status") or "—"),
                }
                for item in response["items"]
                if isinstance(item, dict)
            ]
            self.has_products = bool(self.products)
        except (XanoAuthError, XanoPermissionError, XanoConnectionError, XanoServerError, XanoRequestError) as exc:
            self.error_message = exc.message
        except Exception:
            self.error_message = "Não foi possível carregar os produtos. Tente novamente."
        finally:
            self.is_loading = False

    async def load_create_form(self):
        self.is_loading = True
        self.error_message = ""
        self.category_error_message = ""
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
        self.codigo = ""
        self.nome = ""
        self.descricao = ""
        self.category_selection = ""
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
        if not self.codigo.strip() or not self.nome.strip() or category_id is None or not self.unidade_medida.strip() or minimum is None:
            self.error_message = "Preencha código, nome, categoria, unidade de medida e estoque mínimo válido (maior ou igual a zero)."
            return

        payload = {
            "codigo": self.codigo,
            "nome": self.nome,
            "categoria_id": category_id,
            "unidade_medida": self.unidade_medida,
            "estoque_minimo": minimum,
        }
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
                    "A Categoria selecionada não existe ou está inativa. Selecione uma Categoria ativa."
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
            self.unidade_medida = str(product.get("unidade_medida") or "")
            self.estoque_minimo = str(product.get("estoque_minimo") if product.get("estoque_minimo") is not None else "")
            self.original_product_status = str(product.get("status") or "")
            self.current_product_status = self.original_product_status
            current_category_id = int(product["categoria_id"])
            self.has_loaded_product = True
            try:
                await self._load_categories(token, current_category_id)
            except (XanoError, XanoRequestError) as exc:
                self.category_error_message = exc.message
                self.category_options = [f"{current_category_id} · Categoria atual"]
            self.category_selection = next(
                (option for option in self.category_options if option.split(" · ", 1)[0] == str(current_category_id)),
                f"{current_category_id} · Categoria atual",
            )
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
        if not self.codigo.strip() or not self.nome.strip() or category_id is None or not self.unidade_medida.strip() or minimum is None:
            self.error_message = "Preencha código, nome, categoria, unidade de medida e estoque mínimo válido."
            return

        original = self.original_product
        payload: dict[str, object] = {}
        for field, value in (
            ("codigo", self.codigo),
            ("nome", self.nome),
            ("categoria_id", category_id),
            ("unidade_medida", self.unidade_medida),
            ("estoque_minimo", minimum),
        ):
            if str(original.get(field, "")) != str(value):
                payload[field] = value
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


def _product_row(product: dict[str, str]) -> rx.Component:
    category_id = product["categoria_id"]
    category_text = rx.cond(category_id != "", f"ID {category_id}", "—")
    return rx.hstack(
        rx.text(product["codigo"], flex="1", min_width="120px"),
        rx.text(product["nome"], flex="1", min_width="120px"),
        rx.text(category_text, flex="1", min_width="120px"),
        rx.text(product["unidade_medida"], flex="1", min_width="120px"),
        rx.text("—", flex="1", min_width="120px"),
        rx.text(product["estoque_minimo"], flex="1", min_width="120px"),
        rx.text(product["status"], flex="1", min_width="120px"),
        rx.cond(
            ProductsState.can_manage_products,
            rx.link("Editar", href=f"/produtos/{product['id']}/editar"),
            rx.text("—"),
        ),
        width="100%",
        padding="0.75rem",
        border_bottom="1px solid #eee",
    )


def _products_table() -> rx.Component:
    headers = ["Código", "Nome", "Categoria ID", "Unidade", "Qtd.", "Mínimo", "Status", "Ações"]
    header = rx.hstack(
        *[rx.text(label, weight="bold", flex="1", min_width="120px") for label in headers],
        width="100%",
        padding="0.75rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(ProductsState.products, _product_row), width="100%", spacing="0"),
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
        rx.vstack(rx.text("Categoria"), rx.select(ProductsState.category_options, value=ProductsState.category_selection, on_change=ProductsState.change_category, placeholder="Selecione uma Categoria"), width="100%", align="stretch", spacing="1"),
        rx.vstack(rx.text("Unidade de medida"), rx.input(value=ProductsState.unidade_medida, on_change=ProductsState.change_unidade_medida, placeholder="Ex.: UN, KG, L"), width="100%", align="stretch", spacing="1"),
        rx.vstack(rx.text("Estoque mínimo"), rx.input(value=ProductsState.estoque_minimo, on_change=ProductsState.change_estoque_minimo, placeholder="0", type="number", step="0.01"), width="100%", align="stretch", spacing="1"),
        width="100%",
        align="stretch",
        spacing="3",
    )


def _feedback() -> rx.Component:
    return rx.vstack(
        rx.cond(ProductsState.error_message != "", rx.text(ProductsState.error_message, color="#b91c1c")),
        rx.cond(ProductsState.category_error_message != "", rx.text(ProductsState.category_error_message, color="#b91c1c")),
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
                rx.input(placeholder="Buscar por código ou nome...", width="350px"),
                rx.button("Buscar"),
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
                            rx.vstack(
                                _products_table(),
                                rx.text("A API não informa a quantidade atual em estoque nem o nome da Categoria.", color="#64748b", size="2"),
                                width="100%",
                                align="stretch",
                                spacing="2",
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
