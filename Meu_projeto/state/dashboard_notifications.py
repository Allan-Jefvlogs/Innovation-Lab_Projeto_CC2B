"""Estado privado da central de notificações do Dashboard."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import reflex as rx

from ..services.session_read_cache import session_read_cache
from ..services.xano_client import XanoAuthError, XanoError, XanoPermissionError, XanoRequestError, XanoServerError, auth_client, _DASHBOARD_CONFIG_ERRORS
from .auth import AuthState


logger = logging.getLogger(__name__)
NOTIFICATIONS_ENABLED = os.getenv("NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
NOTIFICATION_TTL = 20.0
NOTIFICATION_ENDPOINT = "GET /purchase_requests/notifications"


class DashboardNotificationsState(rx.State):
    enabled: bool = NOTIFICATIONS_ENABLED
    loaded: bool = False
    loading: bool = False
    error: str = ""
    items: list[dict[str, str | int | bool]] = []
    unread_count: int | None = None
    page: int = 1
    per_page: int = 10
    has_previous: bool = False
    has_next: bool = False
    owner_user_id: int = 0
    global_scope: bool = False
    _session_fingerprint: str = ""
    retry_after_epoch: float = 0.0
    panel_open: bool = False
    _failed_append: bool = False
    _opening_history_id: int = 0

    @rx.var
    def badge_label(self) -> str:
        count = self.unread_count or 0
        return "9+" if count >= 10 else str(count)

    def set_panel_open(self, value: bool):
        if value and not self.panel_open:
            self._opening_history_id = 0
        self.panel_open = value

    async def load_page(self):
        async for event in self._load_page():
            yield event

    async def _load_page(self, append: bool = False, expected_page: int = 0):
        if self.loading:
            return
        auth = await self.get_state(AuthState)
        if not auth.session_is_valid:
            self.items = []
            self.unread_count = None
            self.loaded = False
            self.owner_user_id = 0
            self.has_previous = False
            self.has_next = False
            self._session_fingerprint = ""
            self.error = "Sessão não validada."
            return
        if not auth.has_permission("purchase_request.read"):
            self.items = []
            self.unread_count = None
            self.loaded = True
            self.owner_user_id = 0
            self.has_previous = False
            self.has_next = False
            self._session_fingerprint = ""
            self.error = "Sem acesso às solicitações."
            return
        if not self.enabled:
            self.items = []
            self.unread_count = None
            self.loaded = True
            self.owner_user_id = 0
            self.has_previous = False
            self.has_next = False
            self._session_fingerprint = ""
            self.error = "Integração aguardando publicação do contrato Xano."
            return
        token = str(auth.auth_token or "").strip()
        fingerprint = _session_signature(auth)
        if fingerprint != self._session_fingerprint:
            self.items = []
            self.unread_count = None
            self.loaded = False
            self.error = ""
            self.page = 1
            self.has_previous = False
            self.has_next = False
            self._session_fingerprint = fingerprint
            self.retry_after_epoch = 0.0
            self._failed_append = False
            self._opening_history_id = 0
        if append and (not self.panel_open or not self.loaded or not self.has_next
                       or self.error or self._failed_append or expected_page != self.page):
            return
        target_page = self.page + 1 if append else 1
        scope = "notifications:global" if auth.has_permission("purchase_request.manage") else "notifications:own"
        key = session_read_cache.key(scope, NOTIFICATION_ENDPOINT, token, {"page": target_page, "per_page": self.per_page})
        cached, fresh = session_read_cache.get(key, NOTIFICATION_TTL, allow_stale=True)
        if self.loading or (not append and self.loaded and (fresh or self.error)) or self.retry_after_epoch > time.time():
            return
        self.loading = True
        yield
        try:
            data = cached if fresh else await auth_client.get_purchase_request_notifications(token, page=target_page, per_page=self.per_page)
            latest = await self.get_state(AuthState)
            if not latest.session_is_valid or not latest.has_permission("purchase_request.read") or _session_signature(latest) != fingerprint:
                self.items = []
                self.unread_count = None
                self.owner_user_id = 0
                self.loaded = False
                return
            if data["curPage"] != target_page or data["perPage"] != self.per_page:
                raise XanoServerError("O Xano retornou uma página de notificações diferente da solicitada.", status_code=200)
            if not fresh:
                session_read_cache.set(key, data, NOTIFICATION_TTL)
            incoming = [
                {
                    "history_id": int(item["history_id"]),
                    "purchase_request_id": int(item["purchase_request_id"]),
                    "evento": str(item["evento"]),
                    "descricao": _notification_description(str(item["evento"]), int(item["purchase_request_id"]), item.get("status_novo")),
                    "data_formatada": datetime.fromtimestamp(float(item["data_evento"]) / 1000, ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M"),
                    "lida": bool(item["lida"]),
                }
                for item in data["items"]
            ]
            # Offset pagination can overlap when new events arrive between GETs.
            # Keep the confirmed order and read state of already displayed events.
            merged = list(self.items) if append else []
            existing_ids = {item["history_id"] for item in merged}
            for item in incoming:
                if item["history_id"] not in existing_ids:
                    merged.append(item)
                    existing_ids.add(item["history_id"])
            self.items = merged
            self.page = target_page
            self.unread_count = int(data["unreadTotal"])
            self.owner_user_id = int(auth.user_id)
            self.global_scope = auth.has_permission("purchase_request.manage")
            self.has_previous = int(data["curPage"]) > 1
            self.has_next = int(data["curPage"]) * int(data["perPage"]) < int(data["itemsTotal"])
            self.error = ""
            self.loaded = True
            self._failed_append = False
        except XanoAuthError:
            self.error = "Sessão expirada."
            yield AuthState.logout
        except XanoPermissionError:
            self.items = []
            self.unread_count = None
            self.error = "Sem autorização para consultar notificações."
            self.loaded = True
            self.has_next = False
        except XanoError as exc:
            logger.warning(
                "Dashboard notifications unavailable: endpoint=GET /purchase_requests/notifications "
                "exception_type=%s status=%s origin=%s contract_field=%s expected=%s found_type=%s",
                type(exc).__name__, getattr(exc, "status_code", None), getattr(exc, "origin", None),
                getattr(exc, "contract_field", None), getattr(exc, "contract_expected", None),
                getattr(exc, "contract_found_type", None),
            )
            self.error = (
                _DASHBOARD_CONFIG_ERRORS[exc.error_code]
                if isinstance(exc, XanoRequestError) and exc.error_code in _DASHBOARD_CONFIG_ERRORS
                else "Não foi possível carregar as notificações."
            )
            self.loaded = True
            self._failed_append = append
            if getattr(exc, "status_code", None) == 429:
                from ..pages.dashboard import _retry_delay_seconds
                self.retry_after_epoch = time.time() + _retry_delay_seconds(exc)
        finally:
            self.loading = False

    async def mark_read(self, history_id: int):
        if self._opening_history_id:
            return
        async for event in self._mark_read(history_id):
            yield event

    async def _mark_read(self, history_id: int):
        if not self.enabled or self.loading or self.retry_after_epoch > time.time():
            return
        auth = await self.get_state(AuthState)
        if (not auth.session_is_valid or not auth.has_permission("purchase_request.read")
                or _session_signature(auth) != self._session_fingerprint or self.owner_user_id != auth.user_id):
            self.error = "Sem autorização para marcar esta notificação."
            return
        item = next((row for row in self.items if row["history_id"] == history_id), None)
        if self.loading or not item or item["lida"]:
            return
        self.loading = True
        token = str(auth.auth_token)
        fingerprint = _session_signature(auth)
        yield
        try:
            await auth_client.mark_purchase_request_notification_read(token, history_id)
            session_read_cache.invalidate(endpoint=NOTIFICATION_ENDPOINT, token=token)
            latest = await self.get_state(AuthState)
            if not latest.session_is_valid or not latest.has_permission("purchase_request.read") or _session_signature(latest) != fingerprint:
                self.items = []
                self.unread_count = None
                self.owner_user_id = 0
                return
            item["lida"] = True
            self.items = list(self.items)
            self.unread_count = max(0, (self.unread_count or 0) - 1)
            if not self._failed_append:
                self.error = ""
        except XanoAuthError:
            yield AuthState.logout
        except XanoError as exc:
            logger.warning("Notification read update failed: exception_type=%s status=%s", type(exc).__name__, getattr(exc, "status_code", None))
            self.error = "Não foi possível marcar a notificação como lida."
            if getattr(exc, "status_code", None) == 429:
                from ..pages.dashboard import _retry_delay_seconds
                self.retry_after_epoch = time.time() + _retry_delay_seconds(exc)
        finally:
            self.loading = False

    async def open_notification(self, history_id: int):
        if not self.enabled or self.loading or self._opening_history_id:
            return
        auth = await self.get_state(AuthState)
        if (not auth.session_is_valid or not auth.has_permission("purchase_request.read")
                or _session_signature(auth) != self._session_fingerprint or self.owner_user_id != auth.user_id):
            self.error = "Sem autorização para abrir esta notificação."
            return
        item = next((row for row in self.items if row["history_id"] == history_id), None)
        if not item or type(item["purchase_request_id"]) is not int or item["purchase_request_id"] <= 0:
            return
        if self.loading or self._opening_history_id:
            return
        self._opening_history_id = history_id
        fingerprint = self._session_fingerprint
        logout_requested = False
        if not item["lida"]:
            async for event in self._mark_read(history_id):
                if event is not None:
                    logout_requested = True
                yield event
        latest = await self.get_state(AuthState)
        if (logout_requested or not latest.session_is_valid
                or not latest.has_permission("purchase_request.read")
                or _session_signature(latest) != fingerprint):
            return
        self.panel_open = False
        # Keep the click latch until the panel is opened again: queued duplicate
        # clicks must not repeat a failed/ambiguous read attempt after redirect.
        yield rx.redirect(f"/compras/{item['purchase_request_id']}")

    def reload(self):
        if self.loading or self.retry_after_epoch > time.time():
            return
        self.error = ""
        if self._failed_append:
            self._failed_append = False
            return DashboardNotificationsState.load_more(self.page)
        self.loaded = False
        return DashboardNotificationsState.load_page

    async def load_more(self, expected_page: int):
        async for event in self._load_page(True, expected_page):
            yield event

    async def on_list_scroll(self, position: dict):
        # The browser supplies only geometry and a rendered page number, no data.
        # A queued event for an already consumed page must not fetch the next one.
        if not isinstance(position, dict) or position.get("near_end") is not True:
            return
        expected_page = position.get("page")
        if type(expected_page) is not int:
            return
        async for event in self.load_more(expected_page):
            yield event


def _notification_description(event: str, request_id: int, status: str | None = None) -> str:
    labels = {
        "criada": "Solicitação criada",
        "status_alterado": "Status da solicitação alterado",
        "cancelada": "Solicitação cancelada",
        "rejeitada": "Solicitação rejeitada",
        "recebimento_registrado": "Recebimento registrado",
    }
    label = labels.get(event, "Evento da solicitação")
    if event == "recebimento_registrado" and status == "concluida":
        label = "Solicitação concluída por recebimento"
    return f"{label} · pedido #{request_id}"


def _session_signature(auth) -> str:
    scope = "global" if auth.has_permission("purchase_request.manage") else "own"
    return hashlib.sha256(f"{str(auth.auth_token or '').strip()}:{scope}".encode("utf-8")).hexdigest()
