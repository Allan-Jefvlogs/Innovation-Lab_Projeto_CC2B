"""Native XanoScript structure, independent date/count oracle, and client mocks.

No XanoScript runtime is executed; the oracle is not evidence of Xano execution.
"""

from __future__ import annotations

import json
import re
import unittest
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from Meu_projeto.services.xano_client import XanoAuthClient


XS = (Path(__file__).resolve().parents[1] / "xano/api/inventory_stock/movements_dashboard_get.xs").read_text(encoding="utf-8")
SP = ZoneInfo("America/Sao_Paulo")


def at(day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=SP)


def reference_series(start: datetime, end: datetime, records: list[dict]) -> list[dict]:
    """Independent oracle using calendar dates and Counter, not the XS map loop."""
    local = start.astimezone(SP)
    boundary = datetime.combine(local.date(), time.min, SP)
    end_boundary = datetime.combine(local.date() + timedelta(days=7), time.min, SP)
    if start.timestamp() != boundary.timestamp() or end.timestamp() != end_boundary.timestamp():
        raise ValueError("Expected seven complete Sao Paulo civil days")
    counts = Counter(
        (row["at"].astimezone(SP).date(), row["tipo"])
        for row in records
        if start.timestamp() <= row["at"].timestamp() < end.timestamp()
    )
    return [
        {
            "dia": (local.date() + timedelta(days=offset)).isoformat(),
            "entradas": counts[(local.date() + timedelta(days=offset), "entrada")],
            "saidas": counts[(local.date() + timedelta(days=offset), "saida")],
        }
        for offset in range(7)
    ]


class NativeDashboardMovementStructureTests(unittest.TestCase):
    def test_native_projection_is_complete_and_half_open_with_two_data_queries(self):
        self.assertNotIn("db.direct_query", XS)
        self.assertEqual(XS.count("db.query inventory_movement"), 2)
        period = XS.split("db.query inventory_movement {", 1)[1].split("} as $period_movements", 1)[0]
        self.assertIn("$db.inventory_movement.data_hora >= $input.date_from", period)
        self.assertIn("$db.inventory_movement.data_hora < $input.date_to", period)
        self.assertIn('output = ["tipo", "data_hora"]', period)
        self.assertIn('return = {type: "stream"}', period)
        self.assertNotIn("paging", period)
        self.assertNotIn("join", period)
        aggregation = XS.split("foreach ($period_movements)", 1)[1].split("db.query inventory_movement", 1)[0]
        self.assertNotIn("db.query", aggregation)
        self.assertNotIn("$movement.quantidade", aggregation)
        self.assertIn('$day_counts|set:"entradas":($day_counts.entradas + 1)', aggregation)
        self.assertIn('$day_counts|set:"saidas":($day_counts.saidas + 1)', aggregation)
        self.assertNotIn("api.request", XS)

    def test_seven_local_days_are_seeded_and_validated_before_data_query(self):
        indexes = re.search(r"var \$day_indexes \{ value = (\[[^\]]+\]) \}", XS)
        self.assertIsNotNone(indexes)
        self.assertEqual(json.loads(indexes.group(1)), list(range(7)))
        self.assertIn('value = ($start_day ~ " 00:00:00")|parse_timestamp:"Y-m-d H:i:s":"America/Sao_Paulo"', XS)
        self.assertIn('$daily_counts|set:$day_key:{dia: $day_key, entradas: 0, saidas: 0}', XS)
        self.assertIn('transform_timestamp:"tomorrow":"America/Sao_Paulo"', XS)
        self.assertIn('$movement.data_hora|format_timestamp:"Y-m-d":"America/Sao_Paulo"', XS)
        self.assertNotIn("604800", XS)
        self.assertLess(XS.index("precondition ($input.date_from == $start_boundary)"), XS.index("db.query inventory_movement"))
        self.assertLess(XS.index("precondition ($input.date_to == $day_cursor)"), XS.index("db.query inventory_movement"))
        self.assertIn("foreach ($day_keys)", XS)

    def test_recent_contract_and_permission_are_preserved(self):
        self.assertIn('auth = "user"', XS)
        self.assertIn('permission_code: "movement.read", alternate_permission_code: "report.read"', XS)
        self.assertIn('sort = {data_hora: "desc", id: "desc"}', XS)
        self.assertIn('paging: {page: 1, per_page: 5, totals: false}', XS)
        recent = XS.split("} as $period_movements", 1)[1].split("db.query inventory_movement {", 1)[1]
        self.assertNotIn("where =", recent.split("} as $recent_page", 1)[0].split("eval =", 1)[1])
        for key in ("id", "tipo", "product_name", "quantidade", "data_hora", "user_name"):
            self.assertIn(f"{key}: $recent_movement.{key}", recent)
        self.assertIn("serie: $daily_rows", recent)

    def test_recent_objects_are_built_in_stack_not_inline_response_map(self):
        self.assertIn("foreach ($recent_page.items)", XS)
        self.assertIn("array.push $recent_items", XS)
        self.assertNotIn("$recent_page.items|map:", XS)
        response = XS.split("response =", 1)[1]
        self.assertIn("items: $recent_items", response)
        self.assertNotIn("|map:", response)


class NativeDashboardMovementOracleTests(unittest.TestCase):
    def test_empty_period_has_seven_ordered_zero_days(self):
        rows = reference_series(at(5), at(12), [])
        self.assertEqual([row["dia"] for row in rows], [f"2026-11-{day:02d}" for day in range(5, 12)])
        self.assertTrue(all(row["entradas"] == row["saidas"] == 0 for row in rows))

    def test_start_is_inclusive_end_is_exclusive_and_midnight_uses_sao_paulo(self):
        records = [
            {"at": at(5) - timedelta(milliseconds=1), "tipo": "entrada"},
            {"at": at(5), "tipo": "entrada"},
            {"at": datetime(2026, 11, 6, 2, 59, 59, tzinfo=timezone.utc), "tipo": "saida"},
            {"at": datetime(2026, 11, 6, 3, 0, 0, tzinfo=timezone.utc), "tipo": "entrada"},
            {"at": at(12) - timedelta(milliseconds=1), "tipo": "saida"},
            {"at": at(12), "tipo": "entrada"},
        ]
        rows = reference_series(at(5), at(12), records)
        self.assertEqual(rows[0], {"dia": "2026-11-05", "entradas": 1, "saidas": 1})
        self.assertEqual(rows[1]["entradas"], 1)
        self.assertEqual(rows[-1]["saidas"], 1)
        self.assertEqual(sum(row["entradas"] + row["saidas"] for row in rows), 4)

    def test_count_is_per_operation_not_quantity_and_exceeds_a_single_page(self):
        records = [
            {"at": at(7, 12), "tipo": "entrada", "quantidade": 0.25, "unidade": "KG"}
            for _ in range(125)
        ] + [{"at": at(7, 13), "tipo": "entrada", "quantidade": 9000, "unidade": "UN"},
             {"at": at(7, 14), "tipo": "saida", "quantidade": 400, "unidade": "L"}]
        rows = reference_series(at(5), at(12), records)
        self.assertEqual(rows[2], {"dia": "2026-11-07", "entradas": 126, "saidas": 1})

    def test_rejects_non_midnight_or_incomplete_or_oversized_period(self):
        for start, end in ((at(5, 1), at(12, 1)), (at(5), at(11)), (at(5), at(13)),
                           (at(5), at(12) + timedelta(milliseconds=1)), (at(12), at(5))):
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    reference_series(start, end, [])

    def test_seven_civil_days_do_not_assume_fixed_utc_duration(self):
        start = datetime(2018, 11, 1, tzinfo=SP)
        end = datetime(2018, 11, 8, tzinfo=SP)
        self.assertEqual(end.timestamp() - start.timestamp(), 167 * 3600)
        self.assertEqual(len(reference_series(start, end, [])), 7)


class NativeDashboardMovementClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_response_shape_and_five_recent_rows_fit_unchanged_client(self):
        series = reference_series(at(5), at(12), [{"at": at(7, 12), "tipo": "entrada"}])
        recent = [
            {"id": index, "tipo": "entrada", "product_name": "Teste local",
             "quantidade": 1, "data_hora": int(at(11, index).timestamp() * 1000), "user_name": "Teste"}
            for index in range(5, 0, -1)
        ]
        payload = {"serie": series, "recentes": {"items": recent, "curPage": 1, "perPage": 5}}
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)) as get:
            result = await client.get_dashboard_movements("local-test-token", date_from=at(5).isoformat(), date_to=at(12).isoformat())
        self.assertEqual(result["serie"], series)
        self.assertEqual(result["recentes"]["items"], recent)
        get.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
