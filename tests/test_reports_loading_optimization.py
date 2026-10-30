"""Mocked coverage for lazy, session-scoped report filter option loading."""

from __future__ import annotations

import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages import relatorios as reports_module
from Meu_projeto.pages.relatorios import ReportState
from Meu_projeto.services import session_read_cache as cache_module
from Meu_projeto.services.session_read_cache import session_read_cache
from Meu_projeto.services.xano_client import (
    XanoConnectionError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestError,
    XanoServerError,
)
from Meu_projeto.services.session_read_cache import CACHE_MISS


def _state() -> ReportState:
    state = object.__new__(ReportState)
    object.__setattr__(state, "dirty_vars", set())
    values = {
        "movements": [],
        "is_loading": False,
        "error_message": "",
        "report_data_loaded": False,
        "report_results_stale": False,
        "report_retry_available": False,
        "report_retry_page": 1,
        "report_retry_apply_draft": False,
        "report_loaded_at": 0.0,
        "summary_loaded_at": 0.0,
        "current_page": 1,
        "per_page": 20,
        "total_items": 0,
        "total_pages": 1,
        "next_page": None,
        "prev_page": None,
        "start_date": "",
        "end_date": "",
        "filter_type": "",
        "filter_product_id": "",
        "filter_supplier_id": "",
        "applied_start_date": "",
        "applied_end_date": "",
        "applied_filter_type": "",
        "applied_filter_product_id": "",
        "applied_filter_supplier_id": "",
        "product_options": [],
        "product_query": "",
        "product_options_open": False,
        "product_page": 1,
        "product_has_more": False,
        "product_loading_more": False,
        "product_options_loading": False,
        "product_options_loaded": False,
        "product_options_loaded_at": 0.0,
        "product_options_stale": False,
        "supplier_options": [],
        "supplier_query": "",
        "supplier_options_open": False,
        "supplier_page": 1,
        "supplier_has_more": False,
        "supplier_loading_more": False,
        "supplier_options_loading": False,
        "supplier_options_loaded": False,
        "supplier_options_loaded_at": 0.0,
        "supplier_options_stale": False,
        "filter_options_message": "",
        "filter_options_error_kind": "",
        "preserve_product_selection_on_retry": False,
        "preserve_supplier_selection_on_retry": False,
        "movement_total": 0,
        "entry_quantity_total": "0",
        "exit_quantity_total": "0",
        "export_loading": False,
    }
    for name, value in values.items():
        setattr(state, name, value)
    return state


def _primary_report_result():
    return {
        "total_movimentacoes": 1,
        "quantidade_entradas": "2",
        "quantidade_saidas": "0",
    }


def _movement_page(*, next_page=None):
    return {
        "items": [
            {
                "data_hora": 1_700_000_000_000,
                "tipo": "entrada",
                "product_code": "P-1",
                "product_name": "Produto 1",
                "quantidade": "2",
                "user_name": "Usuário",
                "supplier_name": "Fornecedor",
                "motivo": "Reposição",
            }
        ],
        "curPage": 1,
        "itemsTotal": 1,
        "pageTotal": 1,
        "nextPage": next_page,
        "prevPage": None,
    }


async def _drain(event) -> None:
    async for _ in event:
        pass


class ReportLoadingOptimizationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()

    def tearDown(self):
        session_read_cache.clear()

    def test_filter_recovery_controls_are_compact_and_local_to_each_selector(self):
        rendered = repr(reports_module.relatorios())

        self.assertNotIn("Tentar novamente — Produtos", rendered)
        self.assertNotIn("Tentar novamente — Fornecedores", rendered)
        self.assertEqual(rendered.count("filter_options_error_kind"), 2)
        self.assertEqual(rendered.count("filter_options_message"), 2)
        self.assertIn("Aplicar filtros", rendered)
        self.assertIn("Exportar Excel", rendered)
        self.assertIn("Exportar PDF", rendered)

    async def test_initial_report_load_uses_two_calls_and_defers_filter_options(self):
        state = _state()
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                return_value=_primary_report_result(),
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ) as movements,
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                return_value={"items": [{"id": 1, "codigo": "P-1", "nome": "Produto 1"}]},
            ) as options,
        ):
            await _drain(state.load_initial())

        self.assertEqual(summary.await_count, 1)
        self.assertEqual(movements.await_count, 1)
        self.assertEqual(summary.await_count + movements.await_count, 2)
        options.assert_not_awaited()
        self.assertEqual(state.movement_total, 1)
        self.assertEqual(len(state.movements), 1)

    async def test_mocked_call_counter_compares_old_four_call_open_with_new_two_call_open(self):
        old_flow, optimized_flow = _state(), _state()
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, side_effect=["old-session", "new-session"]),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                return_value=_primary_report_result(),
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ) as movements,
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[
                    {"items": [{"id": 1, "codigo": "P-1", "nome": "Produto"}]},
                    {"items": [{"id": 2, "nome_razao_social": "Fornecedor"}]},
                ],
            ) as options,
        ):
            # Reproduce the previous eager startup: report plus both filter lists.
            await _drain(old_flow.load_initial())
            await old_flow._load_products("old-session")
            await old_flow._load_suppliers("old-session")
            old_flow_calls = summary.await_count + movements.await_count + options.await_count
            self.assertEqual(old_flow_calls, 4)

            await _drain(optimized_flow.load_initial())
            optimized_calls = (
                summary.await_count
                + movements.await_count
                + options.await_count
                - old_flow_calls
            )

        self.assertEqual(optimized_calls, 2)

    async def test_simultaneous_filter_open_events_issue_one_option_request(self):
        state = _state()
        request_started = asyncio.Event()
        finish_request = asyncio.Event()

        async def delayed_options(*_args, **_kwargs):
            request_started.set()
            await finish_request.wait()
            return {"items": [{"id": 1, "codigo": "P-1", "nome": "Produto 1"}]}

        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=delayed_options,
            ) as options,
        ):
            first = asyncio.create_task(_drain(state.open_product_options()))
            await request_started.wait()
            await _drain(state.open_product_options())
            finish_request.set()
            await first

        options.assert_awaited_once()

    async def test_opening_filter_loads_once_then_reuses_session_cache(self):
        state = _state()
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                return_value={"items": [{"id": 7, "codigo": "P-7", "nome": "Produto 7"}]},
            ) as options,
        ):
            await _drain(state.open_product_options())
            await _drain(state.open_product_options())
            state.load_page()
            await _drain(state.open_product_options())

        options.assert_awaited_once_with("session-a", "product", page=1, per_page=100)
        self.assertEqual(state.product_options, [{"id": "7", "label": "P-7 - Produto 7"}])
        self.assertTrue(state.product_options_loaded)

    async def test_open_filter_revalidates_after_option_ttl_expires(self):
        state = _state()
        now = [50.0]
        with (
            patch.object(reports_module.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[
                    {"items": [{"id": 1, "codigo": "P-1", "nome": "Antigo"}]},
                    {"items": [{"id": 1, "codigo": "P-1", "nome": "Atualizado"}]},
                ],
            ) as options,
        ):
            await _drain(state.open_product_options())
            await _drain(state.open_product_options())
            now[0] += reports_module.REPORT_PRODUCT_OPTIONS_TTL + 1
            await _drain(state.open_product_options())

        self.assertEqual(options.await_count, 2)
        self.assertEqual(state.product_options[0]["label"], "P-1 - Atualizado")

    async def test_supplier_options_refresh_after_supplier_ttl_expires(self):
        state = _state()
        now = [80.0]
        with (
            patch.object(reports_module.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[
                    {"items": [{"id": 2, "nome_razao_social": "Fornecedor antigo"}]},
                    {"items": [{"id": 2, "nome_razao_social": "Fornecedor atual"}]},
                ],
            ) as options,
        ):
            await _drain(state.open_supplier_options())
            now[0] += reports_module.REPORT_SUPPLIER_OPTIONS_TTL + 1
            await _drain(state.open_supplier_options())

        self.assertEqual(options.await_count, 2)
        self.assertEqual(state.supplier_options[0]["label"], "Fornecedor atual")

    async def test_product_options_are_isolated_by_session(self):
        first, second = _state(), _state()
        with (
            patch.object(
                ReportState,
                "_session_token",
                new_callable=AsyncMock,
                side_effect=["session-a", "session-b"],
            ),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[
                    {"items": [{"id": 1, "codigo": "A", "nome": "Privado A"}]},
                    {"items": [{"id": 2, "codigo": "B", "nome": "Privado B"}]},
                ],
            ) as options,
        ):
            await _drain(first.open_product_options())
            await _drain(second.open_product_options())

        self.assertEqual(options.await_count, 2)
        self.assertEqual(first.product_options[0]["label"], "A - Privado A")
        self.assertEqual(second.product_options[0]["label"], "B - Privado B")

    async def test_local_filter_edits_do_not_call_xano(self):
        state = _state()
        state.product_options = [{"id": "1", "label": "P-1 - Produto 1"}]
        with patch.object(
            reports_module.auth_client,
            "list_report_options",
            new_callable=AsyncMock,
        ) as options:
            state.change_start_date("2026-10-01")
            state.change_end_date("2026-10-14")
            state.change_type("entrada")
            state.search_products("produto")
            state.select_product("1")

        options.assert_not_awaited()
        self.assertEqual(state.filter_product_id, "1")
        self.assertEqual(state.filter_type, "entrada")

    async def test_initial_429_does_not_trigger_filter_option_queries(self):
        state = _state()
        rate_limit = XanoRequestError(
            "O Xano est\u00e1 limitando as solicita\u00e7\u00f5es. Aguarde 9 segundos e tente novamente.",
            "TOO_MANY_REQUESTS",
            429,
            {},
            "9",
        )
        self.assertEqual(rate_limit.origin, "remote_xano")
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                side_effect=rate_limit,
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
            ) as options,
        ):
            await _drain(state.load_initial())

        summary.assert_awaited_once()
        options.assert_not_awaited()
        self.assertIn("9 segundos", state.error_message)
        self.assertIn("Xano está limitando", state.error_message)
        self.assertFalse(state.is_loading)

    async def test_local_rate_limit_preserves_coordinator_wait_message(self):
        state = _state()
        rate_limit = XanoRateLimitError(7)
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                side_effect=rate_limit,
            ),
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
            ) as options,
        ):
            await _drain(state.load_initial())

        self.assertIn("Limite local", state.error_message)
        self.assertIn("Aguarde 7 segundo(s)", state.error_message)
        options.assert_not_awaited()
        self.assertFalse(state.is_loading)

    async def test_stale_filter_options_survive_429_and_manual_reopen_recovers(self):
        state = _state()
        now = [100.0]
        key = session_read_cache.key(
            "report_filter_options",
            "GET /report_options",
            "session-a",
            {"kind": "product", "page": 1, "per_page": 100},
        )
        with patch.object(cache_module.time, "monotonic", side_effect=lambda: now[0]):
            session_read_cache.set(
                key,
                {"items": [{"id": "1", "label": "P-1 - Antigo"}], "has_more": False},
                reports_module.REPORT_PRODUCT_OPTIONS_TTL,
            )
            now[0] += reports_module.REPORT_PRODUCT_OPTIONS_TTL + 1
            with (
                patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
                patch.object(
                    reports_module.auth_client,
                    "list_report_options",
                    new_callable=AsyncMock,
                    side_effect=[
                        XanoRequestError("Aguarde.", "TOO_MANY_REQUESTS", 429, {}, "5"),
                        {"items": [{"id": 1, "codigo": "P-1", "nome": "Atualizado"}]},
                    ],
                ) as options,
            ):
                await _drain(state.open_product_options())
                self.assertEqual(options.await_count, 1)
                self.assertIn("desatualizadas", state.filter_options_message)
                self.assertEqual(state.product_options[0]["label"], "P-1 - Antigo")
                state.product_options_open = False
                await _drain(state.open_product_options())

        self.assertEqual(options.await_count, 2)
        self.assertEqual(state.product_options[0]["label"], "P-1 - Atualizado")
        self.assertTrue(state.product_options_loaded)
        self.assertEqual(state.filter_options_message, "")

    async def test_load_more_options_preserves_pagination_and_deduplicates_ids(self):
        state = _state()
        first_page = [
            {"id": index, "codigo": f"P-{index}", "nome": f"Produto {index}"}
            for index in range(100)
        ]
        second_page = [
            {"id": 99, "codigo": "P-99", "nome": "Duplicado"},
            {"id": 100, "codigo": "P-100", "nome": "Produto 100"},
        ]
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[{"items": first_page}, {"items": second_page}],
            ) as options,
        ):
            await _drain(state.open_product_options())
            await state.load_more_products()

        self.assertEqual(options.await_count, 2)
        self.assertEqual(state.product_page, 2)
        self.assertEqual(len(state.product_options), 101)
        self.assertEqual(state.product_options[-1]["id"], "100")

    async def test_export_still_fetches_all_filtered_pages_without_using_options_cache(self):
        state = _state()
        state.applied_filter_type = "entrada"
        responses = [_movement_page(next_page=2), _movement_page()]
        with patch.object(
            reports_module.auth_client,
            "list_movements",
            new_callable=AsyncMock,
            side_effect=responses,
        ) as movements:
            rows = await state._all_filtered_rows("session-a")

        self.assertEqual(len(rows), 2)
        self.assertEqual(movements.await_count, 2)
        self.assertEqual(movements.await_args_list[0].kwargs["tipo"], "entrada")
        self.assertEqual(movements.await_args_list[1].kwargs["page"], 2)
        self.assertTrue(state._build_xlsx(rows).startswith(b"PK"))
        self.assertTrue(state._build_pdf(rows).startswith(b"%PDF"))

    async def test_full_filter_flow_uses_six_calls_then_repeated_apply_uses_none(self):
        state = _state()

        async def options(_token, kind, **_kwargs):
            if kind == "product":
                return {"items": [{"id": 7, "codigo": "P-7", "nome": "Produto 7"}]}
            return {"items": [{"id": 9, "nome_razao_social": "Fornecedor 9"}]}

        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                return_value=_primary_report_result(),
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ) as movements,
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=options,
            ) as option_calls,
        ):
            await _drain(state.load_initial())
            await _drain(state.open_product_options())
            state.select_product("7")
            await _drain(state.open_supplier_options())
            state.select_supplier("9")
            self.assertTrue(state.filters_dirty)
            apply_event = await state.apply_filters()
            if apply_event is not None:
                await _drain(state.load_report(1, apply_draft=True))

            self.assertFalse(state.filters_dirty)
            repeated_apply = await state.apply_filters()
            self.assertIsNone(repeated_apply)

        total = summary.await_count + movements.await_count + option_calls.await_count
        self.assertEqual(total, 6)
        self.assertEqual(summary.await_count, 2)
        self.assertEqual(movements.await_count, 2)
        self.assertEqual(option_calls.await_count, 2)
        self.assertEqual(state.applied_filter_product_id, "7")
        self.assertEqual(state.applied_filter_supplier_id, "9")

    async def test_failed_filter_apply_preserves_previous_results_and_applied_filters(self):
        state = _state()
        state.report_data_loaded = True
        state.movements = [{"product_name": "Resultado anterior"}]
        state.movement_total = 4
        state.entry_quantity_total = "12"
        state.exit_quantity_total = "3"
        state.applied_filter_type = "entrada"
        state.filter_type = "saida"
        failure = XanoRequestError(
            "O Xano está limitando as solicitações. Aguarde 9 segundo(s) e tente novamente.",
            "TOO_MANY_REQUESTS",
            429,
            {},
            "9",
        )
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                side_effect=failure,
            ),
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ),
        ):
            await _drain(state.load_report(1, apply_draft=True))

        self.assertEqual(state.applied_filter_type, "entrada")
        self.assertEqual(state.filter_type, "saida")
        self.assertTrue(state.filters_dirty)
        self.assertEqual(state.movements, [{"product_name": "Resultado anterior"}])
        self.assertEqual(state.movement_total, 4)
        self.assertEqual(state.entry_quantity_total, "12")
        self.assertEqual(state.exit_quantity_total, "3")
        self.assertIn("filtros aplicados anteriormente", state.error_message)
        self.assertIn("9 segundo(s)", state.error_message)
        self.assertTrue(state.report_results_stale)
        self.assertTrue(state.report_retry_available)
        self.assertFalse(state.can_export)

    async def test_empty_options_are_distinct_from_failed_options_and_failures_are_not_cached(self):
        session_read_cache.clear()
        state = _state()
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-empty"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as options,
        ):
            await _drain(state.open_product_options())

        self.assertEqual(options.await_count, 1)
        self.assertTrue(state.product_options_loaded)
        self.assertEqual(state.product_options, [])
        self.assertEqual(state.filter_options_error_kind, "")
        self.assertEqual(state.product_options_empty_message, "Nenhuma opção encontrada.")

        session_read_cache.clear()
        failed = _state()
        key = session_read_cache.key(
            "report_filter_options",
            "GET /report_options",
            "session-failed",
            {"kind": "supplier", "page": 1, "per_page": 100},
        )
        failure = XanoRequestError("Erro temporário.", "API_ERROR", 500, {})
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-failed"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=failure,
            ),
        ):
            await _drain(failed.open_supplier_options())

        self.assertFalse(failed.supplier_options_loaded)
        self.assertEqual(failed.supplier_options, [])
        self.assertEqual(failed.filter_options_error_kind, "supplier")
        self.assertIn("Não foi possível confirmar", failed.supplier_options_empty_message)
        self.assertNotIn("Nenhuma opção", failed.supplier_options_empty_message)
        cached, _fresh = session_read_cache.get(key, 120)
        self.assertIs(cached, CACHE_MISS)

    async def test_option_failures_500_429_403_404_and_connection_are_error_states(self):
        failures = [
            XanoRequestError("Server error.", "API_ERROR", 500, {}),
            XanoRequestError("Rate limited.", "TOO_MANY_REQUESTS", 429, {}, "5"),
            XanoPermissionError("Forbidden.", status_code=403),
            XanoRequestError("Not found.", "API_ERROR", 404, {}),
            XanoConnectionError("Connection unavailable."),
        ]
        for index, failure in enumerate(failures):
            with self.subTest(failure=type(failure).__name__, status=getattr(failure, "status_code", None)):
                session_read_cache.clear()
                state = _state()
                with (
                    patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value=f"session-{index}"),
                    patch.object(
                        reports_module.auth_client,
                        "list_report_options",
                        new_callable=AsyncMock,
                        side_effect=failure,
                    ) as options,
                ):
                    await _drain(state.open_supplier_options())

                self.assertEqual(options.await_count, 1)
                self.assertEqual(state.filter_options_error_kind, "supplier")
                self.assertIn("Não foi possível confirmar", state.supplier_options_empty_message)
                self.assertTrue(state.filter_options_message)
                key = session_read_cache.key(
                    "report_filter_options",
                    "GET /report_options",
                    f"session-{index}",
                    {"kind": "supplier", "page": 1, "per_page": 100},
                )
                cached, _fresh = session_read_cache.get(key, 120)
                self.assertIs(cached, CACHE_MISS)

    async def test_manual_option_retry_preserves_selection_and_loads_real_options(self):
        session_read_cache.clear()
        state = _state()
        state.filter_supplier_id = "8"
        state.supplier_query = "Fornecedor 8"
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-retry"),
            patch.object(
                reports_module.auth_client,
                "list_report_options",
                new_callable=AsyncMock,
                side_effect=[
                    XanoRequestError("Server error.", "API_ERROR", 500, {}),
                    {"items": [{"id": 8, "nome_razao_social": "Fornecedor 8"}]},
                ],
            ) as options,
        ):
            await _drain(state.open_supplier_options())
            self.assertEqual(state.filter_supplier_id, "")
            state.filter_supplier_id = "8"
            state.supplier_query = "Fornecedor 8"
            retry_event = state.retry_supplier_options()
            self.assertIsNotNone(retry_event)
            await _drain(state.open_supplier_options())

        self.assertEqual(options.await_count, 2)
        self.assertEqual(state.filter_supplier_id, "8")
        self.assertEqual(state.supplier_query, "Fornecedor 8")
        self.assertEqual(state.supplier_options[0]["id"], "8")
        self.assertTrue(state.supplier_options_loaded)
        self.assertEqual(state.filter_options_error_kind, "")
        self.assertEqual(state.filter_options_message, "")

    async def test_export_is_blocked_until_draft_filters_are_successfully_applied(self):
        state = _state()
        state.report_data_loaded = True
        state.movements = [{"product_name": "Resultado anterior"}]
        state.applied_filter_type = "entrada"
        state.filter_type = "saida"
        state.report_results_stale = True
        with patch.object(
            reports_module.auth_client,
            "list_movements",
            new_callable=AsyncMock,
        ) as movements:
            await _drain(state.export_excel())
            await _drain(state.export_pdf())

        movements.assert_not_awaited()
        self.assertFalse(state.can_export)

    async def test_missing_report_grant_clears_private_report_and_option_data(self):
        session_read_cache.clear()
        state = _state()
        state.report_data_loaded = True
        state.movements = [{"product_name": "Privado"}]
        state.movement_total = 2
        state.product_options = [{"id": "1", "label": "Privado"}]
        state.supplier_options = [{"id": "2", "label": "Privado"}]
        cache_key = session_read_cache.key(
            "report_filter_options",
            "GET /report_options",
            "session-revoked",
            {"kind": "product", "page": 1, "per_page": 100},
        )
        session_read_cache.set(cache_key, {"items": [{"id": "1"}], "has_more": False}, 30)
        auth_state = SimpleNamespace(
            is_authenticated=True,
            auth_token="session-revoked",
            has_permission=lambda code: False,
        )

        with patch.object(
            ReportState,
            "get_state",
            new_callable=AsyncMock,
            return_value=auth_state,
        ):
            self.assertEqual(await state._session_token(), "")

        self.assertEqual(state.movements, [])
        self.assertEqual(state.movement_total, 0)
        self.assertEqual(state.product_options, [])
        self.assertEqual(state.supplier_options, [])
        cached, _fresh = session_read_cache.get(cache_key, 30)
        self.assertIs(cached, CACHE_MISS)

    async def test_report_retry_applies_draft_only_after_success_and_restores_export(self):
        state = _state()
        state.report_data_loaded = True
        state.report_loaded_at = 0.0
        state.summary_loaded_at = 0.0
        state.movements = [{"product_name": "Resultado aplicado"}]
        state.applied_filter_type = "entrada"
        state.filter_type = "saida"
        failure = XanoRequestError("Erro temporário.", "API_ERROR", 500, {})
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                side_effect=[failure, _primary_report_result()],
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                side_effect=[_movement_page(), _movement_page()],
            ) as movements,
        ):
            await _drain(state.load_report(1, apply_draft=True))
            self.assertTrue(state.report_results_stale)
            self.assertTrue(state.report_retry_available)
            retry_event = state.retry_report()
            self.assertIsNotNone(retry_event)
            await _drain(state.load_report(state.report_retry_page, state.report_retry_apply_draft))

        self.assertEqual(summary.await_count, 2)
        self.assertEqual(movements.await_count, 2)
        self.assertEqual(state.applied_filter_type, "saida")
        self.assertFalse(state.report_results_stale)
        self.assertFalse(state.report_retry_available)
        self.assertTrue(state.can_export)

    async def test_pagination_reuses_applied_summary_and_loads_only_the_requested_page(self):
        state = _state()
        state.report_data_loaded = True
        state.report_loaded_at = reports_module.time.monotonic()
        state.summary_loaded_at = reports_module.time.monotonic()
        state.applied_filter_type = "entrada"
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ) as movements,
        ):
            await _drain(state.load_report(2))

        summary.assert_not_awaited()
        movements.assert_awaited_once()
        self.assertEqual(movements.await_args.kwargs["page"], 2)
        self.assertEqual(state.applied_filter_type, "entrada")

    async def test_same_filters_refresh_after_report_results_ttl_expires(self):
        state = _state()
        state.report_data_loaded = True
        state.report_loaded_at = reports_module.time.monotonic()
        state.summary_loaded_at = state.report_loaded_at
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                return_value=_primary_report_result(),
            ) as summary,
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ) as movements,
        ):
            self.assertIsNone(await state.apply_filters())
            state.report_loaded_at -= reports_module.REPORT_RESULTS_TTL + 1
            state.summary_loaded_at -= reports_module.REPORT_RESULTS_TTL + 1
            apply_event = await state.apply_filters()
            self.assertIsNotNone(apply_event)
            await _drain(state.load_report(1, apply_draft=True))

        summary.assert_awaited_once()
        movements.assert_awaited_once()

    async def test_permission_revocation_clears_previously_loaded_report_data(self):
        state = _state()
        state.report_data_loaded = True
        state.report_loaded_at = 0.0
        state.summary_loaded_at = 0.0
        state.movements = [{"product_name": "Privado"}]
        state.movement_total = 1
        with (
            patch.object(ReportState, "_session_token", new_callable=AsyncMock, return_value="session-a"),
            patch.object(
                reports_module.auth_client,
                "get_movements_summary",
                new_callable=AsyncMock,
                side_effect=XanoPermissionError("PERMISSION_DENIED", status_code=403),
            ),
            patch.object(
                reports_module.auth_client,
                "list_movements",
                new_callable=AsyncMock,
                return_value=_movement_page(),
            ),
        ):
            await _drain(state.load_report(1))

        self.assertEqual(state.movements, [])
        self.assertEqual(state.movement_total, 0)
        self.assertFalse(state.report_data_loaded)


if __name__ == "__main__":
    unittest.main()
