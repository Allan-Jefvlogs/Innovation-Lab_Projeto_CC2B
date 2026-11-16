"""Dashboard integration tests use mocks only; no request reaches the real Xano."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
import inspect
from unittest.mock import AsyncMock, patch

import httpx

from Meu_projeto.pages import dashboard as dashboard_module
from Meu_projeto.components import layout
from Meu_projeto.pages import login as login_module
from Meu_projeto.pages.dashboard import DashboardState, _cache_key
from Meu_projeto.services.session_read_cache import CACHE_MISS, session_read_cache
from Meu_projeto.services.xano_client import (
    XanoAuthError,
    XanoConnectionError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestError,
    XanoServerError,
    auth_client,
    _DASHBOARD_CACHE_ENDPOINTS,
)
from Meu_projeto.state.auth import AuthState


ALL_GRANTS = {"products": True, "stock": True, "movements": True, "purchase_requests": False}


def _state(token: str = "dashboard-session", grants=None) -> DashboardState:
    state = object.__new__(DashboardState)
    DashboardState._init_bookkeeping(state)
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
        "chart_data": [],
        "chart_error": "",
        "chart_enabled": dashboard_module.REAL_DASHBOARD_MOVEMENTS_ENABLED,
        "_auth_user_name": "Usuário de teste",
        "purchase_requests_accessible": False,
        "purchase_requests_count": None,
        "purchase_requests_error": "",
        "purchase_requests_stale": False,
    }.items():
        setattr(state, name, value)
    object.__setattr__(state, "_session", AsyncMock(return_value=(token, grants if grants is not None else dict(ALL_GRANTS))))
    return state


async def _drain(event) -> None:
    async for _ in event:
        pass


class DashboardIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()

    def tearDown(self):
        session_read_cache.clear()

    def _mock_endpoints(self, *, products=None, categories=None, suppliers=None, stock=None, movements=None):
        return (
            patch.object(
                dashboard_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value=products or {"items": [{"id": 1}], "itemsTotal": 12},
            ),
            patch.object(
                dashboard_module.auth_client,
                "list_categories",
                new_callable=AsyncMock,
                return_value=categories or {"items": [{"id": 1}], "itemsTotal": 4},
            ),
            patch.object(
                dashboard_module.auth_client,
                "list_suppliers",
                new_callable=AsyncMock,
                return_value=suppliers or {"items": [{"id": 1}], "itemsTotal": 3},
            ),
            patch.object(
                dashboard_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value=stock or {
                    "itemsTotal": 2,
                    "items": [{"codigo": "P-1", "nome": "Peça", "quantidade_disponivel": "2.5", "estoque_minimo": "5"}],
                },
            ),
            patch.object(
                dashboard_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=movements or {
                    "items": [{
                        "tipo": "entrada", "product_name": "Peça", "product_code": "P-1",
                        "quantidade": "3.5", "data_hora": 1_760_000_000_000, "user_name": "Operador",
                    }],
                },
            ),
        )

    async def test_dashboard_uses_only_products_stock_and_movement_gets(self):
        state = _state()
        product_call, category_call, supplier_call, stock_call, movement_call = self._mock_endpoints()
        with product_call as products, category_call as categories, supplier_call as suppliers, stock_call as stock, movement_call as movements:
            await _drain(state.load_dashboard())

        self.assertEqual(state.products_count, 12)
        self.assertEqual(state.below_minimum_count, 2)
        self.assertEqual(state.stock_alerts[0], {"codigo": "P-1", "nome": "Peça", "atual": "2,5", "minimo": "5"})
        self.assertEqual(state.recent_movements[0]["tipo"], "Entrada")
        self.assertEqual(state.recent_movements[0]["usuario"], "Operador")
        self.assertTrue(state.has_loaded)
        self.assertEqual(sum(call.await_count for call in (products, stock, movements)), 3)
        products.assert_awaited_once_with("dashboard-session", page=1, per_page=1, status="ativo")
        stock.assert_awaited_once_with("dashboard-session", page=1, per_page=5, situacao="abaixo_minimo")
        movements.assert_awaited_once_with("dashboard-session", page=1, per_page=5)
        categories.assert_not_awaited()
        suppliers.assert_not_awaited()

    async def test_no_grant_skips_endpoint_and_does_not_show_fake_zero(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        product_call, category_call, supplier_call, stock_call, movement_call = self._mock_endpoints()
        with product_call as products, category_call as categories, supplier_call as suppliers, stock_call as stock, movement_call as movements:
            await _drain(state.load_dashboard())

        products.assert_awaited_once()
        categories.assert_not_awaited()
        suppliers.assert_not_awaited()
        stock.assert_not_awaited()
        movements.assert_not_awaited()
        self.assertEqual(state.products_count, 12)

    async def test_successful_empty_responses_are_distinct_from_unavailable_data(self):
        state = _state()
        product_call, category_call, supplier_call, stock_call, movement_call = self._mock_endpoints(
            products={"items": [], "itemsTotal": 0},
            categories={"items": [], "itemsTotal": 0},
            suppliers={"items": [], "itemsTotal": 0},
            stock={"items": [], "itemsTotal": 0},
            movements={"items": []},
        )
        with product_call, category_call, supplier_call, stock_call, movement_call:
            await _drain(state.load_dashboard())

        self.assertEqual(state.products_value, "0")
        self.assertEqual(state.stock_value, "0")
        self.assertEqual(state.stock_message, "Nenhum produto abaixo do estoque mínimo.")
        self.assertEqual(state.movements_message, "Nenhuma movimentação registrada.")

    async def test_page_loader_runs_auth_guard_before_fetching_dashboard(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        auth_state = SimpleNamespace(
            require_auth=AsyncMock(return_value=None),
            session_is_valid=True,
            user_name="Usuário de teste",
        )
        with (
            patch.object(DashboardState, "get_state", new_callable=AsyncMock, return_value=auth_state),
            patch.object(DashboardState, "_session", new_callable=AsyncMock, return_value=("dashboard-session", {"products": True, "stock": False, "movements": False})),
            patch.object(
                dashboard_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [], "itemsTotal": 2},
            ) as products,
        ):
            await _drain(state.load_page())

        auth_state.require_auth.assert_awaited_once()
        products.assert_awaited_once()

    async def test_dashboard_cache_hits_and_isolated_sessions(self):
        product_call, category_call, supplier_call, stock_call, movement_call = self._mock_endpoints()
        with product_call as products, category_call as categories, supplier_call as suppliers, stock_call as stock, movement_call as movements:
            first = _state("session-a")
            second = _state("session-a")
            other_session = _state("session-b")
            await _drain(first.load_dashboard())
            # Returning to Dashboard in the same session reuses fresh reads.
            await _drain(first.load_dashboard())
            await _drain(second.load_dashboard())
            await _drain(other_session.load_dashboard())

        for call in (products, stock, movements):
            self.assertEqual(call.await_count, 2)
        categories.assert_not_awaited()
        suppliers.assert_not_awaited()

    async def test_expired_dashboard_cache_is_revalidated(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        with patch.object(
            dashboard_module.auth_client,
            "list_products",
            new_callable=AsyncMock,
            side_effect=[{"items": [], "itemsTotal": 7}, {"items": [], "itemsTotal": 8}],
        ) as products:
            await _drain(state.load_dashboard())
            key = _cache_key("products", "dashboard-session", {"status": "ativo", "page": 1, "per_page": 1})
            created_at, ttl, value = session_read_cache._entries[key]
            session_read_cache._entries[key] = (created_at - dashboard_module.DASHBOARD_PRODUCT_TTL - 1, ttl, value)
            await _drain(state.load_dashboard())

        self.assertEqual(products.await_count, 2)
        self.assertEqual(state.products_count, 8)

    async def test_timeout_preserves_previous_indicator_and_marks_it_stale(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        state.products_count = 6
        with patch.object(
            dashboard_module.auth_client,
            "list_products",
            new_callable=AsyncMock,
            side_effect=XanoConnectionError("timeout"),
        ):
            await _drain(state.load_dashboard())

        self.assertEqual(state.products_count, 6)
        self.assertTrue(state.products_stale)
        self.assertIn("desatualizado", state.products_detail)

    async def test_successful_write_invalidates_dashboard_cache_but_failed_write_does_not(self):
        token = "write-cache-session"
        key = _cache_key("products", token, {"status": "ativo", "page": 1, "per_page": 1})
        purchase_summary_key = _cache_key("purchase_requests", token, {})
        session_read_cache.set(key, {"count": 7}, 30)
        session_read_cache.set(
            purchase_summary_key,
            {"count": 3},
            dashboard_module.DASHBOARD_OPERATIONAL_TTL,
        )
        with patch.object(
            dashboard_module.auth_client,
            "_send_request",
            new_callable=AsyncMock,
            return_value=httpx.Response(200, json={"id": 1}),
        ):
            await dashboard_module.auth_client._inventory_request("PATCH", "/products/by_id/1", token)
        cached, _fresh = session_read_cache.get(key, 30)
        self.assertIs(cached, CACHE_MISS)
        cached, _fresh = session_read_cache.get(
            purchase_summary_key, dashboard_module.DASHBOARD_OPERATIONAL_TTL
        )
        self.assertIs(cached, CACHE_MISS)

        session_read_cache.set(key, {"count": 8}, 30)
        session_read_cache.set(
            purchase_summary_key,
            {"count": 4},
            dashboard_module.DASHBOARD_OPERATIONAL_TTL,
        )
        with patch.object(
            dashboard_module.auth_client,
            "_send_request",
            new_callable=AsyncMock,
            return_value=httpx.Response(500, json={"code": "ERROR_FATAL"}),
        ):
            with self.assertRaises(XanoRequestError):
                await dashboard_module.auth_client._inventory_request("PATCH", "/products/by_id/1", token)
        cached, fresh = session_read_cache.get(key, 30)
        self.assertTrue(fresh)
        self.assertEqual(cached, {"count": 8})
        cached, fresh = session_read_cache.get(
            purchase_summary_key, dashboard_module.DASHBOARD_OPERATIONAL_TTL
        )
        self.assertTrue(fresh)
        self.assertEqual(cached, {"count": 4})

    async def test_429_preserves_cached_dashboard_data_as_stale_and_manual_retry_recovers(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        cached_key = _cache_key("products", "dashboard-session", {"status": "ativo", "page": 1, "per_page": 1})
        session_read_cache.set(cached_key, {"count": 9}, dashboard_module.DASHBOARD_PRODUCT_TTL)
        created_at, ttl, value = session_read_cache._entries[cached_key]
        session_read_cache._entries[cached_key] = (created_at - ttl - 1, ttl, value)
        with (
            patch.object(dashboard_module.auth_client, "list_products", new_callable=AsyncMock, side_effect=[XanoRequestError("limited", "TOO_MANY_REQUESTS", 429, {}), {"items": [], "itemsTotal": 5}]) as products,
            patch.object(dashboard_module, "_retry_delay_seconds", return_value=0),
        ):
            await _drain(state.load_dashboard())
            self.assertEqual(state.products_count, 9)
            self.assertTrue(state.products_stale)
            await _drain(state.load_dashboard(retry_failed_only=True))

        self.assertEqual(products.await_count, 2)
        self.assertEqual(state.products_count, 5)
        self.assertFalse(state.products_stale)
        self.assertFalse(state.has_errors)

    async def test_dashboard_does_not_repeat_failed_reads_on_reopened_route(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        with patch.object(
            dashboard_module.auth_client,
            "list_products",
            new_callable=AsyncMock,
            side_effect=XanoRateLimitError(5),
        ) as products:
            await _drain(state.load_dashboard())
            await _drain(state.load_dashboard())

        products.assert_awaited_once()
        self.assertIn("products", state.retry_sources)
        self.assertIsNone(state.products_count)
        self.assertEqual(dashboard_module._error_origin(XanoRateLimitError(1)), "local_coordinator")
        self.assertEqual(
            dashboard_module._error_origin(XanoRequestError("limited", "TOO_MANY_REQUESTS", 429, {})),
            "remote_xano",
        )

    async def test_manual_retry_respects_cooldown_then_retries_only_failed_source(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        clock = {"now": 100.0}
        with (
            patch.object(
                dashboard_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                side_effect=[XanoRateLimitError(5), {"items": [], "itemsTotal": 4}],
            ) as products,
            patch.object(dashboard_module.time, "time", side_effect=lambda: clock["now"]),
        ):
            await _drain(state.load_dashboard())
            clock["now"] = 104.0
            await _drain(state.load_dashboard(retry_failed_only=True))
            products.assert_awaited_once()
            clock["now"] = 105.0
            await _drain(state.load_dashboard(retry_failed_only=True))

        self.assertEqual(products.await_count, 2)
        self.assertEqual(state.products_count, 4)
        self.assertFalse(state.retry_sources)

    async def test_api_failure_without_cache_is_not_reported_as_zero(self):
        state = _state(grants={"products": True, "stock": False, "movements": False})
        with patch.object(
            dashboard_module.auth_client,
            "list_products",
            new_callable=AsyncMock,
            side_effect=XanoRequestError("limited", "TOO_MANY_REQUESTS", 429, {}),
        ):
            await _drain(state.load_dashboard())

        self.assertIsNone(state.products_count)
        self.assertEqual(state.products_value, "Indisponível")
        self.assertTrue(state.retry_sources)
        self.assertIn("Produtos", state.error_message)

    async def test_dashboard_keeps_current_cards_and_uses_purchase_request_metric_card(self):
        rendered = repr(dashboard_module.dashboard())
        dashboard_source = inspect.getsource(dashboard_module.dashboard)
        purchase_card_source = inspect.getsource(dashboard_module._purchase_requests_card)
        for fake in ("Arroz 5kg", "Café 500g", "Ana", "128", "22/09/2026"):
            self.assertNotIn(fake, rendered)
        self.assertIn('"Produtos ativos"', dashboard_source)
        self.assertIn('"Abaixo do m', dashboard_source)
        self.assertNotIn('"Categorias"', dashboard_source)
        self.assertNotIn('"Fornecedores"', dashboard_source)
        self.assertIn("Solicitações de Compras", purchase_card_source)
        self.assertIn("purchase_requests_value", purchase_card_source)
        self.assertIn("purchase_requests_detail", purchase_card_source)
        self.assertNotIn("Aguardando integração", dashboard_source)
        self.assertIn("recent_movements_rx_state_", rendered)
        self.assertIn("stock_alerts_rx_state_", rendered)
        self.assertIn("products_value_rx_state_", rendered)

    def test_login_and_sidebar_reuse_shared_brand_components(self):
        self.assertIn("brand_mark", inspect.getsource(login_module))
        self.assertIn("brand_wordmark", inspect.getsource(login_module))
        self.assertIn("brand_mark", inspect.getsource(layout))
        self.assertIn("brand_wordmark", inspect.getsource(layout))

    def test_recent_movement_quantity_and_date_have_separate_spacing(self):
        values = {"tipo": "Entrada", "produto": "Produto exemplo", "quantidade": "8,75", "data": "12/10/2026 19:33", "usuario": "Operador"}
        header = dashboard_module._movement_header()
        row = dashboard_module._movement_row(values)
        table_source = inspect.getsource(dashboard_module._recent_movements_panel)

        self.assertEqual(header.display, "grid")
        self.assertEqual(row.display, "grid")
        self.assertEqual(header.grid_template_columns, row.grid_template_columns)
        self.assertEqual(
            dict(header.grid_template_columns),
            {
                "initial": "minmax(0, 1fr) minmax(0, 1fr)",
                "md": "17fr 22fr 17fr 22fr 22fr",
            },
        )
        self.assertEqual(dict(header.column_gap), {"initial": "12px", "md": "16px"})
        self.assertEqual(dict(row.column_gap), {"initial": "12px", "md": "16px"})
        self.assertEqual(dict(header.row_gap), {"initial": "10px", "md": "12px"})
        self.assertEqual(dict(row.row_gap), {"initial": "10px", "md": "12px"})
        self.assertEqual(header.min_width, "0")
        self.assertEqual(row.min_width, "0")
        generated_css = header.render()["props"][0]
        self.assertIn("@media screen and (min-width: 0px)", generated_css)
        self.assertIn("@media screen and (min-width: 62em)", generated_css)
        self.assertIn("Qtde.", str(header.children[2]))
        self.assertEqual(len(header.children), 5)
        self.assertEqual(len(row.children), 5)
        self.assertEqual([cell.text_align for cell in header.children], ["left"] * 5)
        self.assertEqual([cell.text_align for cell in row.children], ["left"] * 5)
        self.assertIn('role="table"', table_source)
        self.assertNotIn("overflow_x", table_source)
        self.assertNotIn("_MOVEMENT_GRID_MIN_WIDTH", table_source)
        self.assertIn('aria_label="Movimentações recentes"', table_source)
        self.assertIn('font_variant_numeric="tabular-nums"', inspect.getsource(dashboard_module._movement_row))
        self.assertNotIn("text_overflow", inspect.getsource(dashboard_module._movement_row))
        self.assertNotIn("rx.grid(", inspect.getsource(dashboard_module._movement_grid_row))


    def test_dashboard_card_spacing_and_padding_are_consistent(self):
        dashboard_source = inspect.getsource(dashboard_module.dashboard)
        metric_card = dashboard_module._metric_card(
            "Produtos ativos",
            "package",
            dashboard_module.DashboardState.products_value,
            dashboard_module.DashboardState.products_detail,
        )
        purchase_card = dashboard_module._purchase_requests_card()

        self.assertEqual(metric_card.padding, "17px 18px")
        self.assertEqual(purchase_card.padding, "17px 18px")
        self.assertEqual(dashboard_module.DASHBOARD_GAP, "17px")
        self.assertEqual(dashboard_source.count('gap=DASHBOARD_GAP'), 2)
        self.assertIn('repeat(3, minmax(0, 1fr))', dashboard_source)
        self.assertIn('gap="18px"', dashboard_source)

    def test_chart_has_a_real_positive_height_in_generated_component(self):
        from Meu_projeto.components.stock_movement_chart import stock_movement_chart

        points = [
            {"dia": f"{day:02d}/11", "entradas": 0, "saidas": 0}
            for day in range(1, 8)
        ]
        component = stock_movement_chart(points)
        generated = str(component)
        self.assertIn('height:228', generated)
        self.assertIn('dataKey:"entradas"', generated)
        self.assertIn('dataKey:"saidas"', generated)
        self.assertNotIn("Dados ilustrativos", generated)

    def test_sidebar_responsive_dimensions_compile_to_media_queries(self):
        sidebar = layout.sidebar()
        generated_css = str(sidebar.render())
        self.assertIn("@media screen and (min-width: 1051px)", generated_css)
        self.assertIn("252px", generated_css)
        self.assertNotIn('"initial"', generated_css)
        self.assertNotIn('"lg"', generated_css)

    def test_stock_alert_ratio_handles_zero_minimum_and_fractional_balances(self):
        import json
        import subprocess

        cases = [
            ("0", "0", [False, 0]),
            ("0", "10", [True, 0]),
            ("2,5", "10", [True, 25]),
            ("—", "10", [False, 0]),
            ("12", "10", [True, 100]),
        ]
        expressions = []
        for current, minimum, _ in cases:
            visible, percentage = dashboard_module._stock_alert_progress(current, minimum)
            expressions.append([str(visible), str(percentage)])
        # The inputs to Reflex's pyAnd helper are booleans in these expressions.
        # Evaluate the generated arithmetic with that boolean helper, without DOM/network.
        result = subprocess.run(
            ["node", "-e", "const pyAnd=(a,b)=>a?b():a;let input='';process.stdin.on('data',c=>input+=c);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(input).map(pair=>pair.map(expression=>eval(expression))))));"],
            input=json.dumps(expressions),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), [expected for _, _, expected in cases])


class DashboardPurchaseRequestSummaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()

    def tearDown(self):
        session_read_cache.clear()

    async def test_client_validates_zero_positive_and_rejects_invalid_counts(self):
        for expected in (0, 7):
            with patch.object(
                auth_client,
                "_inventory_request",
                new_callable=AsyncMock,
                return_value={"solicitacoes_abertas": expected},
            ) as request:
                result = await auth_client.get_purchase_requests_summary("token")
            self.assertEqual(result, {"solicitacoes_abertas": expected})
            request.assert_awaited_once_with(
                "GET",
                "/purchase_requests/summary",
                "token",
                group_url=auth_client.stock_group_url,
            )

        invalid_responses = (
            {},
            {"solicitacoes_abertas": None},
            {"solicitacoes_abertas": "0"},
            {"solicitacoes_abertas": True},
            {"solicitacoes_abertas": 1.0},
            {"solicitacoes_abertas": -1},
            ["not-an-object"],
        )
        for response in invalid_responses:
            with self.subTest(response=response):
                with patch.object(
                    auth_client,
                    "_inventory_request",
                    new_callable=AsyncMock,
                    return_value=response,
                ):
                    with self.assertRaises(XanoServerError):
                        await auth_client.get_purchase_requests_summary("token")

        self.assertIn("GET /purchase_requests/summary", _DASHBOARD_CACHE_ENDPOINTS)

    async def test_dashboard_adds_one_authorized_get_without_changing_other_sources(self):
        state = _state(
            grants={**ALL_GRANTS, "purchase_requests": True},
        )
        product_call, _, _, stock_call, movement_call = DashboardIntegrationTests()._mock_endpoints()
        with (
            product_call as products,
            stock_call as stock,
            movement_call as movements,
            patch.object(
                auth_client,
                "get_purchase_requests_summary",
                new_callable=AsyncMock,
                return_value={"solicitacoes_abertas": 0},
            ) as purchase_requests,
        ):
            await _drain(state.load_dashboard())

        self.assertEqual(state.purchase_requests_count, 0)
        self.assertEqual(state.purchase_requests_value, "0")
        self.assertEqual(state.purchase_requests_detail, "Solicitações em andamento")
        self.assertEqual(sum(call.await_count for call in (products, stock, movements, purchase_requests)), 4)
        purchase_requests.assert_awaited_once_with("dashboard-session")
        self.assertEqual(state.products_count, 12)
        self.assertEqual(state.below_minimum_count, 2)
        self.assertEqual(state.recent_movements[0]["tipo"], "Entrada")

    async def test_missing_grant_skips_summary_and_keeps_other_dashboard_sources(self):
        grants = {**ALL_GRANTS, "purchase_requests": False}
        state = _state(grants=grants)
        cached_key = _cache_key("purchase_requests", "dashboard-session", {})
        session_read_cache.set(
            cached_key,
            {"count": 99},
            dashboard_module.DASHBOARD_OPERATIONAL_TTL,
        )
        product_call, _, _, stock_call, movement_call = DashboardIntegrationTests()._mock_endpoints()
        with (
            product_call as products,
            stock_call as stock,
            movement_call as movements,
            patch.object(auth_client, "get_purchase_requests_summary", new_callable=AsyncMock) as summary,
        ):
            await _drain(state.load_dashboard())

        summary.assert_not_awaited()
        self.assertIsNone(state.purchase_requests_count)
        self.assertEqual(state.purchase_requests_value, "Sem acesso")
        self.assertEqual(state.purchase_requests_detail, "Permissão de leitura não concedida")
        cached, _fresh = session_read_cache.get(
            cached_key, dashboard_module.DASHBOARD_OPERATIONAL_TTL
        )
        self.assertIs(cached, CACHE_MISS)
        self.assertEqual(sum(call.await_count for call in (products, stock, movements)), 3)
        self.assertEqual(state.products_count, 12)
        self.assertEqual(state.below_minimum_count, 2)
        self.assertEqual(state.recent_movements[0]["tipo"], "Entrada")

    async def test_expired_purchase_summary_cache_is_revalidated(self):
        grants = {"products": False, "stock": False, "movements": False, "purchase_requests": True}
        with patch.object(
            auth_client,
            "get_purchase_requests_summary",
            new_callable=AsyncMock,
            side_effect=[{"solicitacoes_abertas": 2}, {"solicitacoes_abertas": 5}],
        ) as summary:
            first = _state("same-session", grants)
            await _drain(first.load_dashboard())
            cache_key = _cache_key("purchase_requests", "same-session", {})
            created_at, ttl, value = session_read_cache._entries[cache_key]
            session_read_cache._entries[cache_key] = (
                created_at - dashboard_module.DASHBOARD_OPERATIONAL_TTL - 1,
                ttl,
                value,
            )
            after_expiration = _state("same-session", grants)
            await _drain(after_expiration.load_dashboard())

        self.assertEqual(summary.await_count, 2)
        self.assertEqual(first.purchase_requests_count, 2)
        self.assertEqual(after_expiration.purchase_requests_count, 5)

    async def test_administrator_bypass_is_respected_by_dashboard_grant_resolution(self):
        admin = object.__new__(AuthState)
        AuthState._init_bookkeeping(admin)
        for name, value in {
            "auth_token": "admin-session",
            "inventory_profile_code": "administrator",
            "permission_codes": [],
            "is_authenticated": True,
            "session_validation": "valid",
        }.items():
            setattr(admin, name, value)

        state = _state()
        object.__setattr__(state, "get_state", AsyncMock(return_value=admin))
        token, grants = await DashboardState._session(state)

        self.assertEqual(token, "admin-session")
        self.assertTrue(admin.has_permission("purchase_request.read"))
        self.assertTrue(grants["purchase_requests"])

    async def test_forbidden_summary_is_local_to_card_and_preserves_other_cards(self):
        state = _state(
            grants={**ALL_GRANTS, "purchase_requests": True},
        )
        product_call, _, _, stock_call, movement_call = DashboardIntegrationTests()._mock_endpoints()
        with (
            product_call,
            stock_call,
            movement_call,
            patch.object(
                auth_client,
                "get_purchase_requests_summary",
                new_callable=AsyncMock,
                side_effect=XanoPermissionError("denied", status_code=403),
            ) as summary,
        ):
            await _drain(state.load_dashboard())

        summary.assert_awaited_once()
        self.assertIsNone(state.purchase_requests_count)
        self.assertEqual(state.purchase_requests_value, "Indisponível")
        self.assertEqual(state.purchase_requests_detail, "O servidor não autorizou esta consulta")
        self.assertNotIn("purchase_requests", state.retry_sources)
        self.assertEqual(state.error_message, "")
        self.assertEqual(state.products_count, 12)
        self.assertEqual(state.below_minimum_count, 2)
        self.assertEqual(state.recent_movements[0]["tipo"], "Entrada")
        await _drain(state.load_dashboard())
        summary.assert_awaited_once()

    async def test_unauthorized_summary_uses_central_session_invalidation(self):
        state = _state(
            grants={"products": False, "stock": False, "movements": False, "purchase_requests": True}
        )
        with patch.object(
            auth_client,
            "get_purchase_requests_summary",
            new_callable=AsyncMock,
            side_effect=XanoAuthError("unauthorized", status_code=401),
        ) as summary:
            await _drain(state.load_dashboard())

        summary.assert_awaited_once()
        self.assertIsNone(state.purchase_requests_count)
        self.assertEqual(state.session_fingerprint, "")
        self.assertIn("sessão expirou", state.error_message)

    async def test_rate_limit_respects_cooldown_without_automatic_retry(self):
        state = _state(
            grants={"products": False, "stock": False, "movements": False, "purchase_requests": True}
        )
        with (
            patch.object(dashboard_module.time, "time", return_value=1000.0),
            patch.object(
                auth_client,
                "get_purchase_requests_summary",
                new_callable=AsyncMock,
                side_effect=XanoRequestError(
                    "rate limited", "TOO_MANY_REQUESTS", 429, {}, retry_after="30"
                ),
            ) as summary,
        ):
            await _drain(state.load_dashboard())
            self.assertEqual(state.purchase_requests_value, "Indisponível")
            self.assertIn("purchase_requests", state.retry_sources)
            self.assertEqual(state.retry_after_epoch, 1030.0)
            await _drain(state.load_dashboard())
            await _drain(state.load_dashboard(retry_failed_only=True))

        summary.assert_awaited_once()

    async def test_summary_cache_is_session_scoped_and_invalidated_by_successful_writes(self):
        grants = {"products": False, "stock": False, "movements": False, "purchase_requests": True}
        with patch.object(
            auth_client,
            "get_purchase_requests_summary",
            new_callable=AsyncMock,
            return_value={"solicitacoes_abertas": 4},
        ) as summary:
            first = _state("same-session", grants)
            second = _state("same-session", grants)
            other = _state("different-session", grants)
            await _drain(first.load_dashboard())
            await _drain(second.load_dashboard())
            await _drain(other.load_dashboard())

        self.assertEqual(summary.await_count, 2)
        self.assertEqual(first.purchase_requests_count, 4)
        self.assertEqual(second.purchase_requests_count, 4)
        self.assertEqual(other.purchase_requests_count, 4)
        self.assertIn("GET /purchase_requests/summary", _DASHBOARD_CACHE_ENDPOINTS)


class DashboardProductClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_products_can_filter_active_for_paged_total(self):
        from Meu_projeto.services.xano_client import auth_client

        with patch.object(
            auth_client,
            "_inventory_request",
            new_callable=AsyncMock,
            return_value={"items": [], "itemsTotal": 0},
        ) as request:
            response = await auth_client.list_products("token", page=1, per_page=1, status="ativo")

        self.assertEqual(response["itemsTotal"], 0)
        request.assert_awaited_once_with(
            "GET", "/products", "token", params={"page": 1, "per_page": 1, "status": "ativo"}
        )
