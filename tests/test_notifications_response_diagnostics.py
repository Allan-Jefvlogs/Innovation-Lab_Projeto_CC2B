"""Response-contract diagnostics using mocks; no remote requests or writes."""

import copy
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from Meu_projeto.services.xano_client import XanoAuthClient, XanoServerError, XanoRateLimitError, auth_client
from Meu_projeto.state.dashboard_notifications import DashboardNotificationsState
from tests.test_dashboard_periods_notifications import auth, drain, notification, state
from Meu_projeto.services.session_read_cache import session_read_cache


class NotificationResponseDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def test_status_projection_selects_nested_scalar_without_exporting_metadata(self):
        xs = (Path(__file__).resolve().parents[1] / "xano/api/inventory_stock/purchase_requests_notifications_get.xs").read_text(encoding="utf-8")
        self.assertIn("status_novo: $notification.dados.status_novo,", xs)
        self.assertNotIn('status_novo: $notification.dados|get:', xs)
        self.assertNotIn("status_novo: $notification.dados,", xs)

    async def test_status_metadata_object_is_rejected_but_scalar_and_null_are_accepted(self):
        client = XanoAuthClient()
        metadata = {"status_anterior": "aberta", "status_novo": "em_analise"}
        for value in (None, "em_analise", "concluida", metadata):
            data = copy.deepcopy(notification())
            data["items"][0]["status_novo"] = value
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)):
                if isinstance(value, dict):
                    with self.assertRaises(XanoServerError) as caught:
                        await client.get_purchase_request_notifications("private-test-token")
                    self.assertEqual(caught.exception.contract_field, "items[].status_novo")
                    self.assertEqual(caught.exception.contract_found_type, "dict")
                else:
                    self.assertIs(await client.get_purchase_request_notifications("private-test-token"), data)

    async def test_empty_and_populated_contracts_preserve_all_values(self):
        client = XanoAuthClient()
        for data in (
            {"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 10, "unreadTotal": 0},
            notification(),
            {**notification(), "items": [{**notification()["items"][0], "lida": True}], "unreadTotal": 0},
        ):
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as get:
                self.assertIs(await client.get_purchase_request_notifications("private-test-token"), data)
            get.assert_awaited_once()

    async def test_invalid_fields_report_only_fixed_path_and_type(self):
        client = XanoAuthClient()
        cases = []
        for field in ("itemsTotal", "curPage", "perPage", "unreadTotal"):
            for value in (None, "private-response-value", False):
                data = copy.deepcopy(notification())
                data[field] = value
                cases.append((data, field, type(value).__name__))
            data = copy.deepcopy(notification())
            del data[field]
            cases.append((data, field, "missing"))
        cases.append(({**notification(), "items": [None]}, "items[]", "NoneType"))
        for field in ("history_id", "purchase_request_id", "descricao", "evento", "data_evento", "lida"):
            data = copy.deepcopy(notification())
            del data["items"][0][field]
            cases.append((data, f"items[].{field}", "missing"))
        for value in (None, 0, 1, "false"):
            data = copy.deepcopy(notification())
            data["items"][0]["lida"] = value
            cases.append((data, "items[].lida", type(value).__name__))
        data = copy.deepcopy(notification())
        data["items"][0]["status_novo"] = "private-response-value"
        cases.append((data, "items[].status_novo", "str"))
        for data, field, found in cases:
            with self.subTest(field=field, found=found):
                with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as get:
                    with self.assertRaises(XanoServerError) as caught:
                        await client.get_purchase_request_notifications("private-test-token")
                error = caught.exception
                self.assertEqual(error.status_code, 200)
                self.assertEqual(error.origin, "response_contract")
                self.assertEqual((error.contract_field, error.contract_found_type), (field, found))
                self.assertEqual(error.payload, {})
                self.assertNotIn("private-response-value", str(error))
                self.assertNotIn("private-test-token", str(error))
                get.assert_awaited_once()

    async def test_diagnostic_log_is_sanitized_and_invalid_response_is_not_cached_as_empty(self):
        session_read_cache.clear()
        obj = state(DashboardNotificationsState)
        obj.enabled = True
        client = XanoAuthClient()
        malformed = notification()
        malformed["items"][0]["lida"] = "private-response-value"
        try:
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=malformed)):
                with self.assertRaises(XanoServerError) as caught:
                    await client.get_purchase_request_notifications("private-test-token")
            with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
                 patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=caught.exception)) as get, \
                 self.assertLogs("Meu_projeto.state.dashboard_notifications", level="WARNING") as logs:
                await drain(obj.load_page())
                await drain(obj.load_page())
            output = " ".join(logs.output)
            for expected in ("status=200", "origin=response_contract", "contract_field=items[].lida", "found_type=str"):
                self.assertIn(expected, output)
            for secret in ("private-test-token", "private-response-value", "Authorization", "Bearer"):
                self.assertNotIn(secret, output)
            self.assertIsNone(obj.unread_count)
            self.assertTrue(obj.error)
            get.assert_awaited_once()
        finally:
            session_read_cache.clear()

    async def test_local_rate_limit_keeps_cooldown_and_does_not_retry_on_bell_open(self):
        session_read_cache.clear()
        obj = state(DashboardNotificationsState)
        obj.enabled = True
        try:
            with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
                 patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=XanoRateLimitError(20))) as get:
                await drain(obj.load_page())
                await drain(obj.load_page())
                self.assertIsNone(obj.reload())
            get.assert_awaited_once()
            self.assertIsNone(obj.unread_count)
        finally:
            session_read_cache.clear()
