"""Área exclusiva de acompanhamento das solicitações para o perfil Compras."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import reflex as rx

from ..components.layout import page, section
from ..components.operation_feedback import success_dialog
from ..components.theme import ERROR_TEXT, SUCCESS_TEXT, TEXT_MUTED
from ..services.session_read_cache import session_read_cache
from ..services.xano_client import (
    XanoAuthError, XanoConnectionError, XanoError, XanoPermissionError,
    XanoRequestError, auth_client,
)
from ..state import AuthState


LIST_ENDPOINT = "GET /purchase_requests"
DETAIL_ENDPOINT = "GET /purchase_requests/by_id"
PAGE_SIZE = 20
READ_TTL = 20.0
logger = logging.getLogger(__name__)


def _log_list_failure(error: XanoError) -> None:
    _log_read_failure(error, detail=False)


def _log_detail_failure(error: XanoError) -> None:
    _log_read_failure(error, detail=True)


def _log_read_failure(error: XanoError, *, detail: bool) -> None:
    status = error.status_code
    origin = getattr(error, "origin", None) or (
        "response_contract" if status == 200 else
        "network_transport" if isinstance(error, XanoConnectionError) else
        "authentication" if status == 401 else
        "authorization" if status == 403 else
        "remote_xano" if status is not None else "unknown"
    )
    # Only locally assigned schema diagnostics; never log payloads or exception text.
    logger.warning(
        "Purchase %s read failed: endpoint=%s status=%s "
        "exception_type=%s origin=%s contract_section=%s contract_field=%s expected=%s found_type=%s",
        "detail" if detail else "list", DETAIL_ENDPOINT if detail else LIST_ENDPOINT,
        status, type(error).__name__, origin,
        getattr(error, "contract_section", "-"),
        getattr(error, "contract_field", "-"),
        getattr(error, "contract_expected", "-"),
        getattr(error, "contract_found_type", "-"),
    )


STATUS_OPTIONS = {
    "aberta": [("em_analise", "Em análise")],
    "em_analise": [("aprovada", "Aprovada"), ("rejeitada", "Rejeitada")],
    "aprovada": [("em_compra", "Em compra")],
    "em_compra": [("aguardando_recebimento", "Aguardando recebimento")],
}
STATUS_LABELS = {
    "aberta": "Aberta", "em_analise": "Em análise", "aprovada": "Aprovada",
    "rejeitada": "Rejeitada", "em_compra": "Em compra",
    "aguardando_recebimento": "Aguardando recebimento",
    "recebimento_parcial": "Recebimento parcial", "concluida": "Concluída",
    "cancelada": "Cancelada",
}


def _formatted_date(value: object) -> str:
    try:
        return datetime.fromtimestamp(float(value) / 1000, ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return "—"


def _invalidate_reads(token: str) -> None:
    for endpoint in (
        LIST_ENDPOINT, DETAIL_ENDPOINT, "GET /purchase_requests/summary",
        "GET /purchase_requests/notifications", "GET /stock/replenishment",
    ):
        session_read_cache.invalidate(endpoint=endpoint, token=token)


class PurchaseManagementState(rx.State):
    rows: list[dict[str, str]] = []
    total: int = 0
    current_page: int = 1
    status_filter: str = "todos"
    list_state: str = "loading"
    list_busy: bool = False
    list_error: str = ""
    detail_state: str = "loading"
    detail_busy: bool = False
    detail_error: str = ""
    request_data: dict[str, str] = {}
    product_data: dict[str, str] = {}
    history_rows: list[dict[str, str]] = []
    history_page: int = 1
    history_total: int = 0
    request_id: int = 0
    status_choice: str = ""
    status_busy: bool = False
    status_message: str = ""
    success_dialog_title: str = ""
    success_dialog_message: str = ""
    success_dialog_open: bool = False
    status_error: str = ""
    needs_reconciliation: bool = False
    justification_open: bool = False
    justification_mode: str = ""
    justification: str = ""
    cancel_busy: bool = False
    can_update_status: bool = False
    can_cancel_requests: bool = False
    _owner_fingerprint: str = ""
    _global_scope: bool = False

    @rx.var
    def has_previous(self) -> bool:
        return self.current_page > 1

    @rx.var
    def has_next(self) -> bool:
        return self.current_page * PAGE_SIZE < self.total

    @rx.var
    def history_has_next(self) -> bool:
        return self.history_page * PAGE_SIZE < self.history_total

    @rx.var
    def history_page_total(self) -> int:
        return max(1, (self.history_total + PAGE_SIZE - 1) // PAGE_SIZE)

    def set_success_dialog_open(self, is_open: bool):
        self.success_dialog_open = is_open

    @rx.var
    def allowed_statuses(self) -> list[dict[str, str]]:
        return [{"code": code, "label": label} for code, label in STATUS_OPTIONS.get(self.request_data.get("status", ""), [])]

    @rx.var
    def can_cancel(self) -> bool:
        return self.request_data.get("status") in {"aberta", "em_analise"}

    @rx.var
    def confirmed_status_label(self) -> str:
        status = self.request_data.get("status", "")
        return STATUS_LABELS.get(status, status or "—")

    @rx.var
    def formatted_request_date(self) -> str:
        return _formatted_date(self.request_data.get("data_criacao"))

    def _reset_session(self, token: str, grants: list[str], profile_code: str) -> None:
        fingerprint = hashlib.sha256(
            (token + "|" + profile_code + "|" + ",".join(sorted(grants))).encode("utf-8")
        ).hexdigest()
        if fingerprint == self._owner_fingerprint:
            return
        self._owner_fingerprint = fingerprint
        self._global_scope = profile_code == "administrator" or (
            "purchase_request.read" in grants and "purchase_request.manage" in grants
        )
        self.rows = []
        self.total = 0
        self.current_page = 1
        self.request_data = {}
        self.product_data = {}
        self.history_rows = []
        self.request_id = 0
        self.status_message = ""
        self.status_error = ""
        self.justification_open = False
        self.justification = ""
        self.status_choice = ""
        self.can_update_status = False
        self.can_cancel_requests = False

    async def _authorized(self, *, detail: bool = False) -> tuple[str, object | None]:
        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()
        if redirect is not None:
            return "", redirect
        if not auth.session_is_valid:
            return "", None
        token = str(auth.auth_token or "").strip()
        self._reset_session(token, auth.permission_codes, auth.inventory_profile_code)
        can_read = auth.has_permission("purchase_request.read")
        can_access = can_read
        if not can_access:
            if detail:
                self.request_data = {}
                self.history_rows = []
            else:
                self.rows = []
            return "", None
        self.can_update_status = auth.has_permission("purchase_request.status.update")
        self.can_cancel_requests = auth.has_permission("purchase_request.cancel") or auth.has_permission("purchase_request.manage")
        return token, None

    async def load_list(self, force: bool = False):
        token, redirect = await self._authorized()
        if redirect is not None:
            yield redirect
            return
        if not token:
            self.list_state = "denied"
            self.list_error = "O perfil não possui acesso às solicitações. Contate o administrador."
            return
        if self.list_busy:
            return
        self.list_busy = True
        self.list_state = "loading"
        self.list_error = ""
        yield
        params = {"page": self.current_page, "per_page": PAGE_SIZE, "status": self.status_filter}
        list_scope = "purchase_request.list.global" if self._global_scope else "purchase_request.list.own"
        key = session_read_cache.key(list_scope, LIST_ENDPOINT, token, params)
        cached, fresh = session_read_cache.get(key, READ_TTL)
        try:
            data = cached if fresh and not force else await auth_client.list_purchase_requests(
                token, page=self.current_page, per_page=PAGE_SIZE,
                status=None if self.status_filter == "todos" else self.status_filter,
            )
            if not fresh or force:
                session_read_cache.set(key, data, READ_TTL)
            self.rows = [
                {"id": str(item["id"]), "produto": str(item.get("produto_nome") or "—"),
                 "codigo": str(item.get("produto_codigo") or "—"),
                 "quantidade": str(item.get("quantidade_solicitada") or "—"),
                 "urgencia": str(item.get("urgencia") or "—"),
                 "status": STATUS_LABELS.get(str(item.get("status")), str(item.get("status"))),
                 "data": _formatted_date(item.get("data_criacao"))}
                for item in data["items"]
            ]
            self.total = data["itemsTotal"]
            self.list_state = "ready" if self.rows else "empty"
        except XanoAuthError as exc:
            _log_list_failure(exc)
            auth = await self.get_state(AuthState)
            yield auth.logout()
        except XanoPermissionError as exc:
            _log_list_failure(exc)
            self.rows = []
            self.list_state = "denied"
            self.list_error = "Você não tem acesso às solicitações de compras."
        except XanoRequestError as exc:
            _log_list_failure(exc)
            self.list_state = "unavailable" if exc.status_code == 404 else "error"
            self.list_error = "A consulta de compras ainda não está disponível." if exc.status_code == 404 else exc.message
        except XanoError as exc:
            _log_list_failure(exc)
            self.list_state = "error"
            self.list_error = (
                "Não foi possível interpretar a lista de solicitações. Atualize e tente novamente."
                if exc.status_code == 200 else
                "Não foi possível carregar as solicitações. Verifique sua conexão e tente novamente."
                if isinstance(exc, XanoConnectionError) else
                "Não foi possível carregar as solicitações. Tente novamente mais tarde."
            )
        finally:
            self.list_busy = False

    async def load_detail(self, force: bool = False):
        token, redirect = await self._authorized(detail=True)
        if redirect is not None:
            yield redirect
            return
        if not token:
            self.detail_state = "denied"
            self.detail_error = "O perfil não possui acesso aos detalhes. Contate o administrador."
            return
        if self.detail_busy:
            return
        route_parts = str(self.router.url.path).strip("/").split("/")
        try:
            request_id = int(route_parts[1]) if len(route_parts) == 2 else 0
        except ValueError:
            request_id = 0
        if request_id <= 0:
            self.detail_state = "error"
            self.detail_error = "Solicitação inválida."
            return
        if request_id != self.request_id:
            self.request_data = {}
            self.product_data = {}
            self.history_rows = []
            self.history_page = 1
            self.request_id = request_id
            self.status_message = ""
            self.status_error = ""
        self.detail_state = "loading"
        self.detail_busy = True
        self.detail_error = ""
        yield
        params = {"request_id": request_id, "history_page": self.history_page, "per_page": PAGE_SIZE}
        scope = "purchase_request.detail.global" if self._global_scope else "purchase_request.detail.own"
        key = session_read_cache.key(scope, DETAIL_ENDPOINT, token, params)
        cached, fresh = session_read_cache.get(key, READ_TTL)
        try:
            data = cached if fresh and not force else await auth_client.get_purchase_request_detail(
                token, request_id, history_page=self.history_page, history_per_page=PAGE_SIZE,
            )
            if not fresh or force:
                session_read_cache.set(key, data, READ_TTL)
            self.request_data = {k: str(v) if v is not None else "" for k, v in data["solicitacao"].items()}
            self.product_data = {k: str(v) if v is not None else "" for k, v in data["produto"].items()}
            history = data["historico"]
            self.history_rows = [
                {"id": str(row["id"]), "evento": str(row["evento"]),
                 "data": _formatted_date(row.get("data_evento")),
                 "justificativa": str(row.get("justificativa") or ""),
                 "actor": str(row.get("actor_user_id") or "—")}
                for row in history["items"]
            ]
            self.history_total = history["itemsTotal"]
            self.detail_state = "ready"
            self.needs_reconciliation = False
        except XanoAuthError as exc:
            _log_detail_failure(exc)
            auth = await self.get_state(AuthState)
            yield auth.logout()
        except XanoPermissionError as exc:
            _log_detail_failure(exc)
            self.detail_state = "denied"
            self.detail_error = "Você não tem acesso aos detalhes desta solicitação."
        except XanoRequestError as exc:
            _log_detail_failure(exc)
            self.detail_state = "unavailable" if exc.status_code == 404 else "error"
            self.detail_error = "Solicitação não encontrada ou sem acesso." if exc.status_code == 404 else exc.message
        except XanoError as exc:
            _log_detail_failure(exc)
            self.detail_state = "error"
            self.detail_error = (
                "Não foi possível interpretar os detalhes desta solicitação. Atualize e tente novamente."
                if exc.status_code == 200 else
                "Não foi possível carregar os detalhes. Verifique sua conexão e tente novamente."
                if isinstance(exc, XanoConnectionError) else
                "Não foi possível carregar os detalhes da solicitação. Tente novamente mais tarde."
            )
        finally:
            self.detail_busy = False

    def change_filter(self, value: str):
        if value in {"todos", *STATUS_LABELS}:
            self.status_filter = value
            self.current_page = 1
            return PurchaseManagementState.load_list(True)

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            return PurchaseManagementState.load_list()

    def next_page(self):
        if self.has_next:
            self.current_page += 1
            return PurchaseManagementState.load_list()

    def next_history_page(self):
        if self.history_has_next:
            self.history_page += 1
            return PurchaseManagementState.load_detail(True)

    def previous_history_page(self):
        if self.history_page > 1:
            self.history_page -= 1
            return PurchaseManagementState.load_detail(True)

    async def select_status(self, value: str):
        if self.status_busy or self.cancel_busy or self.needs_reconciliation or self.detail_state != "ready":
            return
        if value not in {code for code, _ in STATUS_OPTIONS.get(self.request_data.get("status", ""), [])}:
            return
        self.status_choice = value
        self.status_error = ""
        if value == "rejeitada":
            self.justification = ""
            self.justification_mode = "rejeicao"
            self.justification_open = True
            return
        async for event in self._write_status(value, None):
            yield event

    async def _write_status(self, value: str, reason: str | None):
        auth = await self.get_state(AuthState)
        token, redirect = await self._authorized(detail=True)
        if redirect is not None:
            yield redirect
            return
        if not auth.has_permission("purchase_request.status.update") or self.status_busy:
            self.status_error = "Sem permissão para alterar o status."
            return
        expected = self.request_data.get("status", "")
        if value not in {code for code, _ in STATUS_OPTIONS.get(expected, [])}:
            self.status_error = "O status confirmado não permite essa transição."
            return
        self.status_busy = True
        self.status_message = ""
        self.success_dialog_open = False
        self.status_error = ""
        yield
        try:
            result = await auth_client.update_purchase_request_status(
                token, self.request_id, status_esperado=expected,
                novo_status=value, justificativa=reason,
            )
        except XanoAuthError:
            yield auth.logout()
            return
        except (XanoPermissionError, XanoRequestError) as exc:
            self.status_error = exc.message
            self.needs_reconciliation = (
                getattr(exc, "error_code", "") == "PURCHASE_REQUEST_STATUS_CONFLICT"
                or getattr(exc, "status_code", 0) >= 500
            )
        except (XanoConnectionError, XanoError):
            self.status_error = "Resultado incerto. Atualize o detalhe antes de tentar outra alteração."
            self.needs_reconciliation = True
        else:
            self.request_data = {k: str(v) if v is not None else "" for k, v in result["solicitacao"].items()}
            self.status_message = "Status da solicitação atualizado com sucesso."
            self.success_dialog_title = "Status atualizado"
            self.success_dialog_message = self.status_message
            self.success_dialog_open = True
            _invalidate_reads(token)
            self.history_page = 1
            async for event in self.load_detail(True):
                yield event
        finally:
            self.status_busy = False
            self.status_choice = ""

    def open_cancel(self):
        if self.can_cancel and self.can_cancel_requests and not self.status_busy and not self.cancel_busy and not self.needs_reconciliation:
            self.justification = ""
            self.justification_mode = "cancelamento"
            self.justification_open = True

    def close_justification(self):
        if not self.status_busy and not self.cancel_busy:
            self.justification_open = False
            self.justification = ""
            self.status_choice = ""

    def change_justification(self, value: str):
        if not self.status_busy and not self.cancel_busy:
            self.justification = value

    async def confirm_justification(self):
        reason = self.justification.strip()
        if not reason:
            self.status_error = "Informe uma justificativa."
            return
        mode = self.justification_mode
        self.justification_open = False
        if mode == "rejeicao":
            async for event in self._write_status("rejeitada", reason):
                yield event
            return
        if mode != "cancelamento" or not self.can_cancel or not self.can_cancel_requests or self.cancel_busy:
            return
        auth = await self.get_state(AuthState)
        token, redirect = await self._authorized(detail=True)
        if redirect is not None:
            yield redirect
            return
        if not (auth.has_permission("purchase_request.cancel") or auth.has_permission("purchase_request.manage")):
            self.status_error = "Sem permissão para cancelar."
            return
        self.cancel_busy = True
        self.status_error = ""
        self.status_message = ""
        self.success_dialog_open = False
        yield
        try:
            await auth_client.cancel_purchase_request(token, self.request_id, reason)
        except XanoAuthError:
            yield auth.logout()
            return
        except (XanoPermissionError, XanoRequestError) as exc:
            self.status_error = exc.message
            if getattr(exc, "status_code", 0) >= 500:
                self.needs_reconciliation = True
        except (XanoConnectionError, XanoError):
            self.status_error = "Resultado incerto. Atualize o detalhe antes de tentar novamente."
            self.needs_reconciliation = True
        else:
            _invalidate_reads(token)
            self.status_message = "Solicitação cancelada com sucesso."
            self.success_dialog_title = "Solicitação cancelada"
            self.success_dialog_message = "O cancelamento foi confirmado. O estoque não foi alterado."
            self.success_dialog_open = True
            self.history_page = 1
            async for event in self.load_detail(True):
                yield event
        finally:
            self.cancel_busy = False
            self.justification = ""


def _request_row(row: dict[str, str]) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.text("#", row["id"], " · ", row["codigo"], " · ", row["produto"], flex="1"),
            rx.badge(row["status"], variant="soft"),
            rx.text(row["data"], size="2", color=TEXT_MUTED),
            width="100%", align="center", wrap="wrap", gap="12px",
        ),
        href="/compras/" + row["id"], width="100%", padding="12px",
        border_bottom="1px solid #d9e4dd", text_decoration="none",
    )


def compras() -> rx.Component:
    return page("Compras solicitadas", rx.vstack(
        rx.text("Acompanhe as solicitações de compra e seus estados.", color=TEXT_MUTED),
        section("Solicitações", rx.vstack(
            rx.select.root(
                rx.select.trigger(placeholder="Filtrar por status", width="220px"),
                rx.select.content(
                    rx.select.item("Todos", value="todos"),
                    *[rx.select.item(label, value=code) for code, label in STATUS_LABELS.items()],
                ),
                value=PurchaseManagementState.status_filter,
                on_change=PurchaseManagementState.change_filter,
            ),
            rx.cond(PurchaseManagementState.list_state == "loading", rx.hstack(rx.spinner(), "Carregando solicitações...")),
            rx.cond(PurchaseManagementState.list_state == "empty", rx.text("Nenhuma solicitação encontrada para este filtro.")),
            rx.cond(PurchaseManagementState.list_error != "", rx.hstack(
                rx.text(PurchaseManagementState.list_error, color=ERROR_TEXT, role="alert"),
                rx.button("Atualizar", on_click=PurchaseManagementState.load_list(True), size="1", variant="soft"),
            )),
            rx.cond(PurchaseManagementState.list_state == "ready", rx.foreach(PurchaseManagementState.rows, _request_row)),
            rx.cond((PurchaseManagementState.list_state == "ready") | (PurchaseManagementState.list_state == "empty"), rx.hstack(
                rx.button("Anterior", on_click=PurchaseManagementState.previous_page, disabled=~PurchaseManagementState.has_previous, variant="soft"),
                rx.text("Página ", PurchaseManagementState.current_page, " · Total ", PurchaseManagementState.total, size="2"),
                rx.button("Próxima", on_click=PurchaseManagementState.next_page, disabled=~PurchaseManagementState.has_next, variant="soft"),
                justify="between", width="100%", wrap="wrap",
            )),
            width="100%", align="stretch", gap="16px",
        )),
        width="100%", align="stretch", gap="20px",
    ))


def _history_row(row: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.text(row["evento"], weight="medium"),
        rx.text(row["data"], color=TEXT_MUTED),
        rx.text("Usuário #", row["actor"], color=TEXT_MUTED),
        rx.cond(row["justificativa"] != "", rx.text(row["justificativa"], color=TEXT_MUTED), rx.fragment()),
        width="100%", gap="12px", wrap="wrap", padding="8px 0",
    )


def _justification_dialog() -> rx.Component:
    return rx.cond(PurchaseManagementState.justification_open, rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(rx.cond(PurchaseManagementState.justification_mode == "rejeicao", "Rejeitar solicitação", "Cancelar solicitação")),
            rx.dialog.description(rx.cond(
                PurchaseManagementState.justification_mode == "rejeicao",
                "Informe brevemente o motivo da rejeição.",
                rx.text(
                    "Deseja cancelar a solicitação do produto ",
                    PurchaseManagementState.product_data["codigo"],
                    " — ",
                    PurchaseManagementState.product_data["nome"],
                    "? Informe o motivo para continuar.",
                ),
            )),
            rx.text(
                rx.cond(PurchaseManagementState.justification_mode == "rejeicao", "Motivo da rejeição", "Motivo do cancelamento"),
                size="2",
                weight="medium",
            ),
            rx.text_area(
                value=PurchaseManagementState.justification,
                on_change=PurchaseManagementState.change_justification,
                placeholder="Descreva brevemente o motivo...",
                width="100%",
                min_height="72px",
                required=True,
                aria_label="Justificativa obrigatória",
                resize="vertical",
            ),
            rx.hstack(
                rx.button("Voltar", on_click=PurchaseManagementState.close_justification, variant="soft", size="2"),
                rx.cond(
                    PurchaseManagementState.justification_mode == "rejeicao",
                    rx.button(
                        "Confirmar rejeição",
                        on_click=PurchaseManagementState.confirm_justification,
                        disabled=PurchaseManagementState.status_busy | PurchaseManagementState.cancel_busy,
                        size="2",
                    ),
                    rx.button(
                        "Confirmar cancelamento",
                        on_click=PurchaseManagementState.confirm_justification,
                        disabled=PurchaseManagementState.status_busy | PurchaseManagementState.cancel_busy,
                        variant="outline",
                        color=ERROR_TEXT,
                        border=f"1px solid {ERROR_TEXT}",
                        size="2",
                    ),
                ),
                justify="end", width="100%", spacing="3", wrap="wrap",
            ),
            width="100%",
            max_width="min(32rem, calc(100vw - 32px))",
            padding="1.25rem",
            border_radius="1rem",
        ),
        open=PurchaseManagementState.justification_open,
    ), rx.fragment())


def compra_detalhe() -> rx.Component:
    return page("Detalhes da solicitação", rx.vstack(
        rx.button(rx.icon("arrow-left", size=16), "Voltar", on_click=rx.redirect("/compras"), variant="soft", size="2", width="fit-content", align_self="start"),
        rx.cond(PurchaseManagementState.detail_state == "loading", rx.hstack(rx.spinner(), "Carregando detalhes...")),
        rx.cond(PurchaseManagementState.detail_error != "", rx.hstack(
            rx.text(PurchaseManagementState.detail_error, color=ERROR_TEXT, role="alert"),
            rx.button("Atualizar", on_click=PurchaseManagementState.load_detail(True), size="1", variant="soft"),
        )),
        rx.cond(PurchaseManagementState.detail_state == "ready", rx.vstack(
            section("Solicitação", rx.vstack(
                rx.text("Pedido #", PurchaseManagementState.request_data["id"]),
                rx.text("Produto: ", PurchaseManagementState.product_data["codigo"], " · ", PurchaseManagementState.product_data["nome"]),
                rx.text("Quantidade: ", PurchaseManagementState.request_data["quantidade_solicitada"], " ", PurchaseManagementState.product_data["unidade_medida"]),
                rx.text("Urgência: ", PurchaseManagementState.request_data["urgencia"]),
                rx.text("Solicitante #", PurchaseManagementState.request_data["solicitante_usuario_id"]),
                rx.text("Criada em: ", PurchaseManagementState.formatted_request_date),
                rx.text("Status confirmado: ", PurchaseManagementState.confirmed_status_label),
                rx.hstack(
                    rx.cond(PurchaseManagementState.can_update_status & (PurchaseManagementState.allowed_statuses.length() > 0), rx.select.root(
                        rx.select.trigger(placeholder="Alterar status", width="260px"),
                        rx.select.content(rx.foreach(PurchaseManagementState.allowed_statuses, lambda item: rx.select.item(item["label"], value=item["code"]))),
                        value=PurchaseManagementState.status_choice,
                        on_change=PurchaseManagementState.select_status,
                        disabled=PurchaseManagementState.status_busy | PurchaseManagementState.cancel_busy | PurchaseManagementState.needs_reconciliation,
                    )),
                    rx.cond(PurchaseManagementState.can_cancel & PurchaseManagementState.can_cancel_requests, rx.button("Cancelar solicitação", on_click=PurchaseManagementState.open_cancel, variant="outline", color=ERROR_TEXT, border=f"1px solid {ERROR_TEXT}", size="2", width="fit-content", disabled=PurchaseManagementState.status_busy | PurchaseManagementState.cancel_busy | PurchaseManagementState.needs_reconciliation)),
                    width="100%", align="center", spacing="3", wrap="wrap",
                ),
                rx.cond(PurchaseManagementState.status_busy | PurchaseManagementState.cancel_busy, rx.hstack(rx.spinner(), "Salvando...")),
                rx.cond(PurchaseManagementState.status_error != "", rx.text(PurchaseManagementState.status_error, color=ERROR_TEXT, role="alert")),
                rx.cond(PurchaseManagementState.needs_reconciliation, rx.button("Atualizar solicitação", on_click=PurchaseManagementState.load_detail(True), variant="soft", disabled=PurchaseManagementState.detail_busy)),
                width="100%", align="stretch", gap="10px",
            )),
            section("Histórico", rx.vstack(
                rx.foreach(PurchaseManagementState.history_rows, _history_row),
                rx.cond(PurchaseManagementState.history_total == 0, rx.text("Ainda não há eventos registrados.")),
                rx.cond(PurchaseManagementState.history_page_total > 1, rx.hstack(
                    rx.button("Anterior", on_click=PurchaseManagementState.previous_history_page, disabled=PurchaseManagementState.history_page <= 1, variant="soft"),
                    rx.text("Página ", PurchaseManagementState.history_page, " de ", PurchaseManagementState.history_page_total, size="2"),
                    rx.button("Próxima", on_click=PurchaseManagementState.next_history_page, disabled=~PurchaseManagementState.history_has_next, variant="soft"),
                    justify="between", width="100%", wrap="wrap",
                )),
                width="100%", align="stretch",
            )),
            width="100%", align="stretch", gap="20px",
        )),
        _justification_dialog(),
        success_dialog(
            is_open=PurchaseManagementState.success_dialog_open,
            title=PurchaseManagementState.success_dialog_title,
            message=PurchaseManagementState.success_dialog_message,
            on_open_change=PurchaseManagementState.set_success_dialog_open,
        ),
        width="100%", align="stretch", gap="20px",
    ))
