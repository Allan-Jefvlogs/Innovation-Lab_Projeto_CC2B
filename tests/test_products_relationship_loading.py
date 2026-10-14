"""Isolated tests for paginated Product relationship selectors."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from Meu_projeto.pages.produtos import ProductsState, auth_client


def _state() -> ProductsState:
    """Build a State shell without starting Reflex runtime or network services."""
    state = object.__new__(ProductsState)
    object.__setattr__(state, "dirty_vars", set())
    defaults = {
        "category_options": [], "category_page": 1, "category_has_more": False,
        "category_loading_more": False, "category_selection": "",
        "category_search_query": "", "category_dropdown_open": False,
        "category_error_message": "", "supplier_options": [], "supplier_page": 1,
        "supplier_has_more": False, "supplier_loading_more": False,
        "supplier_selection": "none", "supplier_search_query": "Sem fornecedor padrão",
        "supplier_dropdown_open": False, "supplier_error_message": "",
        "is_loading": False, "is_saving": False,
        "can_read_products": True, "can_create_products": False,
        "can_update_products": True, "can_activate_products": True,
        "can_inactivate_products": False,
        "has_loaded_product": False, "has_products": False, "products": [],
        "error_message": "", "success_message": "",
        "original_product": {}, "codigo": "", "nome": "", "descricao": "",
        "unidade_medida": "", "estoque_minimo": "", "product_id": 0,
        "original_product_status": "", "current_product_status": "",
    }
    for name, value in defaults.items():
        setattr(state, name, value)

    async def authorized_session():
        state.can_read_products = True
        state.can_update_products = True
        state.can_activate_products = True
        return "fake-token", True

    object.__setattr__(state, "_session", AsyncMock(side_effect=authorized_session))
    return state


def _category(category_id: int, status: str = "ativo") -> dict[str, object]:
    return {"id": category_id, "nome": f"Categoria {category_id}", "status": status}


def _supplier(supplier_id: int) -> dict[str, object]:
    return {
        "id": supplier_id,
        "nome_razao_social": f"Fornecedor {supplier_id}",
        "status": "ativo",
    }


def _page(items: list[dict[str, object]]) -> dict[str, object]:
    return {"items": items, "itemsReceived": len(items)}


class ProductRelationshipPaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_product_without_stock_row_shows_missing_balance(self) -> None:
        state = _state()
        products_response = _page([{
            "id": 501,
            "codigo": "TEST-NO-STOCK",
            "nome": "Produto sem saldo",
            "categoria_id": 1,
            "categoria_nome": "Categoria 1",
            "unidade_medida": "UN",
            "estoque_minimo": 0,
            "status": "ativo",
        }])

        with (
            patch.object(
                auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value=products_response,
            ),
            patch.object(
                auth_client,
                "list_stock",
                new_callable=AsyncMock,
                return_value=_page([]),
            ) as list_stock,
        ):
            async for _ in state.load_products():
                pass

        self.assertEqual(len(state.products), 1)
        self.assertEqual(state.products[0]["quantidade_disponivel"], "—")
        self.assertEqual(state.products[0]["situacao_estoque"], "Saldo não encontrado")
        list_stock.assert_awaited_once_with("fake-token", page=1, per_page=100)

    async def test_stock_pagination_aggregates_pages_and_maps_situations(self) -> None:
        state = _state()
        product_items = [
            {
                "id": product_id,
                "codigo": f"TEST-{product_id}",
                "nome": f"Produto {product_id}",
                "categoria_id": 1,
                "categoria_nome": "Categoria 1",
                "unidade_medida": "UN",
                "estoque_minimo": 5,
                "status": "ativo",
            }
            for product_id in (101, 102, 103, 104)
        ]
        first_stock_page = [
            {
                "product_id": product_id,
                "quantidade_disponivel": 8,
                "estoque_minimo": 5,
                "situacao_estoque": "normal",
            }
            for product_id in range(1, 101)
        ]
        second_stock_page = [
            {
                "product_id": 101,
                "quantidade_disponivel": 0,
                "estoque_minimo": 5,
                "situacao_estoque": "sem_estoque",
            },
            {
                "product_id": 102,
                "quantidade_disponivel": 2,
                "estoque_minimo": 5,
                "situacao_estoque": "abaixo_minimo",
            },
            {
                "product_id": 103,
                "quantidade_disponivel": 8,
                "estoque_minimo": 5,
                "situacao_estoque": "normal",
            },
        ]

        with (
            patch.object(
                auth_client,
                "list_products",
                new_callable=AsyncMock,
                return_value=_page(product_items),
            ),
            patch.object(
                auth_client,
                "list_stock",
                new_callable=AsyncMock,
                side_effect=[_page(first_stock_page), _page(second_stock_page)],
            ) as list_stock,
        ):
            async for _ in state.load_products():
                pass

        self.assertEqual(
            [call.kwargs["page"] for call in list_stock.await_args_list], [1, 2]
        )
        rendered = {product["id"]: product for product in state.products}
        self.assertEqual(rendered["101"]["quantidade_disponivel"], "0")
        self.assertEqual(rendered["101"]["situacao_estoque"], "Sem estoque")
        self.assertEqual(rendered["102"]["quantidade_disponivel"], "2")
        self.assertEqual(rendered["102"]["situacao_estoque"], "Abaixo do mínimo")
        self.assertEqual(rendered["103"]["quantidade_disponivel"], "8")
        self.assertEqual(rendered["103"]["situacao_estoque"], "Normal")
        self.assertEqual(rendered["104"]["quantidade_disponivel"], "—")
        self.assertEqual(rendered["104"]["situacao_estoque"], "Saldo não encontrado")

    async def test_categories_load_next_page_without_duplicate_ids(self) -> None:
        first_page = [_category(value) for value in range(1, 101)]
        second_page = [_category(100), *(_category(value) for value in range(101, 106))]
        state = _state()

        with patch.object(
            auth_client,
            "list_categories",
            new_callable=AsyncMock,
            side_effect=[_page(first_page), _page(second_page)],
        ) as list_categories:
            await state._load_categories("fake-token")
            self.assertEqual(len(state.category_options), 100)
            self.assertTrue(state.category_has_more)

            await state.load_more_categories()

        ids = [option["id"] for option in state.category_options]
        self.assertEqual(len(ids), 105)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(state.category_page, 2)
        self.assertFalse(state.category_has_more)
        self.assertEqual(state.category_options[-1]["id"], "105")
        self.assertEqual(list_categories.await_args_list[1].kwargs["page"], 2)

    async def test_suppliers_load_next_page_without_duplicate_ids(self) -> None:
        first_page = [_supplier(value) for value in range(1, 101)]
        second_page = [_supplier(100), *(_supplier(value) for value in range(101, 106))]
        state = _state()

        with patch.object(
            auth_client,
            "list_suppliers",
            new_callable=AsyncMock,
            side_effect=[_page(first_page), _page(second_page)],
        ) as list_suppliers:
            await state._load_suppliers("fake-token")
            self.assertEqual(len(state.supplier_options), 101)  # includes "none"
            self.assertTrue(state.supplier_has_more)

            await state.load_more_suppliers()

        ids = [option["id"] for option in state.supplier_options]
        relationship_ids = [value for value in ids if value != "none"]
        self.assertEqual(len(relationship_ids), 105)
        self.assertEqual(len(relationship_ids), len(set(relationship_ids)))
        self.assertEqual(state.supplier_page, 2)
        self.assertFalse(state.supplier_has_more)
        self.assertEqual(state.supplier_options[-1]["id"], "105")
        self.assertEqual(list_suppliers.await_args_list[1].kwargs["page"], 2)

    async def test_inactive_category_link_remains_visible_and_is_not_resubmitted(self) -> None:
        product = {
            "id": 42,
            "codigo": "TEST-CATEGORY-42",
            "nome": "Produto de teste",
            "descricao": "",
            "categoria_id": 900,
            "fornecedor_padrao_id": None,
            "unidade_medida": "UN",
            "estoque_minimo": 0,
            "status": "ativo",
        }
        state = _state()
        with (
            patch.object(
                ProductsState,
                "router",
                new_callable=PropertyMock,
                return_value=SimpleNamespace(
                    url=SimpleNamespace(path="/produtos/42/editar")
                ),
            ),
            patch.object(auth_client, "get_product", new_callable=AsyncMock, return_value=product),
            patch.object(
                auth_client,
                "list_categories",
                new_callable=AsyncMock,
                return_value=_page([_category(value) for value in range(1, 5)]),
            ),
            patch.object(
                auth_client,
                "get_category",
                new_callable=AsyncMock,
                return_value=_category(900, status="inativo"),
            ) as get_category,
            patch.object(
                auth_client,
                "list_suppliers",
                new_callable=AsyncMock,
                return_value=_page([_supplier(value) for value in range(1, 4)]),
            ),
            patch.object(auth_client, "update_product", new_callable=AsyncMock) as update_product,
        ):
            async for _ in state.load_edit_form():
                pass

            inactive_option = next(
                option for option in state.category_options if option["id"] == "900"
            )
            self.assertEqual(state.category_selection, "900")
            self.assertEqual(state.original_product["categoria_id"], "900")
            self.assertIn("inativa", inactive_option["label"])
            self.assertEqual(inactive_option["disabled"], "true")
            get_category.assert_awaited_once_with("fake-token", 900)

            # Attempting to select an inactive item cannot replace the selected value.
            state.category_selection = "1"
            state.select_category("900")
            self.assertEqual(state.category_selection, "1")

            # Restore the original link and save an unrelated field. The PATCH omits
            # categoria_id, so loading/editing does not clear or replace the relation.
            state.category_selection = "900"
            state.nome = "Produto de teste editado"
            async for _ in state.update_product():
                pass

        update_product.assert_awaited_once()
        payload = update_product.await_args.args[2]
        self.assertEqual(payload, {"nome": "Produto de teste editado"})
        self.assertNotIn("categoria_id", payload)

        # A new form only receives active Categories; the inactive ID is absent.
        new_form = _state()
        with patch.object(
            auth_client,
            "list_categories",
            new_callable=AsyncMock,
            return_value=_page([_category(value) for value in range(1, 5)]),
        ):
            await new_form._load_categories("fake-token")
        self.assertNotIn("900", {option["id"] for option in new_form.category_options})


if __name__ == "__main__":
    unittest.main()