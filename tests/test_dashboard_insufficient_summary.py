"""Local contract checks for the opt-in Dashboard insufficient-stock summary."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from Meu_projeto.pages import dashboard as dashboard_module
from Meu_projeto.pages.dashboard import DashboardState, _project_insufficient_stock
from Meu_projeto.services.session_read_cache import CACHE_MISS, session_read_cache
from Meu_projeto.services.xano_client import XanoServerError, auth_client
from Meu_projeto.services.xano_client import XanoRequestError


def _item(
    product_id: int,
    quantity: str,
    minimum: str,
    situation: str,
) -> dict[str, object]:
    return {
        "product_id": product_id,
        "codigo": f"SKU-{product_id}",
        "nome": f"Produto {product_id}",
        "quantidade_disponivel": quantity,
        "estoque_minimo": minimum,
        "unidade_medida": "UN",
        "situacao_estoque": situation,
    }


def _dashboard_state(token: str, grants: dict[str, bool]) -> DashboardState:
    state = object.__new__(DashboardState)
    object.__setattr__(state, "dirty_vars", set())
    for name, value in {
        "is_loading": False,
        "has_loaded": False,
        "error_message": "",
        "retry_sources": [],
        "retry_after_epoch": 0.0,
        "session_fingerprint": "",
        "products_accessible": False,
        "products_count": None,
        "products_error": "",
        "products_stale": False,
        "stock_accessible": False,
        "below_minimum_count": None,
        "stock_alerts": [],
        "stock_error": "",
        "stock_stale": False,
        "movements_accessible": False,
        "recent_movements": [],
        "movements_error": "",
        "movements_stale": False,
        "replenishment_accessible": False,
    }.items():
        setattr(state, name, value)
    object.__setattr__(state, "_session", AsyncMock(return_value=(token, grants)))
    return state


async def _drain(event) -> None:
    async for _ in event:
        pass


class DashboardInsufficientSummaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        session_read_cache.clear()

    def tearDown(self) -> None:
        session_read_cache.clear()

    def test_projector_accepts_zero_and_positive_shortage_and_global_total(self):
        result = _project_insufficient_stock(
            {
                "items": [
                    _item(1, "0", "3", "sem_estoque"),
                    _item(2, "0", "0", "sem_estoque"),
                    _item(3, "2.5", "4", "abaixo_minimo"),
                ],
                "itemsTotal": 8,
                "curPage": 1,
                "perPage": 3,
            }
        )

        self.assertEqual(result["count"], 8)
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(result["items"][0]["situacao_estoque"], "sem_estoque")
        self.assertEqual(result["items"][1]["minimo"], "0")
        self.assertEqual(result["items"][2]["atual"], "2,5")
        self.assertEqual(result["items"][2]["unidade_medida"], "UN")

    def test_projector_accepts_legitimate_empty_total(self):
        self.assertEqual(_project_insufficient_stock({"items": [], "itemsTotal": 0}), {"count": 0, "items": []})

    def test_projector_rejects_sufficient_or_duplicate_products(self):
        with self.assertRaises(XanoServerError):
            _project_insufficient_stock({"items": [_item(1, "5", "5", "abaixo_minimo")], "itemsTotal": 1})
        with self.assertRaises(XanoServerError):
            _project_insufficient_stock(
                {"items": [_item(1, "0", "1", "sem_estoque"), _item(1, "0", "1", "sem_estoque")], "itemsTotal": 2}
            )

    def test_projector_rejects_missing_stock_values_and_invalid_totals(self):
        malformed = _item(1, "0", "1", "sem_estoque")
        malformed.pop("estoque_minimo")
        with self.assertRaises(XanoServerError):
            _project_insufficient_stock({"items": [malformed], "itemsTotal": 1})
        with self.assertRaises(XanoServerError):
            _project_insufficient_stock({"items": [_item(1, "0", "1", "sem_estoque")], "itemsTotal": None})

    def test_local_endpoint_has_stock_only_auth_and_exact_global_count(self):
        from pathlib import Path

        source = Path("xano/api/inventory_stock/stock_insufficient_summary_get.xs").read_text(encoding="utf-8")
        shared_filter = '$db.product.status == "ativo" && ($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo))'
        self.assertIn('permission_code: "stock.read"', source)
        self.assertNotIn("purchase_request", source)
        self.assertIn("return = {type: \"count\"}", source)
        self.assertIn("itemsTotal: $insufficient_total", source)
        self.assertIn("$db.product.status == \"ativo\"", source)
        self.assertIn("$db.product.status == \"ativo\" && $db.inventory_stock.id == null", source)
        self.assertEqual(source.count(shared_filter), 2)
        self.assertIn('error = "STOCK_BALANCE_NOT_FOUND"', source)
        self.assertIn('"items.unidade_medida"', source)
        self.assertIn('"items.product_id"', source)
        self.assertIn(
            'return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}',
            source,
        )
        self.assertNotIn("metadata: false", source)
        self.assertEqual(source.count('return = {type: "count"}'), 1)
        self.assertEqual(source.count("db.query inventory_stock"), 2)

    def test_local_endpoint_projects_fields_consumed_by_the_scoped_loop_alias(self):
        from pathlib import Path
        import re

        source = Path("xano/api/inventory_stock/stock_insufficient_summary_get.xs").read_text(encoding="utf-8")
        loop_start = source.index("    foreach ($insufficient_page.items) {")
        loop_end = source.index("\n    }\n  }\n\n  response", loop_start) + len("\n    }")
        loop_body = source[loop_start:loop_end]
        alias_match = re.search(r"each as \$(\w+)\s*\{", loop_body)
        self.assertIsNotNone(alias_match)
        alias = alias_match.group(1)

        # Every item property read, including the conditional quantity, must
        # use the alias declared by this foreach, and each read must be projected.
        scoped_body = loop_body[alias_match.end():]
        item_references = set(re.findall(r"\$(\w+)\.(\w+)", scoped_body))
        self.assertTrue(item_references)
        self.assertEqual({name for name, _field in item_references}, {alias})
        projected_fields = set(re.findall(r'"items\.(\w+)"', source))
        self.assertTrue({field for _name, field in item_references}.issubset(projected_fields))
        self.assertIn(f"if (${alias}.quantidade_disponivel == 0)", loop_body)
        self.assertIn(f"quantidade_disponivel: ${alias}.quantidade_disponivel", loop_body)

    async def test_client_uses_stock_group_and_rejects_null_global_count(self):
        good_response = {
            "items": [_item(1, "0", "1", "sem_estoque")],
            "itemsTotal": 6,
            "curPage": 1,
            "perPage": 5,
        }
        with patch.object(auth_client, "_inventory_request", new_callable=AsyncMock, return_value=good_response) as request:
            result = await auth_client.get_stock_insufficient_summary("private-token", page=1, per_page=5)
        self.assertEqual(result["itemsTotal"], 6)
        request.assert_awaited_once_with(
            "GET",
            "/stock/insufficient_summary",
            "private-token",
            params={"page": 1, "per_page": 5},
            group_url=auth_client.stock_group_url,
        )

        with patch.object(auth_client, "_inventory_request", new_callable=AsyncMock, return_value={**good_response, "itemsTotal": None}):
            with self.assertRaises(XanoServerError):
                await auth_client.get_stock_insufficient_summary("private-token")

    async def test_dashboard_reads_summary_with_stock_read_only_and_caps_cold_gets_at_three(self):
        grant_map = {"products": True, "stock": True, "movements": True, "replenishment": False}
        state = _dashboard_state("session-one", grant_map)
        product_response = {"items": [], "itemsTotal": 6}
        stock_response = {
            "items": [
                _item(1, "0", "1", "sem_estoque"),
                _item(2, "0", "0", "sem_estoque"),
                _item(3, "0", "4", "sem_estoque"),
                _item(4, "0", "2", "sem_estoque"),
                _item(5, "2.5", "4", "abaixo_minimo"),
            ],
            "itemsTotal": 6,
            "curPage": 1,
            "perPage": 5,
        }
        movement_response = {"items": []}
        with (
            patch.object(dashboard_module, "DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", True),
            patch.object(auth_client, "list_products", new_callable=AsyncMock, return_value=product_response) as products,
            patch.object(auth_client, "get_stock_insufficient_summary", new_callable=AsyncMock, return_value=stock_response) as stock,
            patch.object(auth_client, "list_movements", new_callable=AsyncMock, return_value=movement_response) as movements,
            patch.object(auth_client, "list_stock", new_callable=AsyncMock) as legacy_stock,
        ):
            await _drain(state.load_dashboard())

        self.assertEqual(state.below_minimum_count, 6)
        self.assertEqual(state.stock_value, "6")
        self.assertEqual(len(state.stock_alerts), 5)
        self.assertEqual(
            [item["situacao_estoque"] for item in state.stock_alerts].count("sem_estoque"),
            4,
        )
        self.assertEqual(state.stock_alerts[-1]["situacao_estoque"], "abaixo_minimo")
        stock.assert_awaited_once_with("session-one", page=1, per_page=5)
        legacy_stock.assert_not_awaited()
        self.assertEqual(products.await_count + stock.await_count + movements.await_count, 3)
        self.assertFalse(state.replenishment_accessible)

    async def test_new_summary_is_not_used_while_feature_flag_is_off(self):
        state = _dashboard_state(
            "session-one",
            {"products": False, "stock": True, "movements": False, "replenishment": False},
        )
        with (
            patch.object(dashboard_module, "DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", False),
            patch.object(
                auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": [], "itemsTotal": 0},
            ) as old_stock,
            patch.object(auth_client, "get_stock_insufficient_summary", new_callable=AsyncMock) as new_stock,
        ):
            await _drain(state.load_dashboard())

        old_stock.assert_awaited_once()
        new_stock.assert_not_awaited()
        self.assertEqual(dashboard_module._dashboard_endpoint("stock"), "GET /dashboard/stock")

    async def test_dashboard_stock_cache_is_session_scoped_and_invalidated_by_write(self):
        state = _dashboard_state(
            "session-one",
            {"products": False, "stock": True, "movements": False, "replenishment": False},
        )
        response = {"items": [_item(1, "0", "2", "sem_estoque")], "itemsTotal": 1, "curPage": 1, "perPage": 5}
        with (
            patch.object(dashboard_module, "DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", True),
            patch.object(auth_client, "get_stock_insufficient_summary", new_callable=AsyncMock, return_value=response) as summary,
        ):
            await _drain(state.load_dashboard())
            same_session = _dashboard_state(
                "session-one",
                {"products": False, "stock": True, "movements": False, "replenishment": False},
            )
            await _drain(same_session.load_dashboard())
            other_session = _dashboard_state(
                "session-two",
                {"products": False, "stock": True, "movements": False, "replenishment": False},
            )
            await _drain(other_session.load_dashboard())
        self.assertEqual(summary.await_count, 2)

        key = session_read_cache.key(
            "dashboard:stock.read",
            "GET /stock/insufficient_summary",
            "session-one",
            {"page": 1, "per_page": 5},
        )
        session_read_cache.set(key, {"count": 3, "items": []}, 15)
        with patch.object(
            auth_client,
            "_send_request",
            new_callable=AsyncMock,
            return_value=httpx.Response(200, json={"ok": True}),
        ):
            await auth_client._inventory_request("PATCH", "/products/by_id/9", "session-one")
        cached, _fresh = session_read_cache.get(key, 15)
        self.assertIs(cached, CACHE_MISS)

    async def test_429_keeps_previous_summary_and_manual_retry_obeys_cooldown(self):
        state = _dashboard_state(
            "session-one",
            {"products": False, "stock": True, "movements": False, "replenishment": False},
        )
        response = {"items": [_item(1, "0", "1", "sem_estoque")], "itemsTotal": 4, "curPage": 1, "perPage": 5}
        key = session_read_cache.key(
            "dashboard:stock.read",
            "GET /stock/insufficient_summary",
            "session-one",
            {"page": 1, "per_page": 5},
        )
        session_read_cache.set(key, _project_insufficient_stock(response), 15)
        created, ttl, cached_value = session_read_cache._entries[key]
        session_read_cache._entries[key] = (created - ttl - 1, ttl, cached_value)
        now = {"value": 100.0}
        with (
            patch.object(dashboard_module, "DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED", True),
            patch.object(dashboard_module.time, "time", side_effect=lambda: now["value"]),
            patch.object(dashboard_module, "_retry_delay_seconds", return_value=5),
            patch.object(
                auth_client,
                "get_stock_insufficient_summary",
                new_callable=AsyncMock,
                side_effect=[XanoRequestError("limited", "TOO_MANY_REQUESTS", 429, {}), response],
            ) as summary,
        ):
            await _drain(state.load_dashboard())
            self.assertEqual(state.below_minimum_count, 4)
            self.assertTrue(state.stock_stale)
            self.assertEqual(summary.await_count, 1)
            await _drain(state.load_dashboard(retry_failed_only=True))
            self.assertEqual(summary.await_count, 1)
            now["value"] = 105.0
            await _drain(state.load_dashboard(retry_failed_only=True))

        self.assertEqual(summary.await_count, 2)
        self.assertFalse(state.stock_stale)
        self.assertEqual(state.below_minimum_count, 4)


if __name__ == "__main__":
    unittest.main()
