"""RelatÃ³rio operacional de movimentaÃ§Ãµes de estoque."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

import reflex as rx

logger = logging.getLogger(__name__)


def _sao_paulo_timezone():
    try:
        return ZoneInfo("America/Sao_Paulo")
    except Exception:
        return timezone(timedelta(hours=-3))

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
    applied_start_date: str = ""
    applied_end_date: str = ""
    applied_filter_type: str = ""
    applied_filter_product_id: str = ""
    applied_filter_supplier_id: str = ""

    product_options: list[dict[str, str]] = []
    product_query: str = ""
    product_options_open: bool = False
    product_page: int = 1
    product_has_more: bool = False
    product_loading_more: bool = False

    supplier_options: list[dict[str, str]] = []
    supplier_query: str = ""
    supplier_options_open: bool = False
    supplier_page: int = 1
    supplier_has_more: bool = False
    supplier_loading_more: bool = False

    movement_total: int = 0
    entry_quantity_total: str = "0"
    exit_quantity_total: str = "0"
    export_loading: bool = False

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
    def filtered_supplier_options(self) -> list[dict[str, str]]:
        query = normalize_search_text(self.supplier_query)
        if not query:
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
        self.applied_start_date = ""
        self.applied_end_date = ""
        self.applied_filter_type = ""
        self.applied_filter_product_id = ""
        self.applied_filter_supplier_id = ""
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        self.product_query = ""
        self.supplier_query = ""
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
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        yield
        token = await self._session_token()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        try:
            await self._load_report_data(token, 1)
        except XanoAuthError:
            self.error_message = "Sua sessÃ£o expirou. FaÃ§a login novamente."
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.error_message = "VocÃª nÃ£o possui permissÃ£o para visualizar os relatÃ³rios."
        except XanoRequestError as exc:
            self.error_message = self._request_error_message(exc)
        except (XanoConnectionError, XanoServerError, XanoError):
            self.error_message = "Não foi possível carregar os relatórios. Tente novamente."
        except Exception as exc:
            logger.exception("Reports load failed: exception_type=%s", type(exc).__name__)
            self.error_message = "Não foi possível carregar os relatórios. Tente novamente."
        finally:
            self.is_loading = False
        yield

        option_results = await asyncio.gather(
            self._load_products(token),
            self._load_suppliers(token),
            return_exceptions=True,
        )
        for operation, result in zip(("products", "suppliers"), option_results):
            if not isinstance(result, BaseException):
                continue
            logger.warning(
                "Report filter options failed: operation=%s path=/%s exception_type=%s",
                operation,
                operation,
                type(result).__name__,
            )
            if operation == "products":
                self.product_options = []
                self.product_page = 1
                self.product_has_more = False
            else:
                self.supplier_options = []
                self.supplier_page = 1
                self.supplier_has_more = False

    async def _load_products(self, token: str):
        response = await auth_client.list_report_options(token, "product", page=1, per_page=100)
        self.product_options = []
        self.product_options.extend(
            self._product_option(item)
            for item in response["items"]
            if isinstance(item, dict) and item.get("id") is not None
        )
        self.product_page = 1
        self.product_has_more = len(response["items"]) == 100

    async def _load_suppliers(self, token: str):
        response = await auth_client.list_report_options(token, "supplier", page=1, per_page=100)
        self.supplier_options = []
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
            response = await auth_client.list_report_options(token, "product", page=page, per_page=100)
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
        except XanoError as exc:
            logger.warning(
                "Report filter options failed: operation=products path=/products exception_type=%s",
                type(exc).__name__,
            )
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
            response = await auth_client.list_report_options(token, "supplier", page=page, per_page=100)
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
        except XanoError as exc:
            logger.warning(
                "Report filter options failed: operation=suppliers path=/suppliers exception_type=%s",
                type(exc).__name__,
            )
        finally:
            self.supplier_loading_more = False

    def search_products(self, value: str):
        self.product_query = value
        self.filter_product_id = ""
        self.product_options_open = True
        self.supplier_options_open = False

    def open_product_options(self):
        if self.filter_product_id:
            self.filter_product_id = ""
            self.product_query = ""
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
        self.product_query = option["label"] if option else ""
        self.product_options_open = False

    def search_suppliers(self, value: str):
        self.supplier_query = value
        self.filter_supplier_id = ""
        self.supplier_options_open = True
        self.product_options_open = False

    def open_supplier_options(self):
        if self.filter_supplier_id:
            self.filter_supplier_id = ""
            self.supplier_query = ""
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
        self.supplier_query = option["label"] if option else ""
        self.supplier_options_open = False

    @staticmethod
    def _date_boundary(value: str, *, end_of_day: bool) -> int | None:
        if not value.strip():
            return None
        parsed = datetime.strptime(value, "%Y-%m-%d")
        local_timezone = _sao_paulo_timezone()
        if end_of_day:
            parsed = parsed + timedelta(days=1) - timedelta(milliseconds=1)
        return int(parsed.replace(tzinfo=local_timezone).timestamp() * 1000)

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
        return "Não foi possível carregar os relatórios. Tente novamente."

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
            return datetime.fromtimestamp(timestamp, _sao_paulo_timezone()).strftime("%d/%m/%Y %H:%M")
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
            from_ms = self._date_boundary(self.applied_start_date, end_of_day=False)
            to_ms = self._date_boundary(self.applied_end_date, end_of_day=True)
        except ValueError:
            self.error_message = "Informe datas vÃ¡lidas para o período."
            return
        if from_ms is not None and to_ms is not None and from_ms > to_ms:
            self.error_message = "A data inicial deve ser anterior ou igual Ã  data final."
            return

        product_id = int(self.applied_filter_product_id) if self.applied_filter_product_id.isdigit() and int(self.applied_filter_product_id) > 0 else None
        supplier_id = int(self.applied_filter_supplier_id) if self.applied_filter_supplier_id.isdigit() and int(self.applied_filter_supplier_id) > 0 else None
        tipo = self.applied_filter_type or None

        summary, movements = await asyncio.gather(
            auth_client.get_movements_summary(
                token,
                date_from=from_ms,
                date_to=to_ms,
                tipo=tipo,
                product_id=product_id,
                supplier_id=supplier_id,
            ),
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
        self.applied_start_date = self.start_date
        self.applied_end_date = self.end_date
        self.applied_filter_type = self.filter_type
        self.applied_filter_product_id = self.filter_product_id
        self.applied_filter_supplier_id = self.filter_supplier_id
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
        return ReportState.load_report(1)

    async def clear_filters(self):
        self.start_date = ""
        self.end_date = ""
        self.filter_type = ""
        self.filter_product_id = ""
        self.filter_supplier_id = ""
        self.applied_start_date = ""
        self.applied_end_date = ""
        self.applied_filter_type = ""
        self.applied_filter_product_id = ""
        self.applied_filter_supplier_id = ""
        self.product_query = ""
        self.supplier_query = ""
        self.current_page = 1
        self.movement_total = 0
        self.entry_quantity_total = "0"
        self.exit_quantity_total = "0"
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
            self.error_message = "Não foi possível carregar os relatórios. Tente novamente."
        except Exception as exc:
            logger.exception("Reports load failed: exception_type=%s", type(exc).__name__)
            self.error_message = "Não foi possível carregar os relatórios. Tente novamente."
        finally:
            self.is_loading = False

    def load_previous_page(self):
        if self.prev_page is not None:
            return ReportState.load_report(self.prev_page)

    def load_next_page(self):
        if self.next_page is not None:
            return ReportState.load_report(self.next_page)

    async def _all_filtered_rows(self, token: str) -> list[dict[str, str]]:
        from_ms = self._date_boundary(self.applied_start_date, end_of_day=False)
        to_ms = self._date_boundary(self.applied_end_date, end_of_day=True)
        product_id = int(self.applied_filter_product_id) if self.applied_filter_product_id.isdigit() and int(self.applied_filter_product_id) > 0 else None
        supplier_id = int(self.applied_filter_supplier_id) if self.applied_filter_supplier_id.isdigit() and int(self.applied_filter_supplier_id) > 0 else None
        tipo = self.applied_filter_type or None
        rows: list[dict[str, str]] = []
        page = 1
        while True:
            response = await auth_client.list_movements(
                token, page=page, per_page=100, tipo=tipo, product_id=product_id,
                supplier_id=supplier_id, date_from=from_ms, date_to=to_ms,
            )
            rows.extend(self._movement_row(item) for item in response["items"] if isinstance(item, dict))
            if len(rows) > 100_000:
                raise ValueError("O relatório excedeu o limite seguro de exportação (100.000 registros).")
            if response.get("nextPage") is None:
                break
            page = int(response["nextPage"])
        return rows

    async def export_excel(self):
        if self.export_loading:
            return
        self.export_loading = True
        self.error_message = ""
        yield
        token = await self._session_token()
        if not token:
            self.export_loading = False
            yield rx.redirect("/")
            return
        try:
            rows = await self._all_filtered_rows(token)
            content = self._build_xlsx(rows)
            filename = datetime.now(_sao_paulo_timezone()).strftime("relatorio_movimentacoes_%Y%m%d_%H%M%S.xlsx")
            yield rx.download(data=content, filename=filename, mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except XanoAuthError:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
        except XanoError as exc:
            logger.exception("Report export failed: operation=xlsx path=/movements")
            self.error_message = self._request_error_message(exc) if isinstance(exc, XanoRequestError) else "Não foi possível exportar o relatório. Tente novamente."
        except Exception as exc:
            logger.exception("Report export failed: operation=xlsx exception_type=%s", type(exc).__name__)
            self.error_message = str(exc) if isinstance(exc, ValueError) else "Não foi possível exportar o relatório. Tente novamente."
        finally:
            self.export_loading = False

    def _build_xlsx(self, rows: list[dict[str, str]]) -> bytes:
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        pkg_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        ET.register_namespace("", ns)
        ET.register_namespace("r", rel_ns)

        headers = ["Data/Hora", "Tipo", "C\u00f3digo", "Produto", "Quantidade", "Usu\u00e1rio", "Fornecedor", "Motivo"]
        keys = ("data_hora", "tipo", "codigo", "produto", "quantidade", "usuario", "fornecedor", "motivo")
        worksheet = ET.Element(f"{{{ns}}}worksheet")
        views = ET.SubElement(worksheet, f"{{{ns}}}sheetViews")
        view = ET.SubElement(views, f"{{{ns}}}sheetView", {"workbookViewId": "0"})
        ET.SubElement(view, f"{{{ns}}}pane", {"ySplit": "1", "topLeftCell": "A2", "activePane": "bottomLeft", "state": "frozen"})
        ET.SubElement(view, f"{{{ns}}}selection", {"pane": "bottomLeft", "activeCell": "A2", "sqref": "A2"})
        columns = ET.SubElement(worksheet, f"{{{ns}}}cols")
        for index, width in enumerate((19, 12, 13, 32, 15, 26, 26, 42), start=1):
            ET.SubElement(columns, f"{{{ns}}}col", {"min": str(index), "max": str(index), "width": str(width), "customWidth": "1"})

        sheet_data = ET.SubElement(worksheet, f"{{{ns}}}sheetData")

        def text_cell(row_el: ET.Element, reference: str, value: object, style: int = 0) -> None:
            cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": str(style), "t": "inlineStr"})
            inline = ET.SubElement(cell, f"{{{ns}}}is")
            ET.SubElement(inline, f"{{{ns}}}t").text = str(value)

        header_row = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": "1"})
        for col_number, label in enumerate(headers):
            text_cell(header_row, f"{chr(65 + col_number)}1", label, style=1)

        excel_epoch = datetime(1899, 12, 30)
        for row_number, row in enumerate(rows, start=2):
            row_el = ET.SubElement(sheet_data, f"{{{ns}}}row", {"r": str(row_number)})
            for col_number, key in enumerate(keys):
                reference = f"{chr(65 + col_number)}{row_number}"
                value = row.get(key)
                if value is None or value == "":
                    value = "\u2014" if key == "fornecedor" else ""
                if key == "data_hora":
                    try:
                        timestamp = datetime.strptime(str(value), "%d/%m/%Y %H:%M")
                    except ValueError:
                        text_cell(row_el, reference, value)
                    else:
                        serial = (timestamp - excel_epoch).total_seconds() / 86400
                        cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": "2"})
                        ET.SubElement(cell, f"{{{ns}}}v").text = str(serial)
                elif key == "quantidade":
                    try:
                        number = Decimal(str(value).replace(",", "."))
                        if not number.is_finite():
                            raise InvalidOperation
                    except (InvalidOperation, ValueError):
                        text_cell(row_el, reference, value)
                    else:
                        cell = ET.SubElement(row_el, f"{{{ns}}}c", {"r": reference, "s": "3"})
                        ET.SubElement(cell, f"{{{ns}}}v").text = format(number, "f")
                else:
                    text_cell(row_el, reference, value)

        ET.SubElement(worksheet, f"{{{ns}}}autoFilter", {"ref": f"A1:H{max(1, len(rows) + 1)}"})

        styles = ET.Element(f"{{{ns}}}styleSheet")
        formats = ET.SubElement(styles, f"{{{ns}}}numFmts", {"count": "2"})
        ET.SubElement(formats, f"{{{ns}}}numFmt", {"numFmtId": "164", "formatCode": "dd/mm/yyyy hh:mm"})
        ET.SubElement(formats, f"{{{ns}}}numFmt", {"numFmtId": "165", "formatCode": "0.########"})
        fonts = ET.SubElement(styles, f"{{{ns}}}fonts", {"count": "2"})
        ET.SubElement(fonts, f"{{{ns}}}font")
        bold_font = ET.SubElement(fonts, f"{{{ns}}}font")
        ET.SubElement(bold_font, f"{{{ns}}}b")
        fills = ET.SubElement(styles, f"{{{ns}}}fills", {"count": "2"})
        ET.SubElement(ET.SubElement(fills, f"{{{ns}}}fill"), f"{{{ns}}}patternFill", {"patternType": "none"})
        ET.SubElement(ET.SubElement(fills, f"{{{ns}}}fill"), f"{{{ns}}}patternFill", {"patternType": "gray125"})
        borders = ET.SubElement(styles, f"{{{ns}}}borders", {"count": "1"})
        border = ET.SubElement(borders, f"{{{ns}}}border")
        for side in ("left", "right", "top", "bottom", "diagonal"):
            ET.SubElement(border, f"{{{ns}}}{side}")
        base_styles = ET.SubElement(styles, f"{{{ns}}}cellStyleXfs", {"count": "1"})
        ET.SubElement(base_styles, f"{{{ns}}}xf", {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
        cell_styles = ET.SubElement(styles, f"{{{ns}}}cellXfs", {"count": "4"})
        for format_id, font_id in ((0, 0), (0, 1), (164, 0), (165, 0)):
            ET.SubElement(cell_styles, f"{{{ns}}}xf", {
                "numFmtId": str(format_id), "fontId": str(font_id), "fillId": "0",
                "borderId": "0", "xfId": "0", "applyNumberFormat": "1" if format_id else "0",
            })

        content_types = ET.Element(f"{{{ct_ns}}}Types")
        ET.SubElement(content_types, f"{{{ct_ns}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Default", {"Extension": "xml", "ContentType": "application/xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/workbook.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/worksheets/sheet1.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})
        ET.SubElement(content_types, f"{{{ct_ns}}}Override", {"PartName": "/xl/styles.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"})
        root_rels = ET.Element(f"{{{pkg_ns}}}Relationships")
        ET.SubElement(root_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId1", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "Target": "xl/workbook.xml"})
        workbook = ET.Element(f"{{{ns}}}workbook")
        sheets = ET.SubElement(workbook, f"{{{ns}}}sheets")
        sheet = ET.SubElement(sheets, f"{{{ns}}}sheet", {"name": "Movimenta\u00e7\u00f5es", "sheetId": "1"})
        sheet.set(f"{{{rel_ns}}}id", "rId1")
        book_rels = ET.Element(f"{{{pkg_ns}}}Relationships")
        ET.SubElement(book_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId1", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet", "Target": "worksheets/sheet1.xml"})
        ET.SubElement(book_rels, f"{{{pkg_ns}}}Relationship", {"Id": "rId2", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "Target": "styles.xml"})
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for name, root in (
                ("[Content_Types].xml", content_types), ("_rels/.rels", root_rels),
                ("xl/workbook.xml", workbook), ("xl/_rels/workbook.xml.rels", book_rels),
                ("xl/styles.xml", styles), ("xl/worksheets/sheet1.xml", worksheet),
            ):
                archive.writestr(name, ET.tostring(root, encoding="utf-8", xml_declaration=True))
        return output.getvalue()

    async def export_pdf(self):
        if self.export_loading:
            return
        self.export_loading = True
        self.error_message = ""
        yield
        token = await self._session_token()
        if not token:
            self.export_loading = False
            yield rx.redirect("/")
            return
        try:
            rows = await self._all_filtered_rows(token)
            content = self._build_pdf(rows)
            filename = datetime.now(_sao_paulo_timezone()).strftime("relatorio_movimentacoes_%Y%m%d_%H%M%S.pdf")
            yield rx.download(data=content, filename=filename, mime_type="application/pdf")
        except XanoAuthError:
            self.error_message = "Sua sessão expirou. Faça login novamente."
            yield rx.redirect("/")
        except XanoError as exc:
            logger.exception("Report export failed: operation=pdf path=/movements")
            self.error_message = self._request_error_message(exc) if isinstance(exc, XanoRequestError) else "Não foi possível exportar o relatório. Tente novamente."
        except Exception as exc:
            logger.exception("Report export failed: operation=pdf exception_type=%s", type(exc).__name__)
            self.error_message = str(exc) if isinstance(exc, ValueError) else "Não foi possível exportar o relatório. Tente novamente."
        finally:
            self.export_loading = False

    def _build_pdf(self, rows: list[dict[str, str]]) -> bytes:
        page_width, page_height = 842, 595
        margin, font_size, line_height = 22, 7, 9
        widths = [92, 50, 54, 150, 62, 110, 110, 170]
        labels = ["Data/Hora", "Tipo", "C\u00f3digo", "Produto", "Quantidade", "Usu\u00e1rio", "Fornecedor", "Motivo"]
        keys = ("data_hora", "tipo", "codigo", "produto", "quantidade", "usuario", "fornecedor", "motivo")
        pages: list[bytes] = []
        commands: list[str] = []
        y = 0.0

        def pdf_text(value: str) -> str:
            return "<" + value.encode("cp1252", errors="replace").hex().upper() + ">"

        def wrap(value: str, width: float) -> list[str]:
            limit = max(4, int(width / (font_size * 0.52)))
            words = str(value).split() or [""]
            lines: list[str] = []
            line = ""
            for word in words:
                while len(word) > limit:
                    if line:
                        lines.append(line)
                        line = ""
                    lines.append(word[:limit])
                    word = word[limit:]
                candidate = f"{line} {word}".strip()
                if len(candidate) > limit:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            if line or not lines:
                lines.append(line)
            return lines

        def table_header(top: float) -> float:
            header_height = 21
            x = margin
            commands.append("0.90 0.92 0.94 rg")
            commands.append(f"{x} {top-header_height} {sum(widths)} {header_height} re f")
            commands.append("0.72 0.75 0.79 RG 0.35 w")
            commands.append(f"{x} {top-header_height} {sum(widths)} {header_height} re S")
            commands.append("0 0 0 rg")
            for index, label in enumerate(labels):
                commands.append(f"BT /F2 7 Tf 1 0 0 1 {x+4:.2f} {top-14:.2f} Tm {pdf_text(label)} Tj ET")
                x += widths[index]
                if index < len(widths) - 1:
                    commands.append(f"{x:.2f} {top-header_height:.2f} m {x:.2f} {top:.2f} l S")
            return top - header_height

        def start_page() -> None:
            nonlocal commands, y
            if commands:
                pages.append("\n".join(commands).encode("ascii"))
            commands = [
                "0 0 0 rg",
                f"BT /F2 16 Tf 1 0 0 1 {margin} {page_height-28} Tm {pdf_text('NexStock \u2014 Relat\u00f3rio de Movimenta\u00e7\u00f5es')} Tj ET",
            ]
            y = table_header(page_height - 48)

        def draw_row(cell_lines: list[list[str]], height: float) -> None:
            nonlocal y
            commands.append("1 1 1 rg")
            commands.append(f"{margin} {y-height:.2f} {sum(widths)} {height:.2f} re f")
            commands.append("0.82 0.84 0.87 RG 0.3 w")
            commands.append(f"{margin} {y-height:.2f} {sum(widths)} {height:.2f} re S")
            commands.append("0 0 0 rg")
            x = margin
            for col, (lines, width) in enumerate(zip(cell_lines, widths)):
                for line_index, line in enumerate(lines):
                    commands.append(f"BT /F1 {font_size} Tf 1 0 0 1 {x+4:.2f} {y-11-line_index*line_height:.2f} Tm {pdf_text(line)} Tj ET")
                x += width
                if col < len(widths) - 1:
                    commands.append(f"{x:.2f} {y-height:.2f} m {x:.2f} {y:.2f} l S")
            y -= height

        start_page()
        full_page_room = y - 24
        for row in rows:
            remaining = [wrap(row.get(key) or ("\u2014" if key == "fornecedor" else ""), width - 8) for key, width in zip(keys, widths)]
            while any(remaining):
                if y - 24 < 18:
                    start_page()
                required_height = max(18, max(map(len, remaining)) * line_height + 6)
                if required_height > y - 24 and required_height <= full_page_room:
                    start_page()
                lines_fit = max(1, int((y - 24 - 6) / line_height))
                segment = [lines[:lines_fit] for lines in remaining]
                segment_height = max(18, max(map(len, segment)) * line_height + 6)
                draw_row(segment, segment_height)
                remaining = [lines[lines_fit:] for lines in remaining]
                if any(remaining):
                    start_page()
        pages.append("\n".join(commands).encode("ascii"))

        objects: list[bytes] = [
            b"", b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        page_ids = []
        for content in pages:
            page_id = len(objects) + 1
            stream_id = page_id + 1
            page_ids.append(page_id)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>".encode("ascii")
            )
            objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream")
        kids = " ".join(f"{object_id} 0 R" for object_id in page_ids)
        objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{number} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_position = len(output)
        output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("ascii"))
        return bytes(output)


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
                        rx.vstack(rx.text("Data inicial"), rx.input(type="date", value=ReportState.start_date, on_change=ReportState.change_start_date, width="100%"), flex="1", min_width="220px", align="stretch", spacing="1"),
                        rx.vstack(rx.text("Data final"), rx.input(type="date", value=ReportState.end_date, on_change=ReportState.change_end_date, width="100%"), flex="1", min_width="220px", align="stretch", spacing="1"),
                        width="100%", wrap="wrap", align="end", spacing="3",
                    ),
                    rx.hstack(
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
                            flex="1", min_width="180px", align="stretch", spacing="1",
                        ),
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
                                placeholder_color="#cbd5e1",
                            ),
                            flex="1.5", min_width="220px", align="stretch", spacing="1",
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
                                placeholder_color="#cbd5e1",
                            ),
                            flex="1.5", min_width="220px", align="stretch", spacing="1",
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
                width="100%", wrap="wrap", gap="4",
            ),
            section(
                "Movimentações no período",
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.button("Exportar PDF", on_click=ReportState.export_pdf, disabled=ReportState.is_loading | ReportState.export_loading),
                        rx.button("Exportar Excel", on_click=ReportState.export_excel, disabled=ReportState.is_loading | ReportState.export_loading),
                        width="100%", align="center", wrap="wrap",
                    ),
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
                    width="100%", align="stretch", spacing="3",
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
