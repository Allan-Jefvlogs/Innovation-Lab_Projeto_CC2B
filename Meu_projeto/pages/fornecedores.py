import reflex as rx
from typing import Any

from ..components.layout import page, section
from ..components.searchable_select import normalize_search_text
from ..services.xano_client import XanoAuthError, XanoError, XanoRequestError, auth_client
from ..state import AuthState


def _numeric_digits(value: str) -> str:
    """Retorna somente dígitos ASCII do valor digitado."""
    return "".join(character for character in value if "0" <= character <= "9")


def _format_document(value: str, document_type: str) -> str:
    """Formata CPF/CNPJ incrementalmente e limita o número de dígitos."""
    limit = 11 if document_type == "CPF" else 14
    digits = _numeric_digits(value)[:limit]
    if document_type == "CPF":
        if len(digits) <= 3:
            return digits
        if len(digits) <= 6:
            return f"{digits[:3]}.{digits[3:]}"
        if len(digits) <= 9:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    if len(digits) <= 2:
        return digits
    if len(digits) <= 5:
        return f"{digits[:2]}.{digits[2:]}"
    if len(digits) <= 8:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:]}"
    if len(digits) <= 12:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:]}"
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _format_phone(value: str) -> str:
    """Formata telefone fixo/celular e limita a 11 dígitos."""
    digits = _numeric_digits(value)[:11]
    if len(digits) <= 2:
        return digits

    area_code = digits[:2]
    subscriber = digits[2:]
    split_at = 5 if len(digits) == 11 else 4
    if len(subscriber) <= split_at:
        return f"({area_code}) {subscriber}"
    return f"({area_code}) {subscriber[:split_at]}-{subscriber[split_at:]}"


class SupplierState(rx.State):
    """Lista e mantém Fornecedores reais do Xano."""

    suppliers: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    search_term: str = ""
    applied_search_term: str = ""

    modal_open: bool = False
    editing_supplier_id: str = ""
    loading_supplier_id: str = ""
    nome_razao_social: str = ""
    tipo_documento: str = "CNPJ"
    documento: str = ""
    original_documento: str = ""
    documento_dirty: bool = False
    contato: str = ""
    original_contato: str = ""
    contato_dirty: bool = False
    endereco: str = ""
    create_loading: bool = False
    update_loading: bool = False
    _can_create_suppliers: bool = False
    _can_update_suppliers: bool = False

    @rx.var
    def filtered_suppliers(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.applied_search_term)
        if not query:
            return self.suppliers
        fields = ("nome_razao_social", "documento")
        return [
            item
            for item in self.suppliers
            if any(query in normalize_search_text(item.get(field, "")) for field in fields)
        ]

    @rx.var
    def is_saving(self) -> bool:
        return self.create_loading or self.update_loading

    @rx.var
    def is_editing(self) -> bool:
        return self.editing_supplier_id != ""

    @rx.var
    def can_create_suppliers(self) -> bool:
        return self._can_create_suppliers

    @rx.var
    def can_update_suppliers(self) -> bool:
        return self._can_update_suppliers

    @rx.var
    def can_access_supplier_form(self) -> bool:
        return (
            self._can_update_suppliers
            if self.editing_supplier_id
            else self._can_create_suppliers
        )

    def load_page(self):
        return [AuthState.require_auth(), SupplierState.load_suppliers()]

    async def _session(self) -> tuple[str, bool, list[str]]:
        auth_state = await self.get_state(AuthState)
        return (
            str(auth_state.auth_token or "").strip(),
            auth_state.is_authenticated,
            list(auth_state.permission_codes),
        )

    def _set_write_permissions(self, permission_codes: list[str]):
        self._can_create_suppliers = "supplier.create" in permission_codes
        self._can_update_suppliers = "supplier.update" in permission_codes

    async def _fetch_all_suppliers(self, token: str) -> list[dict[str, str]]:
        loaded: list[dict[str, str]] = []
        page_number = 1
        while True:
            response = await auth_client.list_suppliers(token, page=page_number, per_page=100)
            items = response["items"]
            loaded.extend(
                self._supplier_item(item)
                for item in items
                if isinstance(item, dict) and item.get("id") is not None
            )
            if len(items) < 100:
                return loaded
            page_number += 1

    @staticmethod
    def _supplier_item(item: dict[str, Any]) -> dict[str, str]:
        tipo_documento = str(item.get("tipo_documento") or "")
        documento = str(item.get("documento") or "")
        documento_formatado = (
            _format_document(documento, tipo_documento)
            if tipo_documento in {"CPF", "CNPJ"}
            else documento
        )
        contato = str(item.get("contato") or "")
        return {
            "id": str(item.get("id") or ""),
            "nome_razao_social": str(item.get("nome_razao_social") or ""),
            "tipo_documento": tipo_documento,
            "documento": documento,
            "documento_exibicao": (
                f"{tipo_documento}: {documento_formatado}"
                if tipo_documento
                else documento_formatado
            ),
            "contato": contato,
            "contato_exibicao": _format_phone(contato),
            "endereco": str(item.get("endereco") or ""),
        }

    async def load_suppliers(self):
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        yield
        token, authenticated, permission_codes = await self._session()
        self._set_write_permissions(permission_codes)
        if not token or not authenticated:
            self._set_write_permissions([])
            self.modal_open = False
            self._clear_form()
            self.is_loading = False
            yield rx.redirect("/")
            return
        if "supplier.read" not in permission_codes:
            self._set_write_permissions([])
            self.modal_open = False
            self._clear_form()
            self.suppliers = []
            self.is_loading = False
            yield rx.redirect("/dashboard")
            return
        try:
            self.suppliers = await self._fetch_all_suppliers(token)
        except XanoAuthError:
            self.suppliers = []
            self.is_loading = False
            yield rx.redirect("/")
            return
        except XanoError:
            self.suppliers = []
            self.error_message = "Não foi possível carregar os fornecedores. Tente novamente."
        except Exception:
            self.suppliers = []
            self.error_message = "Não foi possível carregar os fornecedores. Tente novamente."
        finally:
            self.is_loading = False

    def change_search_term(self, value: str):
        self.search_term = value

    def search_suppliers(self):
        self.applied_search_term = self.search_term

    def _clear_form(self):
        self.editing_supplier_id = ""
        self.nome_razao_social = ""
        self.tipo_documento = "CNPJ"
        self.documento = ""
        self.original_documento = ""
        self.documento_dirty = False
        self.contato = ""
        self.original_contato = ""
        self.contato_dirty = False
        self.endereco = ""

    async def open_create_modal(self):
        token, authenticated, permission_codes = await self._session()
        self._set_write_permissions(permission_codes)
        if not token or not authenticated:
            yield rx.redirect("/")
            return
        if "supplier.create" not in permission_codes:
            self.modal_open = False
            self.error_message = "Você não possui permissão para cadastrar fornecedores."
            return
        self._clear_form()
        self.error_message = ""
        self.success_message = ""
        self.modal_open = True

    def close_modal(self):
        if self.create_loading or self.update_loading:
            return
        self.modal_open = False
        self._clear_form()

    def change_nome_razao_social(self, value: str):
        self.nome_razao_social = value

    def change_tipo_documento(self, value: str):
        if value not in {"CPF", "CNPJ"}:
            return
        self.tipo_documento = value
        self.documento = _format_document(self.documento, value)
        self.documento_dirty = True

    def change_documento(self, value: str):
        self.documento = _format_document(value, self.tipo_documento)
        self.documento_dirty = True

    def change_contato(self, value: str):
        self.contato = _format_phone(value)
        self.contato_dirty = True

    def change_endereco(self, value: str):
        self.endereco = value

    async def begin_edit_supplier(self, supplier_id: str):
        if self.loading_supplier_id:
            return
        token, authenticated, permission_codes = await self._session()
        self._set_write_permissions(permission_codes)
        if not token or not authenticated:
            yield rx.redirect("/")
            return
        if "supplier.update" not in permission_codes:
            self.modal_open = False
            self._clear_form()
            self.error_message = "Você não possui permissão para editar fornecedores."
            return
        self.loading_supplier_id = supplier_id
        self.error_message = ""
        self.success_message = ""
        yield
        try:
            supplier = await auth_client.get_supplier(token, int(supplier_id))
            item = self._supplier_item(supplier)
            self.editing_supplier_id = item["id"]
            self.nome_razao_social = item["nome_razao_social"]
            self.tipo_documento = item["tipo_documento"]
            self.original_documento = item["documento"]
            self.documento = _format_document(item["documento"], self.tipo_documento)
            self.documento_dirty = False
            self.original_contato = item["contato"]
            self.contato = _format_phone(item["contato"])
            self.contato_dirty = False
            self.endereco = item["endereco"]
            self.modal_open = True
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoRequestError as exc:
            self.error_message = (
                "O fornecedor não foi encontrado. Atualize a listagem."
                if exc.error_code == "NOT_FOUND"
                else "Não foi possível carregar os dados do fornecedor."
            )
        except XanoError:
            self.error_message = "Não foi possível carregar os dados do fornecedor."
        except Exception:
            self.error_message = "Não foi possível carregar os dados do fornecedor."
        finally:
            self.loading_supplier_id = ""

    async def save_supplier(self):
        if self.create_loading or self.update_loading:
            return
        editing_id = self.editing_supplier_id
        token, authenticated, permission_codes = await self._session()
        self._set_write_permissions(permission_codes)
        if not token or not authenticated:
            yield rx.redirect("/")
            return
        required_permission = "supplier.update" if editing_id else "supplier.create"
        if required_permission not in permission_codes:
            self.modal_open = False
            self._clear_form()
            self.error_message = (
                "Você não possui permissão para editar fornecedores."
                if editing_id
                else "Você não possui permissão para cadastrar fornecedores."
            )
            return

        nome = self.nome_razao_social.strip()
        tipo_documento = self.tipo_documento.strip().upper()
        documento = self.documento.strip()
        if self.editing_supplier_id and not self.documento_dirty:
            documento = self.original_documento.strip()
        contato = self.contato
        if self.editing_supplier_id and not self.contato_dirty:
            contato = self.original_contato
        if not nome:
            self.error_message = "Informe o nome ou a razão social do fornecedor."
            return
        if tipo_documento not in {"CPF", "CNPJ"}:
            self.error_message = "Selecione CPF ou CNPJ."
            return
        if not documento:
            self.error_message = "Informe o documento do fornecedor."
            return

        self.create_loading = not bool(editing_id)
        self.update_loading = bool(editing_id)
        self.error_message = ""
        self.success_message = ""
        yield
        try:
            if editing_id:
                await auth_client.update_supplier(
                    token,
                    int(editing_id),
                    nome_razao_social=nome,
                    tipo_documento=tipo_documento,
                    documento=documento,
                    contato=contato,
                    endereco=self.endereco,
                )
                success = "Fornecedor atualizado com sucesso."
            else:
                await auth_client.create_supplier(
                    token,
                    nome_razao_social=nome,
                    tipo_documento=tipo_documento,
                    documento=documento,
                    contato=contato,
                    endereco=self.endereco,
                )
                success = "Fornecedor cadastrado com sucesso."

            self.modal_open = False
            self._clear_form()
            self.success_message = success
            try:
                self.suppliers = await self._fetch_all_suppliers(token)
            except Exception:
                self.error_message = "O fornecedor foi salvo, mas não foi possível atualizar a listagem."
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoRequestError as exc:
            self.error_message = self._write_error_message(exc)
        except XanoError:
            self.error_message = (
                "Não foi possível atualizar o fornecedor."
                if editing_id
                else "Não foi possível cadastrar o fornecedor."
            )
        except Exception:
            self.error_message = (
                "Não foi possível atualizar o fornecedor."
                if editing_id
                else "Não foi possível cadastrar o fornecedor."
            )
        finally:
            self.create_loading = False
            self.update_loading = False

    @staticmethod
    def _write_error_message(exc: XanoRequestError) -> str:
        if exc.error_code == "DUPLICATE_VALUE":
            return "Já existe um fornecedor com esse documento."
        if exc.error_code == "INVALID_INPUT":
            return "Confira o nome, o tipo e o documento informados."
        if exc.error_code == "PERMISSION_DENIED":
            return "Você não possui permissão para alterar fornecedores."
        if exc.error_code == "NOT_FOUND":
            return "O fornecedor não foi encontrado. Atualize a listagem."
        return "Não foi possível salvar o fornecedor."


SUPPLIER_GRID_COLUMNS = "60px minmax(260px, 1.8fr) minmax(220px, 1.3fr) minmax(180px, 1.1fr) 110px"


def _supplier_row(item: dict[str, str]) -> rx.Component:
    return rx.grid(
        rx.text(item["id"], padding_x="0.5rem"),
        rx.text(item["nome_razao_social"], padding_x="0.5rem"),
        rx.text(item["documento_exibicao"], padding_x="0.5rem"),
        rx.cond(
            item["contato_exibicao"] != "",
            rx.text(item["contato_exibicao"], padding_x="0.5rem"),
            rx.text("—", padding_x="0.5rem"),
        ),
        rx.box(
            rx.cond(
                SupplierState.can_update_suppliers,
                rx.button(
                    rx.cond(
                        SupplierState.loading_supplier_id == item["id"],
                        rx.spinner(),
                        "Editar",
                    ),
                    on_click=SupplierState.begin_edit_supplier(item["id"]),
                    variant="soft",
                    disabled=SupplierState.loading_supplier_id != "",
                    width="90px",
                ),
                rx.fragment(),
            ),
            display="flex",
            justify_content="center",
            align_items="center",
            width="100%",
        ),
        columns="5",
        width="100%",
        column_gap="12px",
        style={"grid_template_columns": SUPPLIER_GRID_COLUMNS, "align_items": "center"},
        padding_y="0.75rem",
        padding_x="8px",
        border_bottom="1px solid #e5e7eb",
    )


def _supplier_table() -> rx.Component:
    header = rx.grid(
        rx.text("ID", weight="bold", padding_x="0.5rem"),
        rx.text("Nome / Razão social", weight="bold", padding_x="0.5rem"),
        rx.text("Documento", weight="bold", padding_x="0.5rem"),
        rx.text("Contato", weight="bold", padding_x="0.5rem"),
        rx.text("Ações", weight="bold", width="100%", text_align="center"),
        columns="5",
        width="100%",
        column_gap="12px",
        style={"grid_template_columns": SUPPLIER_GRID_COLUMNS, "align_items": "center"},
        padding_y="0.75rem",
        padding_x="8px",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(SupplierState.filtered_suppliers, _supplier_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
        border_radius="0.4rem",
    )


def _supplier_modal() -> rx.Component:
    return rx.cond(
        SupplierState.modal_open & SupplierState.can_access_supplier_form,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            rx.cond(SupplierState.is_editing, "Editar fornecedor", "Novo fornecedor"),
                            size="5",
                        ),
                        rx.spacer(),
                        rx.button("×", on_click=SupplierState.close_modal, variant="ghost", disabled=SupplierState.is_saving),
                        width="100%",
                        align="center",
                    ),
                    rx.vstack(
                        rx.text("Nome / Razão social"),
                        rx.input(
                            value=SupplierState.nome_razao_social,
                            on_change=SupplierState.change_nome_razao_social,
                            placeholder="Nome ou razão social",
                            disabled=SupplierState.is_saving,
                            width="100%",
                        ),
                        align="stretch",
                        spacing="1",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Tipo de documento"),
                            rx.select(
                                ["CNPJ", "CPF"],
                                value=SupplierState.tipo_documento,
                                on_change=SupplierState.change_tipo_documento,
                                disabled=SupplierState.is_saving,
                                width="100%",
                            ),
                            align="stretch",
                            spacing="1",
                            width="35%",
                        ),
                        rx.vstack(
                            rx.text("Documento"),
                            rx.input(
                                value=SupplierState.documento,
                                on_change=SupplierState.change_documento,
                                placeholder="CPF ou CNPJ",
                                disabled=SupplierState.is_saving,
                                width="100%",
                            ),
                            align="stretch",
                            spacing="1",
                            width="65%",
                        ),
                        width="100%",
                        align="end",
                        wrap="wrap",
                        spacing="3",
                    ),
                    rx.vstack(
                        rx.text("Contato (opcional)"),
                        rx.input(
                            value=SupplierState.contato,
                            on_change=SupplierState.change_contato,
                            placeholder="Telefone ou contato",
                            disabled=SupplierState.is_saving,
                            width="100%",
                        ),
                        align="stretch",
                        spacing="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Endereço (opcional)"),
                        rx.input(
                            value=SupplierState.endereco,
                            on_change=SupplierState.change_endereco,
                            placeholder="Endereço",
                            disabled=SupplierState.is_saving,
                            width="100%",
                        ),
                        align="stretch",
                        spacing="1",
                        width="100%",
                    ),
                    rx.cond(
                        SupplierState.error_message != "",
                        rx.text(SupplierState.error_message, color="#b91c1c"),
                    ),
                    rx.hstack(
                        rx.spacer(),
                        rx.button("Cancelar", on_click=SupplierState.close_modal, variant="soft", disabled=SupplierState.is_saving),
                        rx.button(
                            rx.cond(SupplierState.is_saving, rx.spinner(), "Salvar"),
                            on_click=SupplierState.save_supplier,
                            disabled=SupplierState.is_saving,
                        ),
                        width="100%",
                        justify="end",
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
                width="100%",
                max_width="36rem",
                padding="1.5rem",
                background="white",
                border_radius="0.75rem",
                box_shadow="0 20px 40px rgba(15, 23, 42, 0.2)",
            ),
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            z_index="2000",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1rem",
            background="rgba(15, 23, 42, 0.45)",
        ),
    )


def fornecedores() -> rx.Component:
    return page(
        "Fornecedores",
        rx.vstack(
            rx.hstack(
                rx.input(
                    value=SupplierState.search_term,
                    on_change=SupplierState.change_search_term,
                    placeholder="Buscar fornecedor...",
                    width="min(24rem, 100%)",
                ),
                rx.button("Buscar", on_click=SupplierState.search_suppliers),
                rx.spacer(),
                rx.cond(
                    SupplierState.can_create_suppliers,
                    rx.button("Novo fornecedor", on_click=SupplierState.open_create_modal),
                    rx.fragment(),
                ),
                width="100%",
                wrap="wrap",
                align="center",
                spacing="3",
            ),
            rx.cond(SupplierState.success_message != "", rx.text(SupplierState.success_message, color="#15803d")),
            rx.cond(SupplierState.error_message != "", rx.text(SupplierState.error_message, color="#b91c1c")),
            section(
                "Fornecedores cadastrados",
                rx.cond(
                    SupplierState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando fornecedores..."), width="100%", padding="2rem"),
                    rx.cond(
                        SupplierState.error_message != "",
                        rx.fragment(),
                        rx.cond(
                            SupplierState.filtered_suppliers.length() > 0,
                            _supplier_table(),
                            rx.cond(
                                SupplierState.suppliers.length() > 0,
                                rx.text("Nenhum fornecedor encontrado para a busca."),
                                rx.text("Nenhum fornecedor cadastrado."),
                            ),
                        ),
                    ),
                ),
            ),
            _supplier_modal(),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
