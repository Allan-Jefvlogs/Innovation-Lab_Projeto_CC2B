"""Consulta dos saldos de estoque reais e listas por situação."""

from typing import Any, Optional
from decimal import Decimal, InvalidOperation

import reflex as rx

from ..components.layout import page, section
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


STOCK_SITUATIONS = {
    "normal": {"label": "Normal", "title": "Estoque — Normal"},
    "abaixo_minimo": {"label": "Abaixo do mínimo", "title": "Estoque — Abaixo do mínimo"},
    "sem_estoque": {"label": "Sem estoque", "title": "Estoque — Sem estoque"},
}


class StockState(rx.State):
    """Carrega o resumo e páginas de saldos autorizados pelo Xano."""

    rows: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    selected_situation: str = ""
    search_term: str = ""
    current_page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 1
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
    summary_total: int = 0
    summary_normal: int = 0
    summary_below_minimum: int = 0
    summary_no_stock: int = 0

    def load_page(self):
        self.selected_situation = ""
        self.search_term = ""
        return [AuthState.require_auth(), StockState.load_stock(1)]

    async def _session_token(self) -> str:
        auth_state = await self.get_state(AuthState)
        if not auth_state.is_authenticated or not auth_state.has_permission("stock.read"):
            return ""
        return str(auth_state.auth_token or "").strip()

    @staticmethod
    def _map_stock_row(item: dict[str, Any]) -> dict[str, str]:
        situation = str(item.get("situacao_estoque") or "")
        return {
            "product_id": str(item.get("product_id") or ""),
            "codigo": str(item.get("codigo") or "—"),
            "nome": str(item.get("nome") or "Produto não encontrado"),
            "categoria": str(item.get("categoria_nome") or "Sem categoria"),
            "fornecedor": str(item.get("fornecedor_nome") or "Sem fornecedor"),
            "atual": StockState._format_quantity(item.get("quantidade_disponivel")),
            "minimo": StockState._format_quantity(item.get("estoque_minimo")),
            "situacao": situation,
            "situacao_label": STOCK_SITUATIONS.get(situation, {}).get("label", "Desconhecida"),
        }

    @staticmethod
    def _format_quantity(value: object) -> str:
        try:
            number = Decimal(str(value))
            if not number.is_finite():
                return "—"
            return format(number.normalize(), "f").replace(".", ",")
        except (InvalidOperation, TypeError, ValueError):
            return "—"

    async def load_stock(self, page_number: int = 1):
        self.is_loading = True
        self.error_message = ""
        self.rows = []
        yield

        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return

        try:
            if page_number == 1:
                summary = await auth_client.get_stock_summary(token)
                self.summary_total = summary["total"]
                self.summary_normal = summary["normal"]
                self.summary_below_minimum = summary["abaixo_minimo"]
                self.summary_no_stock = summary["sem_estoque"]
            response = await auth_client.list_stock(
                token,
                page=page_number,
                per_page=self.per_page,
                situacao=self.selected_situation or None,
                search=self.search_term.strip() or None,
            )
            self.rows = [
                self._map_stock_row(item)
                for item in response["items"]
                if isinstance(item, dict)
            ]
            self.current_page = int(response.get("curPage") or page_number)
            self.total_items = int(response.get("itemsTotal") or 0)
            self.total_pages = max(1, int(response.get("pageTotal") or 0))
            self.next_page = int(response["nextPage"]) if response.get("nextPage") is not None else None
            self.prev_page = int(response["prevPage"]) if response.get("prevPage") is not None else None
        except XanoAuthError as exc:
            self.error_message = exc.message
            self.is_loading = False
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para visualizar o estoque."
        except XanoRequestError as exc:
            self.error_message = (
                "Você não possui permissão para visualizar o estoque."
                if exc.error_code == "PERMISSION_DENIED"
                else "Não foi possível carregar o estoque. Tente novamente."
            )
        except (XanoConnectionError, XanoServerError, XanoError):
            self.error_message = "Não foi possível carregar o estoque. Tente novamente."
        except Exception:
            self.error_message = "Não foi possível carregar o estoque. Tente novamente."
        finally:
            self.is_loading = False

    def set_search(self, value: str):
        self.search_term = value

    def search_stock(self):
        self.current_page = 1
        return StockState.load_stock(1)

    def clear_search(self):
        self.search_term = ""
        self.current_page = 1
        return StockState.load_stock(1)

    def select_situation(self, situation: str):
        if situation == "":
            self.selected_situation = ""
        elif situation in {"abaixo_minimo", "sem_estoque"}:
            self.selected_situation = "" if self.selected_situation == situation else situation
        else:
            return
        self.current_page = 1
        return StockState.load_stock(1)

    def load_previous_page(self):
        if self.prev_page is not None:
            return StockState.load_stock(self.prev_page)

    def load_next_page(self):
        if self.next_page is not None:
            return StockState.load_stock(self.next_page)


def _stock_status_badge(row: dict[str, str]) -> rx.Component:
    color = rx.match(
        row["situacao"],
        ("normal", "#15803d"),
        ("abaixo_minimo", "#b45309"),
        ("sem_estoque", "#b91c1c"),
        "#64748b",
    )
    background = rx.match(
        row["situacao"],
        ("normal", "#dcfce7"),
        ("abaixo_minimo", "#fef3c7"),
        ("sem_estoque", "#fee2e2"),
        "#f1f5f9",
    )
    return rx.badge(row["situacao_label"], color=color, background=background)


STOCK_GRID = "120px minmax(220px, 1.35fr) minmax(150px, 0.9fr) minmax(190px, 1.15fr) 82px 82px 145px"


def _stock_row(row: dict[str, str]) -> rx.Component:
    return rx.grid(
        rx.text(row["codigo"], padding_x="8px"),
        rx.text(row["nome"], padding_x="8px"),
        rx.text(row["categoria"], padding_x="8px"),
        rx.text(row["fornecedor"], padding_x="8px"),
        rx.text(row["atual"], padding_x="8px"),
        rx.text(row["minimo"], padding_x="8px"),
        rx.box(_stock_status_badge(row), padding_x="8px"),
        columns="7",
        width="100%",
        column_gap="12px",
        style={"grid_template_columns": STOCK_GRID, "align_items": "center"},
        padding_y="0.8rem",
        border_bottom="1px solid #eee",
    )


def _stock_table() -> rx.Component:
    header = rx.grid(
        *[
            rx.text(title, weight="bold", padding_x="8px")
            for title in ["Código", "Produto", "Categoria", "Fornecedor", "Atual", "Mínimo", "Situação"]
        ],
        columns="7",
        width="100%",
        column_gap="12px",
        style={"grid_template_columns": STOCK_GRID, "align_items": "center"},
        padding_y="0.8rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )
    return rx.box(
        header,
        rx.vstack(rx.foreach(StockState.rows, _stock_row), width="100%", spacing="0"),
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
        border_radius="0.4rem",
    )


def _status_card(title: str, count: rx.Var, situation: str, color: str) -> rx.Component:
    is_selected = StockState.selected_situation == situation
    return rx.box(
        rx.vstack(
            rx.text(title, color="#666", size="2"),
            rx.heading(count, size="7", color=color),
            align="start",
            spacing="1",
        ),
        border=rx.cond(is_selected, "2px solid", "1px solid #ddd"),
        border_color=rx.cond(is_selected, color, "#ddd"),
        background=rx.cond(is_selected, "#f8fafc", "white"),
        border_radius="0.5rem",
        padding="1.25rem",
        flex="1",
        min_width="180px",
        cursor="pointer",
        transition="box-shadow 120ms ease, border-color 120ms ease",
        _hover={"box_shadow": "0 2px 8px rgba(15, 23, 42, 0.12)", "border_color": color},
        on_click=StockState.select_situation(situation),
        role="button",
        tab_index=0,
    )


def _pagination() -> rx.Component:
    return rx.hstack(
        rx.button("Anterior", on_click=StockState.load_previous_page, disabled=StockState.prev_page == None),
        rx.text("Página ", StockState.current_page, " de ", StockState.total_pages, " · ", StockState.total_items, " produtos"),
        rx.button("Próxima", on_click=StockState.load_next_page, disabled=StockState.next_page == None),
        width="100%",
        justify="between",
        align="center",
    )


def estoque() -> rx.Component:
    return page(
        "Estoque",
        rx.vstack(
            rx.hstack(
                _status_card("Produtos cadastrados", StockState.summary_total, "", "#1f2937"),
                _status_card("Abaixo do mínimo", StockState.summary_below_minimum, "abaixo_minimo", "#b45309"),
                _status_card("Sem estoque", StockState.summary_no_stock, "sem_estoque", "#b91c1c"),
                width="100%",
                wrap="wrap",
                spacing="4",
            ),
            section(
                "Estoque atual",
                rx.vstack(
                    rx.hstack(
                        rx.input(
                            value=StockState.search_term,
                            on_change=StockState.set_search,
                            placeholder="Buscar produto por código ou nome...",
                            width="100%",
                            max_width="520px",
                        ),
                        rx.button("Buscar", on_click=StockState.search_stock),
                        rx.button("Limpar busca", on_click=StockState.clear_search, variant="soft"),
                        width="100%",
                        wrap="wrap",
                        align="center",
                    ),
                    rx.cond(
                        StockState.is_loading,
                        rx.center(rx.spinner(), "Carregando estoque...", width="100%", padding="2rem"),
                        rx.cond(
                            StockState.error_message != "",
                            rx.text(StockState.error_message, color="#b91c1c"),
                            rx.cond(
                                StockState.rows.length() > 0,
                                _stock_table(),
                                rx.text("Nenhum produto encontrado.", color="#64748b", padding="1rem"),
                            ),
                        ),
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
            _pagination(),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
