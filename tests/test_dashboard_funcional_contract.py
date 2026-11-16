from __future__ import annotations

import inspect
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from Meu_projeto.pages import dashboard
from Meu_projeto.state.dashboard_notifications import DashboardNotificationsState
from Meu_projeto.services.xano_client import XanoServerError, auth_client


ROOT = Path(__file__).resolve().parents[1]


class DashboardFunctionalContractTests(unittest.TestCase):
    def test_greeting_uses_sao_paulo_period_boundaries(self):
        self.assertEqual(dashboard._greeting_for_hour(4), "Boa noite")
        self.assertEqual(dashboard._greeting_for_hour(5), "Bom dia")
        self.assertEqual(dashboard._greeting_for_hour(11), "Bom dia")
        self.assertEqual(dashboard._greeting_for_hour(12), "Boa tarde")
        self.assertEqual(dashboard._greeting_for_hour(17), "Boa tarde")
        self.assertEqual(dashboard._greeting_for_hour(18), "Boa noite")

    def test_period_has_seven_civil_days_in_sao_paulo(self):
        now = datetime(2026, 11, 11, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        start_raw, end_raw = dashboard._dashboard_period(now)
        start = datetime.fromisoformat(start_raw).astimezone(ZoneInfo("America/Sao_Paulo"))
        end = datetime.fromisoformat(end_raw).astimezone(ZoneInfo("America/Sao_Paulo"))
        self.assertEqual(start, datetime(2026, 11, 5, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo")))
        self.assertEqual(end, datetime(2026, 11, 12, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo")))

    def test_dashboard_projection_keeps_operation_counts_and_empty_days(self):
        series = [
            {"dia": f"2026-11-{day:02d}", "entradas": 3 if day == 7 else 0, "saidas": 2 if day == 8 else 0}
            for day in range(5, 12)
        ]
        payload = {
            "serie": series,
            "recentes": {
                "items": [],
                "curPage": 1,
                "perPage": 5,
            },
        }
        projected = dashboard._project_dashboard_movements(payload)
        self.assertEqual(len(projected["serie"]), 7)
        self.assertEqual(projected["serie"][0], {"dia": "05/11", "entradas": 0, "saidas": 0})
        self.assertEqual(projected["serie"][2]["entradas"], 3)
        self.assertEqual(projected["serie"][3]["saidas"], 2)

    def test_dashboard_rejects_incomplete_or_invalid_series(self):
        recent = {"items": [], "curPage": 1, "perPage": 5}
        with self.assertRaises(XanoServerError):
            dashboard._project_dashboard_movements({"serie": [], "recentes": recent})
        series = [{"dia": "2026-11-05", "entradas": True, "saidas": 0}] * 7
        with self.assertRaises(XanoServerError):
            dashboard._project_dashboard_movements({"serie": series, "recentes": recent})

    def test_notification_contract_enforces_scope_marker_and_read_receipt(self):
        list_xs = (ROOT / "xano/api/inventory_stock/purchase_requests_notifications_get.xs").read_text(encoding="utf-8")
        read_xs = (ROOT / "xano/api/inventory_stock/purchase_requests_notifications_by_id_read_patch.xs").read_text(encoding="utf-8")
        scope_xs = (ROOT / "xano/function/inventory/purchase_request_notification_all_access.xs").read_text(encoding="utf-8")
        self.assertIn('permission_code: "purchase_request.read"', list_xs)
        self.assertIn("$scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id", list_xs)
        self.assertIn("NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT", list_xs)
        self.assertIn("purchase_request_notification_read.user_id == $auth.id", read_xs)
        self.assertIn("purchase_request_notification_read.history_id == $history.id", read_xs)
        self.assertIn("$auth.id", read_xs)
        self.assertIn('"purchase_request.manage"', scope_xs)
        self.assertNotIn('"email_status_alterado"', list_xs)

    def test_notifications_are_paginated_without_polling(self):
        state_source = (ROOT / "Meu_projeto/state/dashboard_notifications.py").read_text(encoding="utf-8")
        self.assertIn('"page": target_page, "per_page": self.per_page', state_source)
        self.assertIn("def load_more", state_source)
        self.assertIn("def on_list_scroll", state_source)
        self.assertNotIn("def previous_page", state_source)
        self.assertNotIn("set_interval", state_source)

    def test_user_password_contract_checks_current_password_and_redacts_fields(self):
        endpoint = (ROOT / "xano/api/authentication/auth/change_password_PATCH.xs").read_text(encoding="utf-8")
        frontend = (ROOT / "Meu_projeto/pages/account_password.py").read_text(encoding="utf-8")
        client_source = inspect.getsource(__import__("Meu_projeto.services.xano_client", fromlist=["_SENSITIVE_LOG_KEYS"]))
        self.assertIn("security.check_password", endpoint)
        self.assertIn("$auth.id", endpoint)
        self.assertIn('"current_password"', client_source)
        self.assertIn('"confirm_password"', client_source)
        self.assertNotIn("logger.", endpoint)
        self.assertIn('NEXSTOCK_ACCOUNT_PASSWORD_ENABLED", "false"', frontend)
        self.assertIn("if self.saving or not self.enabled", frontend)

    def test_search_placeholder_removed_and_notifications_dont_poll(self):
        layout_source = (ROOT / "Meu_projeto/components/layout.py").read_text(encoding="utf-8")
        self.assertNotIn("rx.input(", inspect.getsource(__import__("Meu_projeto.components.layout", fromlist=["_topbar"])._topbar))
        self.assertIn("DashboardNotificationsState.mark_read", layout_source)
        self.assertNotIn("set_interval", layout_source)


class DashboardClientContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_notifications_require_pagination_and_typed_items(self):
        valid = {
            "items": [{"history_id": 4, "purchase_request_id": 2, "evento": "criada", "descricao": "Solicitação criada", "data_evento": 1000, "lida": False}],
            "curPage": 1,
            "perPage": 10,
            "itemsTotal": 1,
            "unreadTotal": 1,
        }
        with patch.object(auth_client, "_inventory_request", new=AsyncMock(return_value=valid)):
            result = await auth_client.get_purchase_request_notifications("opaque-token")
        self.assertEqual(result["unreadTotal"], 1)

        invalid = {**valid, "curPage": None}
        with patch.object(auth_client, "_inventory_request", new=AsyncMock(return_value=invalid)):
            with self.assertRaises(XanoServerError):
                await auth_client.get_purchase_request_notifications("opaque-token")

    async def test_real_movement_series_requires_seven_distinct_days(self):
        payload = {
            "serie": [{"dia": f"2026-11-{day:02d}", "entradas": 0, "saidas": 0} for day in range(5, 12)],
            "recentes": {"items": [], "curPage": 1, "perPage": 5},
        }
        with patch.object(auth_client, "_inventory_request", new=AsyncMock(return_value=payload)):
            result = await auth_client.get_dashboard_movements("opaque-token", date_from="2026-11-05T03:00:00Z", date_to="2026-11-12T03:00:00Z")
        self.assertEqual(len(result["serie"]), 7)
        malformed = {**payload, "serie": payload["serie"][:-1]}
        with patch.object(auth_client, "_inventory_request", new=AsyncMock(return_value=malformed)):
            with self.assertRaises(XanoServerError):
                await auth_client.get_dashboard_movements("opaque-token", date_from="2026-11-05T03:00:00Z", date_to="2026-11-12T03:00:00Z")

    async def test_notifications_do_not_call_xano_without_read_grant(self):
        state = object.__new__(DashboardNotificationsState)
        DashboardNotificationsState._init_bookkeeping(state)
        state.enabled = True
        state.loaded = False
        state.loading = False
        state.error = ""
        state.items = []
        state.unread_count = None
        state.page = 1
        state.per_page = 10
        state.has_previous = False
        state.has_next = False
        state._session_fingerprint = ""
        auth = SimpleNamespace(session_is_valid=True, auth_token="opaque-token", has_permission=lambda _: False)
        with (
            patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth)),
            patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock()) as get_notifications,
        ):
            async for _ in state.load_page():
                pass
        get_notifications.assert_not_awaited()
        self.assertIsNone(state.unread_count)
        self.assertEqual(state.items, [])


if __name__ == "__main__":
    unittest.main()
