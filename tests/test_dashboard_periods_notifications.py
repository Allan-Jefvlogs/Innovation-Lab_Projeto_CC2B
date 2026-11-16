"""Calendário e estados com mocks; não executa XanoScript nem acessa o Xano."""

import unittest
import httpx
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages import dashboard
from Meu_projeto.services.dashboard_periods import SP, expected_keys, period_bounds, timestamp_milliseconds
from Meu_projeto.services.session_read_cache import session_read_cache, CACHE_MISS
from Meu_projeto.services.xano_client import XanoAuthClient, XanoServerError, XanoRequestError, auth_client
from Meu_projeto.state.dashboard_notifications import DashboardNotificationsState, _notification_description


def state(cls):
    obj = object.__new__(cls)
    obj._init_bookkeeping()
    return obj


def payload(period="7d", now=None):
    start, end = period_bounds(period, now)
    keys = expected_keys(period, start, end)
    return {"serie": [{"dia": key, "entradas": 0, "saidas": 0} for key in keys],
            "recentes": {"items": [], "curPage": 1, "perPage": 5}}


def auth(token="local-session", manage=True):
    return SimpleNamespace(session_is_valid=True, auth_token=token, user_id=4,
                           has_permission=lambda code: code == "purchase_request.read" or (manage and code == "purchase_request.manage"))


def notification():
    return {"items": [{"history_id": 8, "purchase_request_id": 11, "evento": "recebimento_registrado",
                       "status_novo": "concluida", "descricao": "Recebimento", "data_evento": 1000, "lida": False}],
            "curPage": 1, "perPage": 10, "itemsTotal": 1, "unreadTotal": 1}


async def drain(events):
    async for _ in events:
        pass


class CalendarTests(unittest.TestCase):
    def test_wire_timestamps_preserve_local_midnight_across_month_and_year(self):
        now = datetime(2026, 1, 1, 14, tzinfo=SP)
        for period, first, last in (("7d", "2025-12-26", "2026-01-01"), ("30d", "2025-12-03", "2026-01-01"), ("12m", "2025-02", "2026-01")):
            start, end = period_bounds(period, now)
            keys = expected_keys(period, start, end)
            self.assertEqual((keys[0], keys[-1]), (first, last))
            for boundary in (start, end):
                ms = timestamp_milliseconds(boundary)
                local = datetime.fromtimestamp(ms / 1000, SP)
                self.assertEqual((local.hour, local.minute, local.second, local.microsecond), (0, 0, 0, 0))
        with self.assertRaises(ValueError):
            timestamp_milliseconds("2026-01-01T00:00:00")

    def test_marker_validation_is_separate_and_precedes_history_access(self):
        root = Path(__file__).resolve().parents[1] / "xano/api/inventory_stock"
        for name in ("purchase_requests_notifications_get.xs", "purchase_requests_notifications_by_id_read_patch.xs"):
            xs = (root / name).read_text(encoding="utf-8")
            for code in ("MISSING", "EMPTY", "INVALID", "CONVERSION_FAILED"):
                self.assertIn("NOTIFICATIONS_ACTIVATION_MARKER_" + code, xs)
            self.assertIn("precondition ($activation_raw !== null)", xs)
            self.assertIn("value = $activation_text|to_int", xs)
            self.assertIn("data_evento >= $activation_at", xs)
            self.assertLess(xs.index("NOTIFICATIONS_ACTIVATION_MARKER_CONVERSION_FAILED"), xs.index("purchase_request_history {"))
            self.assertNotIn("debug.log", xs)

    def test_local_visual_changes_keep_lines_and_bound_notification_width(self):
        root = Path(__file__).resolve().parents[1] / "Meu_projeto/components"
        chart = (root / "stock_movement_chart.py").read_text(encoding="utf-8")
        layout = (root / "layout.py").read_text(encoding="utf-8")
        self.assertNotIn("rx.select.root", chart)
        self.assertEqual(chart.count("rx.recharts.line("), 2)
        self.assertIn('aria_pressed=period == value', chart)
        self.assertIn('box_sizing="border-box", overflow_x="hidden"', layout)
        self.assertIn('min_width="0", overflow_wrap="anywhere"', layout)

    def test_thirty_days_cross_leap_day(self):
        start, end = period_bounds("30d", datetime(2024, 3, 1, 15, tzinfo=SP))
        keys = expected_keys("30d", start, end)
        self.assertEqual((len(keys), keys[0], keys[-1]), (30, "2024-02-01", "2024-03-01"))
        self.assertIn("2024-02-29", keys)

    def test_months_cross_year_and_include_current_calendar_month(self):
        start, end = period_bounds("12m", datetime(2026, 1, 15, tzinfo=SP))
        keys = expected_keys("12m", start, end)
        self.assertEqual((len(keys), keys[0], keys[-1]), (12, "2025-02", "2026-01"))
        self.assertEqual(datetime.fromisoformat(end).astimezone(SP).day, 1)

    def test_invalid_period_and_mismatched_boundaries(self):
        with self.assertRaises(ValueError):
            period_bounds("forever")
        start, end = period_bounds("7d")
        with self.assertRaises(ValueError):
            expected_keys("30d", start, end)

    def test_xano_uses_only_two_queries_and_counts_monthly_without_quantities(self):
        xs = (Path(__file__).resolve().parents[1] / "xano/api/inventory_stock/movements_dashboard_get.xs").read_text(encoding="utf-8")
        self.assertEqual(xs.count("db.query inventory_movement"), 2)
        self.assertNotIn("db.direct_query", xs)
        self.assertIn('transform_timestamp:"+1 month":"America/Sao_Paulo"', xs)
        self.assertIn('format_timestamp:"Y-m":"America/Sao_Paulo"', xs)


class PeriodClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_periods_validate_dates_and_preserve_zeros(self):
        client = XanoAuthClient()
        for period in ("7d", "30d", "12m"):
            start, end = period_bounds(period)
            data = payload(period)
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=data)) as get:
                result = await client.get_dashboard_movements("local-token", date_from=start, date_to=end, period=period)
            get.assert_awaited_once()
            self.assertEqual(get.await_args.kwargs["params"]["period"], period)
            self.assertEqual(get.await_args.kwargs["params"]["date_from"], timestamp_milliseconds(start))
            self.assertEqual(get.await_args.kwargs["params"]["date_to"], timestamp_milliseconds(end))
            self.assertEqual(result, data)

    async def test_real_dashboard_error_envelopes_preserve_sanitized_codes(self):
        client = XanoAuthClient()
        start, end = period_bounds()
        errors = [(400, "DATE_RANGE_MUST_START_AT_LOCAL_MIDNIGHT")] + [
            (500, "NOTIFICATIONS_ACTIVATION_MARKER_" + suffix)
            for suffix in ("MISSING", "EMPTY", "INVALID", "CONVERSION_FAILED")
        ]
        for status, code in errors:
            response = httpx.Response(status, json={"code": "ERROR_CODE_INPUT_ERROR" if status == 400 else "ERROR_FATAL", "message": code, "payload": ""})
            with patch.object(client, "_send_request", new=AsyncMock(return_value=response)) as send:
                with self.assertRaises(XanoRequestError) as caught:
                    if status == 400:
                        await client.get_dashboard_movements("local-token", date_from=start, date_to=end)
                    else:
                        await client.get_purchase_request_notifications("local-token")
            self.assertEqual(caught.exception.error_code, code)
            send.assert_awaited_once()

    async def test_reordered_duplicated_or_missing_dates_are_not_accepted(self):
        client = XanoAuthClient()
        start, end = period_bounds("30d")
        valid = payload("30d")
        for series in (valid["serie"][:-1], list(reversed(valid["serie"])), [valid["serie"][0]] * 30):
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value={**valid, "serie": series})):
                with self.assertRaises(XanoServerError):
                    await client.get_dashboard_movements("local-token", date_from=start, date_to=end, period="30d")

    async def test_period_switch_caches_by_period_and_does_not_query_other_cards(self):
        session_read_cache.clear()
        obj = state(dashboard.DashboardState)
        obj.chart_enabled = True
        obj.chart_period = "7d"
        object.__setattr__(obj, "_session", AsyncMock(return_value=("period-session", {"movements": True})))

        async def get(token, **params):
            return payload(params["period"])

        with patch.object(dashboard, "REAL_DASHBOARD_MOVEMENTS_ENABLED", True), patch.object(auth_client, "get_dashboard_movements", new=AsyncMock(side_effect=get)) as get_chart, patch.object(auth_client, "list_products", new=AsyncMock()) as products:
            await drain(obj.change_chart_period("30d"))
            self.assertEqual(len(obj.chart_data), 30)
            await drain(obj.change_chart_period("30d"))
            await drain(obj.change_chart_period("12m"))
            self.assertEqual(len(obj.chart_data), 12)
            await drain(obj.change_chart_period("30d"))
        self.assertEqual(get_chart.await_count, 2)
        products.assert_not_awaited()
        session_read_cache.clear()

    async def test_chart_429_blocks_immediate_period_retry(self):
        obj = state(dashboard.DashboardState)
        obj.chart_enabled = True
        object.__setattr__(obj, "_session", AsyncMock(return_value=("rate-session", {"movements": True})))
        error = XanoRequestError("limit", "TOO_MANY_REQUESTS", 429, {}, retry_after="20")
        with patch.object(auth_client, "get_dashboard_movements", new=AsyncMock(side_effect=error)) as get:
            await drain(obj.change_chart_period("30d"))
            await drain(obj.change_chart_period("12m"))
        get.assert_awaited_once()
        self.assertEqual(obj.chart_data, [])


class NotificationStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_activation_error_does_not_turn_into_empty_notifications(self):
        obj = self.notification_state()
        error = XanoRequestError("internal", "NOTIFICATIONS_ACTIVATION_MARKER_MISSING", 500, {})
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=error)) as get:
            await drain(obj.load_page())
            await drain(obj.load_page())
        self.assertIn("marco", obj.error)
        self.assertIsNone(obj.unread_count)
        get.assert_awaited_once()

    async def test_confirmed_empty_page_is_distinct_from_error(self):
        obj = self.notification_state()
        data = {"items": [], "curPage": 1, "perPage": 10, "itemsTotal": 0, "unreadTotal": 0}
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=data)):
            await drain(obj.load_page())
        self.assertEqual(obj.items, [])
        self.assertEqual(obj.unread_count, 0)
        self.assertEqual(obj.error, "")

    def setUp(self):
        session_read_cache.clear()

    def tearDown(self):
        session_read_cache.clear()

    def notification_state(self):
        obj = state(DashboardNotificationsState)
        obj.enabled = True
        return obj

    async def test_real_contract_is_cached_and_read_waits_for_confirmation(self):
        obj = self.notification_state()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=notification())) as get, patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 8, "lida": True})) as mark:
            await drain(obj.load_page())
            await drain(obj.load_page())
            self.assertEqual(obj.unread_count, 1)
            self.assertIn("concluída", obj.items[0]["descricao"])
            await drain(obj.mark_read(8))
            self.assertTrue(obj.items[0]["lida"])
            self.assertEqual(obj.unread_count, 0)
        get.assert_awaited_once()
        mark.assert_awaited_once()

    async def test_session_change_while_reading_discards_private_result(self):
        obj = self.notification_state()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(side_effect=[auth(), auth("other-token")])), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=notification())):
            await drain(obj.load_page())
        self.assertEqual(obj.items, [])
        self.assertIsNone(obj.unread_count)

    async def test_scope_downgrade_refetches_instead_of_reusing_global_cache(self):
        obj = self.notification_state()
        current = auth()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(side_effect=lambda _: current)), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=notification())) as get:
            await drain(obj.load_page())
            current = auth(manage=False)
            await drain(obj.load_page())
        self.assertEqual(get.await_count, 2)
        self.assertFalse(obj.global_scope)

    async def test_notification_429_is_not_retried_by_reopening_bell(self):
        obj = self.notification_state()
        error = XanoRequestError("limit", "TOO_MANY_REQUESTS", 429, {}, retry_after="20")
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=error)) as get:
            await drain(obj.load_page())
            await drain(obj.load_page())
            self.assertIsNone(obj.reload())
        get.assert_awaited_once()
        self.assertIsNone(obj.unread_count)

    async def test_invalid_read_confirmation_does_not_mark_locally(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"history_id": 8, "lida": False})):
            with self.assertRaises(XanoServerError):
                await client.mark_purchase_request_notification_read("local-token", 8)

    def test_receipt_without_persisted_final_status_does_not_claim_conclusion(self):
        self.assertNotIn("concluída", _notification_description("recebimento_registrado", 11))
