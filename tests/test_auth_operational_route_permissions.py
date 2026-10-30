"""Mocked Products grant checks; no Xano calls or persisted grant changes."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

from Meu_projeto.pages.movimentacoes import MovementHistoryState
from Meu_projeto.pages.produtos import ProductsState
from Meu_projeto.pages import produtos as products_module
from Meu_projeto.services.xano_client import XanoPermissionError
from Meu_projeto.state.auth import AuthState, _required_route_permission


def _auth_state(
    permissions: list[str], *, profile_id: int = 3, profile_code: str = "read_only"
) -> AuthState:
    state = object.__new__(AuthState)
    object.__setattr__(state, "dirty_vars", set())
    for name, value in {
        "auth_token": "mock-token",
        "user_id": 42,
        "user_name": "Usuário de teste",
        "user_email": "tester@example.invalid",
        "user_role": profile_code,
        "inventory_profile_id": profile_id,
        "inventory_profile_code": profile_code,
        "permission_codes": permissions,
        "profile_name": "Perfil de teste",
        "must_change_password": False,
        "password_change_notice": "",
        "is_authenticated": True,
        "is_loading": False,
        "error_message": "",
        "session_validation": "valid",
        "session_retry_after_epoch": 0.0,
    }.items():
        setattr(state, name, value)
    return state


def _products_state(**values) -> ProductsState:
    products_module._cache_clear()
    state = object.__new__(ProductsState)
    object.__setattr__(state, "dirty_vars", set())
    defaults = {
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
        "has_loaded_product": False,
        "edit_load_failed": False,
        "can_retry_edit_load": False,
        "products_stale": False,
        "products_status_message": "",
        "products_session_fingerprint": "",
        "has_products": False,
        "products": [],
        "error_message": "",
        "success_message": "",
        "category_error_message": "",
        "supplier_error_message": "",
        "category_options": [],
        "supplier_options": [],
        "codigo": "",
        "nome": "",
        "descricao": "",
        "category_selection": "",
        "supplier_selection": "none",
        "unidade_medida": "",
        "estoque_minimo": "",
        "product_id": 8,
        "original_product": {},
        "original_product_status": "",
        "current_product_status": "",
    }
    for name, value in {**defaults, **values}.items():
        setattr(state, name, value)
    return state


class OperationalRoutePermissionTests(unittest.TestCase):
    def test_product_routes_map_to_independent_effective_grants(self) -> None:
        for path, grant in (
            ("/produtos", "product.read"),
            ("/produtos/novo", "product.create"),
            ("/produtos/42/editar", "product.update"),
        ):
            with self.subTest(path=path):
                self.assertEqual(_required_route_permission(path), grant)

    def test_auxiliary_operational_grants_do_not_grant_administrative_access(self) -> None:
        auxiliary = _auth_state(
            ["product.create", "product.update", "stock.entry", "stock.exit"]
        )
        self.assertFalse(auxiliary.is_administrator)
        self.assertFalse(auxiliary.has_permission("administrator"))

        leader = _auth_state([], profile_id=1, profile_code="administrator")
        self.assertTrue(leader.is_administrator)

    def test_history_and_report_routes_use_independent_grants(self) -> None:
        self.assertEqual(_required_route_permission("/movimentacoes"), "movement.read")
        self.assertEqual(_required_route_permission("/relatorios"), "report.read")
        self.assertTrue(_auth_state(["movement.read"]).has_permission("movement.read"))
        self.assertFalse(_auth_state(["report.read"]).has_permission("movement.read"))
        self.assertFalse(_auth_state([]).has_permission("movement.read"))
        self.assertTrue(_auth_state(["report.read"]).has_permission("report.read"))
        self.assertFalse(_auth_state(["movement.read"]).has_permission("report.read"))
        self.assertFalse(_auth_state([]).has_permission("report.read"))

    def test_authenticated_user_without_operational_profile_can_use_dashboard_only(self) -> None:
        user = _auth_state([], profile_id=0, profile_code="")
        user.user_role = "read_only"
        self.assertFalse(user.is_administrator)
        self.assertIsNone(_required_route_permission("/dashboard"))
        self.assertFalse(any(
            user.has_permission(code)
            for code in ("movement.read", "report.read", "stock.read")
        ))

    def test_xano_history_endpoint_contracts_remain_distinct(self) -> None:
        movements_script = Path("xano/api/inventory_stock/movements_get.xs").read_text(encoding="utf-8")
        users_script = Path("xano/api/inventory_stock/movement_users_get.xs").read_text(encoding="utf-8")
        self.assertIn('permission_code: "movement.read"', movements_script)
        self.assertIn('alternate_permission_code: "report.read"', movements_script)
        self.assertIn('permission_code: "movement.read"', users_script)
        self.assertNotIn("alternate_permission_code", users_script)


class CanonicalAdministratorTests(unittest.TestCase):
    def test_administrator_profile_code_grants_administrative_identity(self) -> None:
        state = _auth_state([], profile_id=7, profile_code="administrator")
        self.assertTrue(state.is_administrator)
        self.assertTrue(state.has_permission("administrator"))

    def test_profile_id_one_does_not_override_non_admin_profile_code(self) -> None:
        state = _auth_state(["stock.read"], profile_id=1, profile_code="stockkeeper")
        self.assertFalse(state.is_administrator)
        self.assertFalse(state.has_permission("administrator"))
        self.assertTrue(state.has_permission("stock.read"))

    def test_legacy_admin_role_does_not_override_non_admin_profile_code(self) -> None:
        state = _auth_state([], profile_id=2, profile_code="stockkeeper")
        state.user_role = "administrator"
        self.assertFalse(state.is_administrator)
        self.assertFalse(state.has_permission("administrator"))

    def test_missing_profile_code_does_not_grant_administrator_access(self) -> None:
        state = _auth_state([], profile_id=1, profile_code="")
        state.user_role = "administrator"
        self.assertFalse(state.is_administrator)
        self.assertFalse(state.has_permission("administrator"))

    def test_operational_grants_are_independent_of_administrator_identity(self) -> None:
        state = _auth_state(
            ["stock.entry", "stock.exit"], profile_id=3, profile_code="auxiliary"
        )
        self.assertFalse(state.is_administrator)
        self.assertTrue(state.has_permission("stock.entry"))
        self.assertTrue(state.has_permission("stock.exit"))
        self.assertFalse(state.has_permission("user.manage"))

    def test_populate_user_restores_canonical_profile_code(self) -> None:
        state = _auth_state([])
        state._populate_user(
            {
                "id": 1,
                "name": "Admin",
                "email": "admin@example.invalid",
                "role": "legacy_role",
                "inventory_profile_id": 9,
                "inventory_profile_code": "administrator",
                "permission_codes": [],
            }
        )
        self.assertEqual(state.inventory_profile_code, "administrator")
        self.assertTrue(state.is_administrator)


class HistoryPermissionMockTests(unittest.IsolatedAsyncioTestCase):
    async def test_movement_users_permission_denial_is_handled_without_exposing_users(self) -> None:
        state = object.__new__(MovementHistoryState)
        object.__setattr__(state, "dirty_vars", set())
        state.user_filter_error = ""
        state.user_options = []
        state.user_page = 1
        state.user_has_more = False
        object.__setattr__(state, "_session_token", AsyncMock(return_value="mock-token"))
        with (
            patch("Meu_projeto.pages.movimentacoes._log_history_failure"),
            patch(
                "Meu_projeto.pages.movimentacoes.auth_client.list_movement_users",
                new_callable=AsyncMock,
                side_effect=XanoPermissionError("PERMISSION_DENIED"),
            ) as list_users,
        ):
            await MovementHistoryState.load_users.fn(state)

        list_users.assert_awaited_once_with("mock-token", page=1, per_page=100)
        self.assertTrue(state.user_filter_error)
        self.assertEqual(state.user_options[0]["id"], "")


class ProductActionGrantTests(unittest.IsolatedAsyncioTestCase):
    async def _load_list(self, permissions: list[str], *, profile_id: int = 3, code: str = "read_only"):
        state = _products_state()
        auth = _auth_state(permissions, profile_id=profile_id, profile_code=code)
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.list_products", new_callable=AsyncMock, return_value={"items": []}),
            patch("Meu_projeto.pages.produtos.auth_client.list_stock", new_callable=AsyncMock, return_value={"items": []}),
        ):
            async for _event in state.load_products():
                pass
        return state

    async def test_auxiliary_create_and_update_grants_are_independent_and_hide_missing_actions(self):
        create_only = await self._load_list(["product.read", "product.create"])
        self.assertTrue(create_only.can_create_products)
        self.assertFalse(create_only.can_update_products)

        update_only = await self._load_list(["product.read", "product.update"])
        self.assertFalse(update_only.can_create_products)
        self.assertTrue(update_only.can_update_products)

        neither = await self._load_list(["product.read"])
        self.assertFalse(neither.can_create_products)
        self.assertFalse(neither.can_update_products)

    async def test_administrator_and_stockkeeper_effective_grants_still_work(self):
        leader = await self._load_list([], profile_id=1, code="administrator")
        self.assertTrue(leader.can_read_products)
        self.assertTrue(leader.can_create_products)
        self.assertTrue(leader.can_update_products)

        stockkeeper = await self._load_list(
            ["product.read", "product.create", "product.update"], profile_id=2, code="stockkeeper"
        )
        self.assertTrue(stockkeeper.can_create_products)
        self.assertTrue(stockkeeper.can_update_products)

    async def test_auxiliary_with_create_grant_can_load_and_submit_create_form(self):
        auth = _auth_state(["product.create"])
        state = _products_state()
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(ProductsState, "_load_categories", new_callable=AsyncMock) as load_categories,
            patch.object(ProductsState, "_load_suppliers", new_callable=AsyncMock) as load_suppliers,
        ):
            async for _event in state.load_create_form():
                pass
        self.assertTrue(state.can_create_products)
        load_categories.assert_awaited_once_with("mock-token")
        load_suppliers.assert_awaited_once_with("mock-token")

        state.codigo = "TESTE"
        state.nome = "Produto teste"
        state.category_selection = "5"
        state.unidade_medida = "UN"
        state.estoque_minimo = "0"
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.create_product", new_callable=AsyncMock) as create_product,
        ):
            async for _event in state.create_product():
                pass
        create_product.assert_awaited_once()

    async def test_auxiliary_without_create_grant_is_blocked_on_direct_loader_and_event(self):
        auth = _auth_state(["product.read"])
        state = _products_state()
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(ProductsState, "_load_categories", new_callable=AsyncMock) as load_categories,
            patch.object(ProductsState, "_load_suppliers", new_callable=AsyncMock) as load_suppliers,
        ):
            async for _event in state.load_create_form():
                pass
        self.assertFalse(state.can_create_products)
        self.assertIn("não tem permissão", state.error_message)
        load_categories.assert_not_awaited()
        load_suppliers.assert_not_awaited()

        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.create_product", new_callable=AsyncMock) as create_product,
        ):
            async for _event in state.create_product():
                pass
        create_product.assert_not_awaited()

    async def test_auxiliary_without_update_grant_is_blocked_on_direct_loader_and_event(self):
        auth = _auth_state(["product.read"])
        state = _products_state(has_loaded_product=True)
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.get_product", new_callable=AsyncMock) as get_product,
        ):
            async for _event in state.load_edit_form():
                pass
        self.assertFalse(state.has_loaded_product)
        self.assertFalse(state.can_update_products)
        self.assertIn("não tem permissão", state.error_message)
        get_product.assert_not_awaited()

        state.has_loaded_product = True
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.update_product", new_callable=AsyncMock) as update_product,
        ):
            async for _event in state.update_product():
                pass
        self.assertIn("não tem permissão", state.error_message)
        update_product.assert_not_awaited()

    async def test_auxiliary_with_update_grant_can_submit_edit_without_create_grant(self):
        auth = _auth_state(["product.update"])
        state = _products_state(
            has_loaded_product=True,
            product_id=8,
            codigo="A",
            nome="Produto A",
            category_selection="5",
            unidade_medida="UN",
            estoque_minimo="0",
            original_product={
                "codigo": "A", "nome": "Produto antigo", "categoria_id": "5",
                "unidade_medida": "UN", "estoque_minimo": "0", "descricao": "",
                "fornecedor_padrao_id": "",
            },
        )
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.update_product", new_callable=AsyncMock) as update_product,
        ):
            async for _event in state.update_product():
                pass
        update_product.assert_awaited_once_with("mock-token", 8, {"nome": "Produto A"})

    async def test_auxiliary_with_update_grant_can_load_direct_edit_route(self):
        auth = _auth_state(["product.read", "product.update"])
        state = _products_state()
        product = {
            "id": 8,
            "codigo": "A",
            "nome": "Produto A",
            "descricao": "",
            "categoria_id": 5,
            "fornecedor_padrao_id": None,
            "unidade_medida": "UN",
            "estoque_minimo": 0,
            "status": "ativo",
        }
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch.object(
                ProductsState,
                "router",
                new_callable=PropertyMock,
                return_value=SimpleNamespace(url=SimpleNamespace(path="/produtos/8/editar")),
            ),
            patch("Meu_projeto.pages.produtos.auth_client.get_product", new_callable=AsyncMock, return_value=product),
            patch("Meu_projeto.pages.produtos.auth_client.list_categories", new_callable=AsyncMock, return_value={"items": [{"id": 5, "nome": "Categoria", "status": "ativo"}]}),
            patch("Meu_projeto.pages.produtos.auth_client.list_suppliers", new_callable=AsyncMock, return_value={"items": []}),
        ):
            async for _event in state.load_edit_form():
                pass

        self.assertTrue(state.can_update_products)
        self.assertTrue(state.has_loaded_product)
        self.assertEqual(state.product_id, 8)

    async def test_create_and_edit_route_guards_require_their_own_grants(self):
        self.assertEqual(_required_route_permission("/produtos/novo"), "product.create")
        self.assertEqual(_required_route_permission("/produtos/8/editar"), "product.update")
        self.assertTrue(_auth_state(["product.create"]).has_permission("product.create"))
        self.assertFalse(_auth_state(["product.create"]).has_permission("product.update"))
        self.assertTrue(_auth_state(["product.update"]).has_permission("product.update"))
        self.assertFalse(_auth_state(["product.update"]).has_permission("product.create"))


class ProductStatusGrantTests(unittest.IsolatedAsyncioTestCase):
    async def test_product_update_does_not_grant_inactivation(self):
        auth = _auth_state(["product.update"])
        state = _products_state(
            has_loaded_product=True,
            original_product_status="ativo",
            current_product_status="ativo",
        )
        with patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.change_product_status()
        self.assertEqual(state.current_product_status, "ativo")
        self.assertIn("não tem permissão para inativar", state.error_message)

    async def test_active_status_can_be_marked_inactive_with_inactivate_grant_but_not_persisted_yet(self):
        auth = _auth_state(["product.inactivate"])
        state = _products_state(
            has_loaded_product=True,
            original_product_status="ativo",
            current_product_status="ativo",
        )
        with patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.change_product_status()
        self.assertEqual(state.current_product_status, "inativo")
        self.assertTrue(state.can_change_product_status)

    async def test_inactive_product_can_be_activated_with_product_update(self):
        auth = _auth_state(["product.update"])
        state = _products_state(
            has_loaded_product=True,
            original_product_status="inativo",
            current_product_status="inativo",
        )
        with patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth):
            await state.change_product_status()
        self.assertEqual(state.current_product_status, "ativo")
        self.assertTrue(state.can_change_product_status)

    async def test_inactivation_is_rejected_before_any_cadastral_patch_without_inactivate_grant(self):
        auth = _auth_state(["product.update"])
        state = _products_state(
            has_loaded_product=True,
            original_product_status="ativo",
            current_product_status="inativo",
            codigo="A",
            nome="Produto A",
            category_selection="5",
            unidade_medida="UN",
            estoque_minimo="0",
            original_product={
                "codigo": "A", "nome": "Produto A", "categoria_id": "5",
                "unidade_medida": "UN", "estoque_minimo": "0", "descricao": "",
            },
        )
        with (
            patch.object(ProductsState, "get_state", new_callable=AsyncMock, return_value=auth),
            patch("Meu_projeto.pages.produtos.auth_client.update_product", new_callable=AsyncMock) as update_product,
            patch("Meu_projeto.pages.produtos.auth_client.inactivate_product", new_callable=AsyncMock) as inactivate_product,
        ):
            async for _event in state.update_product():
                pass
        self.assertIn("não tem permissão para inativar", state.error_message)
        update_product.assert_not_awaited()
        inactivate_product.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
