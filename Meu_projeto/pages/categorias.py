import reflex as rx

from ..components.layout import page, section
from ..components.searchable_select import normalize_search_text
from ..services.xano_client import (
    XanoAuthError,
    XanoError,
    XanoRequestError,
    auth_client,
)
from ..state import AuthState


class CategoryState(rx.State):
    """Carregamento e gerenciamento de Categorias reais do Xano."""

    categories: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    search_term: str = ""
    applied_search_term: str = ""

    modal_open: bool = False
    new_category_name: str = ""
    create_loading: bool = False
    can_manage_categories: bool = False

    status_loading_category_id: str = ""

    @rx.var
    def filtered_categories(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.applied_search_term)
        if not query:
            return self.categories
        return [
            category
            for category in self.categories
            if query in normalize_search_text(category.get("nome", ""))
        ]

    def load_page(self):
        return [AuthState.require_auth(), CategoryState.load_categories()]

    async def _session(self) -> tuple[str, int | None, bool]:
        auth_state = await self.get_state(AuthState)
        return (
            str(auth_state.auth_token or "").strip(),
            auth_state.inventory_profile_id,
            auth_state.is_authenticated,
        )

    async def _fetch_all_categories(self, token: str) -> list[dict[str, str]]:
        loaded: list[dict[str, str]] = []
        page = 1
        while True:
            response = await auth_client.list_categories(token, page=page, per_page=100)
            items = response["items"]
            loaded.extend(
                {
                    "id": str(item["id"]),
                    "nome": str(item.get("nome") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in items
                if isinstance(item, dict) and item.get("id") is not None
            )
            if len(items) < 100:
                return loaded
            page += 1

    async def load_categories(self):
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        yield
        token, profile_id, authenticated = await self._session()
        self.can_manage_categories = profile_id == 1
        if not token or not authenticated:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            self.categories = await self._fetch_all_categories(token)
        except XanoAuthError:
            self.categories = []
            self.is_loading = False
            yield rx.redirect("/")
            return
        except XanoError:
            self.categories = []
            self.error_message = "Não foi possível carregar as categorias. Tente novamente."
        except Exception:
            self.categories = []
            self.error_message = "Não foi possível carregar as categorias. Tente novamente."
        finally:
            self.is_loading = False

    def change_search_term(self, value: str):
        self.search_term = value

    def set_new_category_name(self, value: str):
        self.new_category_name = value

    def search_categories(self):
        self.applied_search_term = self.search_term

    def open_create_modal(self):
        if not self.can_manage_categories:
            return
        self.error_message = ""
        self.success_message = ""
        self.new_category_name = ""
        self.modal_open = True

    def close_create_modal(self):
        if self.create_loading:
            return
        self.modal_open = False
        self.new_category_name = ""

    async def create_category(self):
        if self.create_loading:
            return
        if not self.can_manage_categories:
            self.error_message = "Você não possui permissão para criar categorias."
            return
        nome = self.new_category_name.strip()
        if not nome:
            self.error_message = "Informe o nome da categoria."
            return
        token, _, authenticated = await self._session()
        if not token or not authenticated:
            yield rx.redirect("/")
            return

        self.create_loading = True
        self.error_message = ""
        self.success_message = ""
        yield
        try:
            await auth_client.create_category(token, nome=nome)
            self.modal_open = False
            self.new_category_name = ""
            self.success_message = "Categoria criada com sucesso."
            try:
                self.categories = await self._fetch_all_categories(token)
            except Exception:
                self.error_message = "A categoria foi criada, mas não foi possível atualizar a listagem."
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoRequestError as exc:
            if exc.error_code == "DUPLICATE_VALUE":
                self.error_message = "Já existe uma categoria com esse nome."
            elif exc.error_code == "INVALID_INPUT":
                self.error_message = "Informe o nome da categoria."
            elif exc.error_code == "PERMISSION_DENIED":
                self.error_message = "Você não possui permissão para criar categorias."
            else:
                self.error_message = "Não foi possível criar a categoria."
        except XanoError:
            self.error_message = "Não foi possível criar a categoria."
        except Exception:
            self.error_message = "Não foi possível criar a categoria."
        finally:
            self.create_loading = False

    async def change_category_status(self, category_id: str, active: bool):
        if self.status_loading_category_id:
            return
        if not self.can_manage_categories:
            self.error_message = "Você não possui permissão para alterar categorias."
            return
        category = next((item for item in self.categories if item["id"] == category_id), None)
        if category is None:
            return
        token, _, authenticated = await self._session()
        if not token or not authenticated:
            yield rx.redirect("/")
            return

        self.status_loading_category_id = category_id
        self.error_message = ""
        self.success_message = ""
        yield
        try:
            category_id_int = int(category_id)
            if active:
                updated = await auth_client.activate_category(token, category_id_int)
            else:
                updated = await auth_client.inactivate_category(token, category_id_int)

            confirmed_status = str(updated.get("status") or "")
            if confirmed_status not in {"ativo", "inativo"}:
                self.categories = await self._fetch_all_categories(token)
            else:
                self.categories = [
                    {**item, "status": confirmed_status} if item["id"] == category_id else item
                    for item in self.categories
                ]
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoRequestError as exc:
            if exc.error_code == "PERMISSION_DENIED":
                self.error_message = "Você não possui permissão para alterar categorias."
            elif exc.error_code == "NOT_FOUND":
                self.error_message = "A categoria não foi encontrada. Atualize a listagem."
            else:
                self.error_message = "Não foi possível atualizar o status da categoria."
        except XanoError:
            self.error_message = "Não foi possível atualizar o status da categoria."
        except Exception:
            self.error_message = "Não foi possível atualizar o status da categoria."
        finally:
            self.status_loading_category_id = ""


CATEGORY_GRID_COLUMNS = "72px minmax(220px, 1fr) 130px 150px"


def _category_row(category: dict[str, str]) -> rx.Component:
    return rx.grid(
        rx.text(category["id"], padding_x="0.5rem"),
        rx.text(category["nome"], padding_x="0.5rem"),
        rx.cond(
            category["status"] == "ativo",
            rx.badge("Ativa", color_scheme="green"),
            rx.cond(
                category["status"] == "inativo",
                rx.badge("Inativa", color_scheme="gray"),
                rx.badge("Status indisponível", color_scheme="gray"),
            ),
        ),
        rx.switch(
            checked=category["status"] == "ativo",
            on_change=CategoryState.change_category_status(category["id"]),
            disabled=(
                (CategoryState.can_manage_categories == False)
                | (CategoryState.status_loading_category_id != "")
                | ((category["status"] != "ativo") & (category["status"] != "inativo"))
            ),
        ),
        columns="4",
        width="100%",
        column_gap="1rem",
        style={"grid_template_columns": CATEGORY_GRID_COLUMNS, "align_items": "center"},
        padding_y="0.75rem",
        border_bottom="1px solid #e5e7eb",
    )


def _category_table() -> rx.Component:
    header = rx.grid(
        rx.text("ID", weight="bold", padding_x="0.5rem"),
        rx.text("Nome", weight="bold", padding_x="0.5rem"),
        rx.text("Status", weight="bold"),
        rx.text("Ativar/Inativar", weight="bold"),
        columns="4",
        width="100%",
        column_gap="1rem",
        style={"grid_template_columns": CATEGORY_GRID_COLUMNS, "align_items": "center"},
        padding="0.75rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(
            rx.foreach(CategoryState.filtered_categories, _category_row),
            width="100%",
            spacing="0",
        ),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
        border_radius="0.4rem",
    )


def _create_category_modal() -> rx.Component:
    return rx.cond(
        CategoryState.modal_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Nova categoria", size="5"),
                        rx.spacer(),
                        rx.button("×", on_click=CategoryState.close_create_modal, variant="ghost", disabled=CategoryState.create_loading),
                        width="100%",
                        align="center",
                    ),
                    rx.text("Nome da categoria"),
                    rx.input(
                        value=CategoryState.new_category_name,
                        on_change=CategoryState.set_new_category_name,
                        placeholder="Ex.: Materiais de escritório",
                        auto_focus=True,
                        disabled=CategoryState.create_loading,
                        width="100%",
                    ),
                    rx.cond(
                        CategoryState.error_message != "",
                        rx.text(CategoryState.error_message, color="#b91c1c"),
                    ),
                    rx.hstack(
                        rx.spacer(),
                        rx.button("Cancelar", on_click=CategoryState.close_create_modal, variant="soft", disabled=CategoryState.create_loading),
                        rx.button(
                            rx.cond(CategoryState.create_loading, rx.spinner(), "Salvar"),
                            on_click=CategoryState.create_category,
                            disabled=CategoryState.create_loading,
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
                max_width="30rem",
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


def categorias() -> rx.Component:
    return page(
        "Categorias",
        rx.vstack(
            rx.hstack(
                rx.input(
                    value=CategoryState.search_term,
                    on_change=CategoryState.change_search_term,
                    placeholder="Nome da categoria...",
                    width="min(24rem, 100%)",
                ),
                rx.button("Buscar", on_click=CategoryState.search_categories),
                rx.spacer(),
                rx.cond(
                    CategoryState.can_manage_categories,
                    rx.button("Nova categoria", on_click=CategoryState.open_create_modal),
                    rx.fragment(),
                ),
                width="100%",
                wrap="wrap",
                align="center",
                spacing="3",
            ),
            rx.cond(
                CategoryState.success_message != "",
                rx.text(CategoryState.success_message, color="#15803d"),
            ),
            rx.cond(
                CategoryState.error_message != "",
                rx.text(CategoryState.error_message, color="#b91c1c"),
            ),
            section(
                "Categorias cadastradas",
                rx.cond(
                    CategoryState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando categorias..."), width="100%", padding="2rem"),
                    rx.cond(
                        CategoryState.error_message != "",
                        rx.fragment(),
                        rx.cond(
                            CategoryState.filtered_categories.length() > 0,
                            _category_table(),
                            rx.cond(
                                CategoryState.categories.length() > 0,
                                rx.text("Nenhuma categoria encontrada para a busca."),
                                rx.text("Nenhuma categoria cadastrada."),
                            ),
                        ),
                    ),
                ),
            ),
            _create_category_modal(),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
