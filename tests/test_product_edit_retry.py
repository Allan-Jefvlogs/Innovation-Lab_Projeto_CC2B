"""Isolated edit-form retry and 429 handling tests for Products."""

from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

import httpx

from Meu_projeto.pages import produtos as products_module
from Meu_projeto.pages.produtos import ProductsState, _feedback, _product_form, auth_client
from Meu_projeto.services.xano_client import XanoRequestCoordinator, XanoRequestError


MOCK_BASE_URL = "https://products-edit-test.invalid"


def _product() -> dict[str, object]:
    return {
        "id": 1,
        "codigo": "TEST-1",
        "nome": "Produto de teste",
        "descricao": "",
        "categoria_id": 5,
        "fornecedor_padrao_id": None,
        "unidade_medida": "UN",
        "estoque_minimo": 0,
        "status": "ativo",
    }


def _state(*, loaded: bool = False) -> ProductsState:
    state = object.__new__(ProductsState)
    object.__setattr__(state, "dirty_vars", set())
    values = {
        "is_loading": False,
        "is_saving": False,
        "is_status_loading": False,
        "has_loaded_product": loaded,
        "edit_load_failed": False,
        "can_retry_edit_load": False,
        "can_read_products": True,
        "can_read_categories": True,
        "can_read_suppliers": True,
        "can_update_products": True,
        "can_activate_products": True,
        "can_inactivate_products": False,
        "product_id": 1 if loaded else 0,
        "original_product": (
            {key: str(value) if value is not None else "" for key, value in _product().items()}
            if loaded
            else {}
        ),
        "codigo": "TEST-1" if loaded else "",
        "nome": "Produto de teste" if loaded else "",
        "descricao": "",
        "unidade_medida": "UN" if loaded else "",
        "estoque_minimo": "0" if loaded else "",
        "category_options": ([{"id": "5", "label": "Categoria", "disabled": "false"}] if loaded else []),
        "category_selection": "5" if loaded else "",
        "category_search_query": "Categoria" if loaded else "",
        "category_has_more": False,
        "category_error_message": "",
        "supplier_options": ([{"id": "none", "label": "Sem fornecedor padrão", "disabled": "false"}] if loaded else []),
        "supplier_selection": "none",
        "supplier_search_query": "Sem fornecedor padrão",
        "supplier_has_more": False,
        "supplier_error_message": "",
        "original_product_status": "ativo" if loaded else "",
        "current_product_status": "ativo" if loaded else "",
        "error_message": "",
        "success_message": "",
    }
    for name, value in values.items():
        setattr(state, name, value)

    async def authorized_session():
        state.can_read_products = True
        state.can_read_categories = True
        state.can_read_suppliers = True
        state.can_update_products = True
        state.can_activate_products = True
        state.can_inactivate_products = False
        return "mock-session-token", True

    object.__setattr__(state, "_session", AsyncMock(side_effect=authorized_session))
    return state


async def _drain(event):
    async for _ in event:
        pass


def _walk_components(component):
    yield component
    for child in getattr(component, "children", []) or []:
        yield from _walk_components(child)


class ProductEditRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        products_module._cache_clear()

    def tearDown(self):
        products_module._cache_clear()

    def _route(self):
        return patch.object(
            ProductsState,
            "router",
            new_callable=PropertyMock,
            return_value=SimpleNamespace(url=SimpleNamespace(path="/produtos/1/editar")),
        )

    def _install_transport(self, transport):
        real_async_client = httpx.AsyncClient

        def make_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        return patch("Meu_projeto.services.xano_client.httpx.AsyncClient", side_effect=make_client)

    async def test_429_shows_one_feedback_and_skips_dependent_queries_and_edit_fields(self):
        state = _state()
        transport_calls: list[str] = []

        def handle(request: httpx.Request):
            transport_calls.append(request.url.path)
            return httpx.Response(
                429,
                headers={"Retry-After": "5"},
                json={"code": "TOO_MANY_REQUESTS"},
                request=request,
            )

        transport = httpx.MockTransport(handle)
        coordinator = XanoRequestCoordinator(5, 20)
        with (
            self._route(),
            patch.object(auth_client, "base_url", MOCK_BASE_URL),
            patch.object(auth_client, "coordinator", coordinator),
            patch.object(auth_client, "list_categories", new_callable=AsyncMock) as categories,
            patch.object(auth_client, "list_suppliers", new_callable=AsyncMock) as suppliers,
            self._install_transport(transport),
        ):
            await _drain(state.load_edit_form())

        self.assertFalse(state.has_loaded_product)
        self.assertTrue(state.can_retry_edit_load)
        self.assertEqual(state.error_message.count("429"), 0)
        self.assertIn("limitando", state.error_message)
        self.assertEqual(len(transport_calls), 1)
        self.assertTrue(transport_calls[0].endswith("/products/by_id/1"))
        categories.assert_not_awaited()
        suppliers.assert_not_awaited()

        # The edit fields are only included in the has_loaded_product branch, and
        # the 429 feedback is rendered once in the edit form.
        with patch("Meu_projeto.pages.produtos._feedback", wraps=_feedback) as feedback:
            edit_form = _product_form(is_edit=True)
            rendered = repr(edit_form)
        self.assertEqual(feedback.call_count, 1)
        self.assertIn("has_loaded_product", rendered)
        self.assertIn("Tentar novamente", rendered)
        loaded_gate = next(
            component
            for component in _walk_components(edit_form)
            if getattr(component, "cond", None) is not None
            and "has_loaded_product" in str(component.cond)
        )
        self.assertGreater(len(loaded_gate.children[0].children), 0)
        self.assertEqual(loaded_gate.children[1].children, [])

        with patch.object(auth_client, "update_product", new_callable=AsyncMock) as update:
            await _drain(state.update_product())
        update.assert_not_awaited()

    async def test_manual_retry_respects_cooldown_then_recovers_and_edits(self):
        current_time = [200.0]
        coordinator = XanoRequestCoordinator(
            5,
            20,
            clock=lambda: current_time[0],
            wall_clock=lambda: current_time[0],
        )
        outcomes = [
            (429, {"Retry-After": "5"}, {"code": "TOO_MANY_REQUESTS"}),
            (200, {}, _product()),
            (200, {}, {"items": [{"id": 5, "nome": "Categoria", "status": "ativo"}]}),
            (200, {}, {"items": []}),
        ]
        requests: list[str] = []

        def handle(request: httpx.Request):
            requests.append(request.url.path)
            status, headers, payload = outcomes.pop(0)
            return httpx.Response(status, headers=headers, json=payload, request=request)

        state = _state()
        with (
            self._route(),
            patch.object(auth_client, "base_url", MOCK_BASE_URL),
            patch.object(auth_client, "coordinator", coordinator),
            self._install_transport(httpx.MockTransport(handle)),
        ):
            await _drain(state.load_edit_form())
            self.assertEqual(len(requests), 1)
            self.assertTrue(state.can_retry_edit_load)

            # A manual click during Retry-After is rejected by the shared client
            # coordinator; it does not reach MockTransport or the Xano host.
            await _drain(state.load_edit_form())
            self.assertEqual(len(requests), 1)
            self.assertTrue(state.can_retry_edit_load)

            current_time[0] += 5
            await _drain(state.load_edit_form())

        self.assertTrue(state.has_loaded_product)
        self.assertFalse(state.edit_load_failed)
        self.assertFalse(state.can_retry_edit_load)
        self.assertEqual(state.nome, "Produto de teste")
        self.assertEqual(state.category_selection, "5")
        self.assertEqual(len(requests), 4)
        self.assertTrue(requests[0].endswith("/products/by_id/1"))

        state.nome = "Produto editado"
        with patch.object(auth_client, "update_product", new_callable=AsyncMock) as update:
            await _drain(state.update_product())
        update.assert_awaited_once_with(
            "mock-session-token", 1, {"nome": "Produto editado"}
        )

    async def test_dependent_failure_preserves_loaded_data_and_blocks_save(self):
        state = _state(loaded=True)
        original_categories = list(state.category_options)
        product = {**_product(), "nome": "Dados carregados"}
        with (
            self._route(),
            patch.object(auth_client, "get_product", new_callable=AsyncMock, return_value=product),
            patch.object(
                auth_client,
                "list_categories",
                new_callable=AsyncMock,
                side_effect=XanoRequestError(
                    "O Xano está limitando as solicitações. Aguarde 5 segundos.",
                    "TOO_MANY_REQUESTS",
                    429,
                    {},
                    retry_after="5",
                ),
            ),
            patch.object(
                auth_client,
                "list_suppliers",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as suppliers,
            patch.object(auth_client, "update_product", new_callable=AsyncMock) as update,
        ):
            await _drain(state.load_edit_form())
            self.assertTrue(state.has_loaded_product)
            self.assertEqual(state.nome, "Dados carregados")
            self.assertEqual(state.category_options, original_categories)
            self.assertTrue(state.can_retry_edit_load)

            state.nome = "Alteração pendente"
            await _drain(state.update_product())

        update.assert_not_awaited()
        suppliers.assert_not_awaited()
        self.assertIn("não foi possível confirmar", state.error_message.lower())

    async def test_simultaneous_loads_issue_only_one_product_request(self):
        state = _state()
        request_started = asyncio.Event()
        release_request = asyncio.Event()
        product_calls = 0

        async def delayed_product(*_args):
            nonlocal product_calls
            product_calls += 1
            request_started.set()
            await release_request.wait()
            return _product()

        with (
            self._route(),
            patch.object(auth_client, "get_product", new_callable=AsyncMock, side_effect=delayed_product),
            patch.object(
                auth_client,
                "list_categories",
                new_callable=AsyncMock,
                return_value={"items": [{"id": 5, "nome": "Categoria", "status": "ativo"}]},
            ),
            patch.object(auth_client, "list_suppliers", new_callable=AsyncMock, return_value={"items": []}),
        ):
            first = asyncio.create_task(_drain(state.load_edit_form()))
            await asyncio.wait_for(request_started.wait(), timeout=1)
            await _drain(state.load_edit_form())
            self.assertEqual(product_calls, 1)
            release_request.set()
            await first

        self.assertTrue(state.has_loaded_product)
        self.assertEqual(product_calls, 1)


if __name__ == "__main__":
    unittest.main()
