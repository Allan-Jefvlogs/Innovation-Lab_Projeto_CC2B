"""Isolated cache tests for the Products module; all Xano calls are mocked."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from Meu_projeto.pages import produtos as products_module
from Meu_projeto.pages.produtos import ProductsState
from Meu_projeto.services import session_read_cache as cache_module
from Meu_projeto.services.xano_client import XanoRateLimitError, XanoRequestError


def _product(name: str = "Produto A") -> dict[str, object]:
    return {
        "id": 1,
        "codigo": "A-1",
        "nome": name,
        "categoria_id": 5,
        "categoria_nome": "Categoria A",
        "descricao": "",
        "fornecedor_padrao_id": None,
        "unidade_medida": "UN",
        "estoque_minimo": 0,
        "status": "ativo",
    }


def _state(token: str = "session-a") -> ProductsState:
    state = object.__new__(ProductsState)
    object.__setattr__(state, "dirty_vars", set())
    values = {
        "is_loading": False,
        "is_saving": False,
        "is_status_loading": False,
        "can_read_products": False,
        "can_read_categories": False,
        "can_read_suppliers": False,
        "can_create_products": False,
        "can_update_products": False,
        "can_activate_products": False,
        "can_inactivate_products": False,
        "products": [],
        "has_products": False,
        "products_stale": False,
        "products_status_message": "",
        "products_session_fingerprint": "",
        "error_message": "",
        "search_query": "",
        "has_loaded_product": False,
        "edit_load_failed": False,
        "category_error_message": "",
        "supplier_error_message": "",
        "product_id": 1,
        "original_product": {},
        "codigo": "",
        "nome": "",
        "descricao": "",
        "unidade_medida": "",
        "estoque_minimo": "",
        "category_options": [],
        "category_selection": "",
        "supplier_options": [],
        "supplier_selection": "none",
        "original_product_status": "ativo",
        "current_product_status": "ativo",
    }
    for key, value in values.items():
        setattr(state, key, value)

    async def session():
        state.can_read_products = True
        state.can_read_categories = True
        state.can_read_suppliers = True
        state.can_create_products = True
        state.can_update_products = True
        state.can_activate_products = True
        state.can_inactivate_products = True
        return token, True

    object.__setattr__(state, "_session", AsyncMock(side_effect=session))
    return state


async def _drain(event) -> None:
    async for _ in event:
        pass


class ProductCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        products_module._cache_clear()

    def tearDown(self):
        products_module._cache_clear()

    def test_product_list_hides_header_refresh_and_keeps_error_recovery(self):
        rendered = repr(products_module.produtos())

        self.assertNotIn("Atualizar Produtos", rendered)
        self.assertIn("Novo produto", rendered)
        self.assertIn("Tentar atualizar", rendered)
        self.assertIn("Tentar novamente", rendered)
        self.assertEqual(rendered.count("refresh_products"), 2)

    async def _load_listing(self, state: ProductsState) -> None:
        await _drain(state.load_products())

    async def test_first_list_load_calls_xano_and_second_load_uses_ttl_cache(self):
        state = _state()
        with (
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [_product()]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": [{"product_id": 1, "quantidade_disponivel": 4}]},
            ) as list_stock,
        ):
            await self._load_listing(state)
            await self._load_listing(state)

        list_products.assert_awaited_once_with("session-a", page=1, per_page=100)
        list_stock.assert_awaited_once_with("session-a", page=1, per_page=100)
        self.assertEqual(state.products[0]["nome"], "Produto A")
        self.assertFalse(state.products_stale)

    async def test_expired_product_cache_revalidates_with_xano(self):
        state = _state()
        now = [100.0]
        with (
            patch.object(cache_module.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                side_effect=[{"items": [_product()]}, {"items": [_product("Atualizado")]}],
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ),
        ):
            await self._load_listing(state)
            now[0] += products_module.PRODUCTS_CACHE_TTL_SECONDS + 1
            await self._load_listing(state)

        self.assertEqual(list_products.await_count, 2)
        self.assertEqual(state.products[0]["nome"], "Atualizado")

    async def test_reference_cache_uses_ttl_and_separates_query_parameters(self):
        loader = AsyncMock(
            side_effect=[
                {"items": [{"id": 1, "nome": "Categoria", "internal_secret": "omit"}]},
                {"items": [{"id": 2}]},
            ]
        )
        first = await products_module._cached_reference_call(
            "categories", "session-a", {"page": 1, "status": "ativo"}, loader,
            cache_fields=("id",),
        )
        repeated = await products_module._cached_reference_call(
            "categories", "session-a", {"status": "ativo", "page": 1}, loader,
            cache_fields=("id",),
        )
        second_page = await products_module._cached_reference_call(
            "categories", "session-a", {"page": 2, "status": "ativo"}, loader,
            cache_fields=("id",),
        )

        self.assertEqual(first["items"][0]["internal_secret"], "omit")
        self.assertEqual(repeated["items"], [{"id": 1}])
        self.assertEqual(second_page, {"items": [{"id": 2}]})
        self.assertEqual(loader.await_count, 2)

    async def test_reference_cache_is_bypassed_without_current_read_grant(self):
        key = products_module._cache_key(
            "categories", "session-a", {"page": 1, "status": "ativo"}
        )
        products_module._cache_set(key, {"items": [{"id": 1, "nome": "Cached"}]})
        loader = AsyncMock(return_value={"items": [{"id": 2, "nome": "Fresh"}]})

        result = await products_module._cached_reference_call(
            "categories",
            "session-a",
            {"page": 1, "status": "ativo"},
            loader,
            cache_allowed=False,
            cache_fields=("id", "nome"),
        )

        loader.assert_awaited_once()
        self.assertEqual(result["items"][0]["nome"], "Fresh")

    async def test_reference_cache_expires_after_configured_ttl(self):
        now = [0.0]
        loader = AsyncMock(side_effect=[{"items": [{"id": 1}]}, {"items": [{"id": 2}]}])
        with patch.object(cache_module.time, "monotonic", side_effect=lambda: now[0]):
            first = await products_module._cached_reference_call(
                "suppliers", "session-a", {"page": 1, "status": "ativo"}, loader,
                cache_fields=("id",),
            )
            now[0] += products_module.REFERENCE_CACHE_TTL_SECONDS + 1
            second = await products_module._cached_reference_call(
                "suppliers", "session-a", {"page": 1, "status": "ativo"}, loader,
                cache_fields=("id",),
            )

        self.assertEqual(first, {"items": [{"id": 1}]})
        self.assertEqual(second, {"items": [{"id": 2}]})
        self.assertEqual(loader.await_count, 2)

    async def test_cache_is_isolated_by_session(self):
        first_state, second_state = _state("session-a"), _state("session-b")
        with (
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                side_effect=lambda token, **_: {"items": [_product(token)]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ),
        ):
            await self._load_listing(first_state)
            await self._load_listing(second_state)
            await self._load_listing(first_state)

        self.assertEqual(list_products.await_count, 2)
        self.assertEqual(first_state.products[0]["nome"], "session-a")
        self.assertEqual(second_state.products[0]["nome"], "session-b")

    async def test_product_post_invalidation_is_limited_to_current_session(self):
        key_a = products_module._products_listing_key("session-a")
        key_b = products_module._products_listing_key("session-b")
        products_module._cache_set(key_a, [{"id": "1"}])
        products_module._cache_set(key_b, [{"id": "2"}])

        products_module._invalidate_products_cache("session-a")

        value_a, fresh_a = products_module._cache_get(
            key_a, products_module.PRODUCTS_CACHE_TTL_SECONDS
        )
        value_b, fresh_b = products_module._cache_get(
            key_b, products_module.PRODUCTS_CACHE_TTL_SECONDS
        )
        self.assertIs(value_a, products_module._CACHE_MISS)
        self.assertFalse(fresh_a)
        self.assertEqual(value_b, [{"id": "2"}])
        self.assertTrue(fresh_b)

    async def test_manual_refresh_fetches_fresh_data_even_inside_ttl(self):
        state = _state()
        with (
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                side_effect=[{"items": [_product()]}, {"items": [_product("Nova versao")]}],
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ),
        ):
            await self._load_listing(state)
            await _drain(state.refresh_products())

        self.assertEqual(list_products.await_count, 2)
        self.assertEqual(state.products[0]["nome"], "Nova versao")
        self.assertFalse(state.products_stale)

    async def test_429_preserves_expired_listing_and_marks_it_stale(self):
        state = _state()
        now = [10.0]
        with (
            patch.object(cache_module.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                side_effect=[{"items": [_product()]}, XanoRateLimitError(12)],
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as list_stock,
        ):
            await self._load_listing(state)
            now[0] += products_module.PRODUCTS_CACHE_TTL_SECONDS + 1
            await _drain(state.refresh_products())

        self.assertEqual(list_products.await_count, 2)
        self.assertEqual(list_stock.await_count, 1)
        self.assertTrue(state.has_products)
        self.assertTrue(state.products_stale)
        self.assertIn("desatualizada", state.products_status_message)
        self.assertEqual(state.products[0]["nome"], "Produto A")

    async def test_permission_failure_does_not_retain_private_cached_products(self):
        state = _state()
        with (
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [_product()]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ),
        ):
            await self._load_listing(state)
            state.products = [{"id": "1", "nome": "Privado"}]
            state.has_products = True
            list_products.side_effect = XanoRequestError(
                "Forbidden", "PERMISSION_DENIED", 403, {}
            )
            await _drain(state.refresh_products())

        self.assertEqual(list_products.await_count, 2)
        self.assertFalse(state.has_products)
        self.assertEqual(state.products, [])
        self.assertFalse(state.products_stale)

    async def test_successful_patch_updates_cached_row_but_failed_patch_does_not(self):
        state = _state()
        state.has_loaded_product = True
        state.original_product = {
            "id": "1", "codigo": "A-1", "nome": "Produto A", "categoria_id": "5",
            "unidade_medida": "UN", "estoque_minimo": "0", "descricao": "",
            "fornecedor_padrao_id": "", "status": "ativo",
        }
        state.codigo = "A-1"
        state.nome = "Produto alterado"
        state.unidade_medida = "UN"
        state.estoque_minimo = "0"
        state.category_selection = "5"
        state.category_options = [{"id": "5", "label": "Categoria A", "disabled": "false"}]
        state.supplier_selection = "none"
        state.original_product_status = "ativo"
        state.current_product_status = "ativo"
        with (
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [_product()]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ),
            patch.object(
                products_module.auth_client,
                "update_product",
                new_callable=AsyncMock,
                return_value={"id": 1, "nome": "Produto alterado"},
            ) as update_product,
        ):
            await self._load_listing(state)
            await _drain(state.update_product())
            self.assertEqual(update_product.await_count, 1)
            await self._load_listing(state)

            state.nome = "Nao deve sobrescrever"
            state.original_product["nome"] = "Produto alterado"
            update_product.side_effect = XanoRequestError(
                "Erro de valida\u00e7\u00e3o", "INVALID_INPUT", 400, {}
            )
            await _drain(state.update_product())
            await self._load_listing(state)

        self.assertEqual(list_products.await_count, 1)
        self.assertEqual(state.products[0]["nome"], "Produto alterado")

    async def test_edit_save_return_flow_uses_five_cold_and_one_warm_call(self):
        state = _state()
        route = patch.object(
            ProductsState,
            "router",
            new_callable=PropertyMock,
            return_value=SimpleNamespace(
                url=SimpleNamespace(path="/produtos/1/editar")
            ),
        )
        with (
            route,
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [_product()]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as list_stock,
            patch.object(
                products_module.auth_client,
                "get_product",
                new_callable=AsyncMock,
                return_value={**_product(), "descricao": "", "fornecedor_padrao_id": None},
            ) as get_product,
            patch.object(
                products_module.auth_client,
                "list_categories",
                new_callable=AsyncMock,
                return_value={"items": [{"id": 5, "nome": "Categoria A", "status": "ativo"}]},
            ) as list_categories,
            patch.object(
                products_module.auth_client,
                "list_suppliers",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as list_suppliers,
            patch.object(
                products_module.auth_client,
                "update_product",
                new_callable=AsyncMock,
                side_effect=lambda _token, _product_id, payload: {
                    "id": 1,
                    "nome": payload.get("nome", "Produto A"),
                },
            ) as update_product,
        ):
            await self._load_listing(state)
            await _drain(state.load_edit_form())
            state.nome = "Produto editado"
            await _drain(state.update_product())
            await self._load_listing(state)

            first_flow_calls = sum(
                mock.await_count
                for mock in (
                    list_products,
                    list_stock,
                    get_product,
                    list_categories,
                    list_suppliers,
                    update_product,
                )
            )
            await _drain(state.load_edit_form())
            state.nome = "Produto atualizado novamente"
            await _drain(state.update_product())
            await self._load_listing(state)

        list_products.assert_awaited_once()
        list_stock.assert_awaited_once()
        get_product.assert_not_awaited()
        list_categories.assert_awaited_once()
        list_suppliers.assert_awaited_once()
        self.assertEqual(update_product.await_count, 2)
        self.assertEqual(state.products[0]["nome"], "Produto atualizado novamente")
        # Cold flow: GET products, GET stock, two reference lists, and PATCH.
        # The fresh list response supplies edit data; the warm repeat needs one PATCH.
        self.assertEqual(first_flow_calls, 5)
        self.assertEqual(
            sum(
                mock.await_count
                for mock in (
                    list_products,
                    list_stock,
                    get_product,
                    list_categories,
                    list_suppliers,
                    update_product,
                )
            ),
            6,
        )

    async def test_uncached_edit_save_return_baseline_uses_eight_http_calls(self):
        """Measure the same mocked navigation without read-cache reuse."""
        state = _state()
        route = patch.object(
            ProductsState,
            "router",
            new_callable=PropertyMock,
            return_value=SimpleNamespace(
                url=SimpleNamespace(path="/produtos/1/editar")
            ),
        )
        with (
            route,
            patch.object(products_module, "_cache_get", return_value=(products_module._CACHE_MISS, False)),
            patch.object(products_module, "_cache_set"),
            patch.object(products_module, "_cached_product_detail", return_value=None),
            patch.object(
                products_module.auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value={"items": [_product()]},
            ) as list_products,
            patch.object(
                products_module.auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as list_stock,
            patch.object(
                products_module.auth_client,
                "get_product",
                new_callable=AsyncMock,
                return_value={**_product(), "descricao": "", "fornecedor_padrao_id": None},
            ) as get_product,
            patch.object(
                products_module.auth_client,
                "list_categories",
                new_callable=AsyncMock,
                return_value={"items": [{"id": 5, "nome": "Categoria A", "status": "ativo"}]},
            ) as list_categories,
            patch.object(
                products_module.auth_client,
                "list_suppliers",
                new_callable=AsyncMock,
                return_value={"items": []},
            ) as list_suppliers,
            patch.object(
                products_module.auth_client,
                "update_product",
                new_callable=AsyncMock,
                return_value={"id": 1, "nome": "Produto editado"},
            ) as update_product,
        ):
            await self._load_listing(state)
            await _drain(state.load_edit_form())
            state.nome = "Produto editado"
            await _drain(state.update_product())
            await self._load_listing(state)

        call_count = sum(
            mock.await_count
            for mock in (
                list_products,
                list_stock,
                get_product,
                list_categories,
                list_suppliers,
                update_product,
            )
        )
        self.assertEqual(call_count, 8)
        self.assertEqual(list_products.await_count, 2)
        self.assertEqual(list_stock.await_count, 2)
        self.assertEqual(get_product.await_count, 1)
        self.assertEqual(list_categories.await_count, 1)
        self.assertEqual(list_suppliers.await_count, 1)
        self.assertEqual(update_product.await_count, 1)


if __name__ == "__main__":
    unittest.main()
