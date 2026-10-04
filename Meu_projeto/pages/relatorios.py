"""RelatÃ³rio operacional de movimentaÃ§Ãµes de estoque."""

import asyncio
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import reflex as rx

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
from ..state import AuthState


class ReportState(rx.State):
    movements: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
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

    product_options: list[dict[str, str]] = [{"id": "", "label": "Todos os produtos"}]
    product_query: str = "Todos os produtos"
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False

    supplier_options: list[dict[str, str]] = [{"id": "", "label": "Todos os fornecedores"}]
    supplier_query: str = "Todos os fornecedores"
    supplier_options_open: bool = False
    supplier_page: int = 1
    supplier_has_more: bool = False
    supplier_loading_more: bool = False

    movement_total: int = 0
    entry_quantity_total: str = "0"
    exit_quantity_total: str = "0"
    stock_below_minimum: int = 0
    stock_no_stock: int = 0

    @rx.var
    def filtered_product_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.product_query)
        if not query or query == normalize_search_text("Todos os produtos"):
            return self.product_options
        return [
            item for item in self.product_options
            if query in normalize_search_text(item.get("label", ""))
        ]

    @rx.var
    def filtered_supplier_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.supplier_query)
        if not query or query == normalize_search_text("Todos os fornecedores"):
            return self.supplier_options
        return [
            item for item in self.supplier_options
            if query in normalize_search_text(item.get("label", ""))
        ]

    def load_page(self):
        self.start_date = ""
        self.end_date = ""
        self.filter_type = ""
        self.filter_product_id = ""
        self.filter_supplier_id = ""
        self.product_query = "Todos os produtos"
        self.supplier_query = "Todos os fornecedores"
        return [AuthState.require_auth(), ReportState.load_initial()]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
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
        self.movements = []
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            await asyncio.gather(
                self._load_products(token),
                self._load_suppliers(token),
            )
            await self._load_report_data(token, 1)
        except XanoAuthError:
            self.error_message = "Sua sessÃ£o expirou. FaÃ§a login novamente."
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        except XanoRequestError as exc:
            self.error_message = self._request_error_message(exc)
        except (XanoConnectionError, XanoServerError, XanoError):
            self.error_message = "NÃ£o foi possÃ­vel carregar os relatÃ³rios. Tente novamente."
        except Exception:
            self.error_message = "NÃ£o foi possÃ­vel carregar os relatÃ³rios. Tente novamente."
        finally:
            self.is_loading = False

    async def _load_products(self, token: str):
        response = await auth_client.list_products(token, page=1, per_page=100)
        self.product_options = [{"id": "", "label": "Todos os produtos"}]
        self.product_options.extend(
            self._product_option(item)
            for item in response["items"]
            if isinstance(item, dict) and item.get("id") is not None
        )
        self.product_page = 1
        self.product_has_more = len(response["items"]) == 100

    async def _load_suppliers(self, token: str):
        response = await auth_client.list_suppliers(token, page=1, per_page=100)
        self.supplier_options = [{"id": "", "label": "Todos os fornecedores"}]
        self.supplier_options.extend(
            self._supplier_option(item)
            for item in response["items"]
            if isinstance(item, dict) and item.get("id") is not None
        )
        self.supplier_page = 1
        self.supplier_has_more = len(response["items"]) == 100

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
            self.error_message = "NÃ£o foi possÃ­vel carregar mais Produtos."
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
            response = await auth_client.list_suppliers(token, page=page, per_page=100)
            known = {item["id"] for item in self.supplier_options}
            self.supplier_options.extend(
                self._supplier_option(item)
                for item in response["items"]
                if isinstance(item, dict)
                and item.get("id") is not None
                and str(item["id"]) not in known
            )
            self.supplier_page = page
            self.supplier_has_more = len(response["items"]) == 100
        except XanoAuthError:
            return rx.redirect("/")
        except XanoError:
            self.error_message = "NÃ£o foi possÃ­vel carregar mais Fornecedores."
        finally:
            self.supplier_loading_more = False

    def search_products(self, value: str):
        self.product_query = value
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

    def select_product(self, product_id: str):
        self.filter_product_id = str(product_id or "")
        option = next((item for item in self.product_options if item["id"] == self.filter_product_id), None)
        self.product_query = option["label"] if option else "Todos os produtos"
        self.product_options_open = False

    def search_suppliers(self, value: str):
        self.supplier_query = value
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

    def select_supplier(self, supplier_id: str):
        self.filter_supplier_id = str(supplier_id or "")
        option = next((item for item in self.supplier_options if item["id"] == self.filter_supplier_id), None)
        self.supplier_query = option["label"] if option else "Todos os fornecedores"
        self.supplier_options_open = False

    @staticmethod
    def _date_boundary(value: str, *, end_of_day: bool) -> int | None:
        if not value.strip():
            return None
        parsed = datetime.strptime(value, "%Y-%m-%d")
        local_offset = timezone(timedelta(hours=-3))
        if end_of_day:
            parsed = parsed + timedelta(days=1) - timedelta(milliseconds=1)
        return int(parsed.replace(tzinfo=local_offset).timestamp() * 1000)

    def change_start_date(self, value: str):
        self.start_date = value

    def change_end_date(self, value: str):
        self.end_date = value

    def change_type(self, value: str):
        self.filter_type = value if value in {"entrada", "saida"} else ""

    @staticmethod
    def _request_error_message(exc: XanoRequestError) -> str:
        if exc.error_code == "PERMISSION_DENIED":
            return "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        if exc.error_code in {"INVALID_INPUT", "ERROR_CODE_INPUT_ERROR"}:
            return "Os filtros informados sÃ£o invÃ¡lidos. Confira as datas selecionadas."
        return "NÃ£o foi possÃ­vel carregar os relatÃ³rios. Tente novamente."

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
            return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
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

    async def _load_report_data(self, token: str, page: int):
        try:
            from_ms = self._date_boundary(self.start_date, end_of_day=False)
            to_ms = self._date_boundary(self.end_date, end_of_day=True)
        except ValueError:
            self.error_message = "Informe datas vÃ¡lidas para o perÃ­odo."
            return
        if from_ms is not None and to_ms is not None and from_ms > to_ms:
            self.error_message = "A data inicial deve ser anterior ou igual Ã  data final."
            return

        product_id = int(self.filter_product_id) if self.filter_product_id.isdigit() and int(self.filter_product_id) > 0 else None
        supplier_id = int(self.filter_supplier_id) if self.filter_supplier_id.isdigit() and int(self.filter_supplier_id) > 0 else None
        tipo = self.filter_type or None

        summary, stock_summary, movements = await asyncio.gather(
            auth_client.get_movements_summary(
                token,
                date_from=from_ms,
                date_to=to_ms,
                product_id=product_id,
                supplier_id=supplier_id,
            ),
            auth_client.get_stock_summary(token),
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
        self.movement_total = summary["total_movimentacoes"]
        self.entry_quantity_total = self._format_quantity(summary["quantidade_entradas"])
        self.exit_quantity_total = self._format_quantity(summary["quantidade_saidas"])
        self.stock_below_minimum = stock_summary["abaixo_minimo"]
        self.stock_no_stock = stock_summary["sem_estoque"]
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

    async def apply_filters(self):
        self.current_page = 1
        return ReportState.load_report(1)

    async def clear_filters(self):
        self.start_date = ""
        self.end_date = ""
        self.filter_type = ""
        self.filter_product_id = ""
        self.filter_supplier_id = ""
        self.product_query = "Todos os produtos"
        self.supplier_query = "Todos os fornecedores"
        self.current_page = 1
        return ReportState.load_report(1)

    async def load_report(self, page: int = 1):
        self.is_loading = True
        self.error_message = ""
        self.movements = []
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            await self._load_report_data(token, page)
        except XanoAuthError:
            self.error_message = "Sua sessÃ£o expirou. FaÃ§a login novamente."
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        except XanoRequestError as exc:
            self.error_message = self._request_error_message(exc)
        except (XanoConnectionError, XanoServerError, XanoError):
            self.error_message = "NÃ£o foi possÃ­vel carregar os relatÃ³rios. Tente novamente."
        except Exception:
            self.error_message = "NÃ£o foi possÃ­vel carregar os relatÃ³rios. Tente novamente."
        finally:
            self.is_loading = False

    def load_previous_page(self):
        if self.prev_page is not None:
            return ReportState.load_report(self.prev_page)

    def load_next_page(self):
        if self.next_page is not None:
            return ReportState.load_report(self.next_page)


def _report_card(title: str, value: rx.Var) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, color="#64748b", size="2"),
            rx.heading(value, size="6"),
            align="start",
            spacing="1",
        ),
        flex="1",
        min_width="170px",
        padding="1rem",
        border="1px solid #e2e8f0",
        border_radius="0.5rem",
        background="white",
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
        border_bottom="1px solid #eee",
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
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(ReportState.movements, _report_movement_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
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
                        rx.vstack(rx.text("Data inicial"), rx.input(type="date", value=ReportState.start_date, on_change=ReportState.change_start_date), width="100%", align="stretch", spacing="1"),
                        rx.vstack(rx.text("Data final"), rx.input(type="date", value=ReportState.end_date, on_change=ReportState.change_end_date), width="100%", align="stretch", spacing="1"),
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
                            width="100%", align="stretch", spacing="1",
                        ),
                        width="100%", wrap="wrap", align="end", spacing="3",
                    ),
                    rx.hstack(
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
                            ),
                            width="100%", align="stretch", spacing="1",
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
                            ),
                            width="100%", align="stretch", spacing="1",
                        ),
                        width="100%", wrap="wrap", align="end", spacing="3",
                    ),
                    rx.hstack(
                        rx.button("Aplicar filtros", on_click=ReportState.apply_filters, disabled=ReportState.is_loading),
                        rx.button("Limpar", on_click=ReportState.clear_filters, variant="soft", disabled=ReportState.is_loading),
                        width="100%", justify="end",
                    ),
                    width="100%", align="stretch", spacing="3",
                ),
            ),
            rx.cond(ReportState.error_message != "", rx.text(ReportState.error_message, color="#b91c1c")),
            rx.flex(
                _report_card("Movimentações", ReportState.movement_total),
                _report_card("Entradas (unidades)", ReportState.entry_quantity_total),
                _report_card("Saídas (unidades)", ReportState.exit_quantity_total),
                _report_card("Abaixo do mínimo", ReportState.stock_below_minimum),
                _report_card("Sem estoque", ReportState.stock_no_stock),
                width="100%", wrap="wrap", gap="4",
            ),
            section(
                "Movimentações no período",
                rx.cond(
                    ReportState.is_loading,
                    rx.center(rx.spinner(), "Carregando relatório...", width="100%", padding="2rem"),
                    rx.cond(
                        ReportState.error_message != "",
                        rx.fragment(),
                        rx.cond(
                            ReportState.movements.length() > 0,
                            _report_table(),
                            rx.text("Nenhuma movimentação encontrada para os filtros selecionados.", color="#64748b", padding="1rem"),
                        ),
                    ),
                ),
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
