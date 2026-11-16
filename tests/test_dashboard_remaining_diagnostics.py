"""Regressões locais; não executa endpoints nem comprova o retorno publicado."""

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages import dashboard
from Meu_projeto.services.dashboard_periods import expected_keys, period_bounds
from Meu_projeto.services.xano_client import XanoAuthClient, XanoServerError


class RemainingDashboardDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def test_dense_axis_keeps_daily_data_and_two_lines(self):
        source = (Path(__file__).resolve().parents[1] / "Meu_projeto/components/stock_movement_chart.py").read_text(encoding="utf-8")
        self.assertIn('min_tick_gap=rx.cond(period == "30d", 20, 8)', source)
        self.assertIn('interval="preserveStartEnd"', source)
        self.assertEqual(source.count("rx.recharts.line("), 2)
        self.assertIn('data=data,', source)

    async def test_five_global_recent_rows_survive_all_chart_periods(self):
        client = XanoAuthClient()
        # Deliberadamente anteriores ao gráfico: recentes não são filtrados pelo frontend.
        rows = [{"id": i, "tipo": "entrada", "product_name": "Teste local",
                 "quantidade": 1, "data_hora": 1000, "user_name": "Teste"}
                for i in range(5, 0, -1)]
        for period in ("7d", "30d", "12m"):
            start, end = period_bounds(period)
            payload = {"serie": [{"dia": key, "entradas": 0, "saidas": 0}
                                 for key in expected_keys(period, start, end)],
                       "recentes": {"items": rows, "curPage": 1, "perPage": 5}}
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)) as get:
                result = await client.get_dashboard_movements("local-test-token", date_from=start, date_to=end, period=period)
            self.assertEqual(len(dashboard._project_dashboard_movements(result, period)["items"]), 5)
            get.assert_awaited_once()

    async def test_invalid_recent_rows_are_not_silently_discarded(self):
        with self.assertRaises(XanoServerError):
            dashboard.DashboardState._project_movements({"items": [None]})
        start, end = period_bounds()
        payload = {"serie": [{"dia": key, "entradas": 0, "saidas": 0}
                             for key in expected_keys("7d", start, end)],
                   "recentes": {"items": ["sensitive-invalid-value"], "curPage": 1, "perPage": 5}}
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)), self.assertLogs("Meu_projeto.services.xano_client", level="WARNING") as logs:
            with self.assertRaises(XanoServerError):
                await client.get_dashboard_movements("local-test-token", date_from=start, date_to=end)
        self.assertNotIn("sensitive-invalid-value", " ".join(logs.output))

    async def test_empty_recent_with_real_counts_reports_only_contract_metadata(self):
        start, end = period_bounds()
        payload = {"serie": [{"dia": key, "entradas": 1, "saidas": 0}
                             for key in expected_keys("7d", start, end)],
                   "recentes": {"items": [], "curPage": 1, "perPage": 5}}
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)), self.assertLogs("Meu_projeto.services.xano_client", level="WARNING") as logs:
            result = await client.get_dashboard_movements("do-not-log-token", date_from=start, date_to=end)
        self.assertEqual(result, payload)
        self.assertIn("recent_items=0", " ".join(logs.output))
        self.assertNotIn("do-not-log-token", " ".join(logs.output))

    async def test_summary_missing_field_remains_error_with_safe_diagnostic(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value={"private": "do-not-log"})), self.assertLogs("Meu_projeto.services.xano_client", level="WARNING") as logs:
            with self.assertRaises(XanoServerError) as caught:
                await client.get_purchase_requests_summary("do-not-log-token")
        self.assertEqual(caught.exception.origin, "response_contract")
        self.assertEqual(caught.exception.status_code, 200)
        self.assertIn("found_type=missing", " ".join(logs.output))
        self.assertNotIn("do-not-log", " ".join(logs.output))
