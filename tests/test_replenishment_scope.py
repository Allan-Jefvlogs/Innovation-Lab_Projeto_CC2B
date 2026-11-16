"""Local structural and mocked checks; these do not execute XanoScript."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages.reposicao import ReplenishmentState, _map_item, _requested_content
from Meu_projeto.services.session_read_cache import CACHE_MISS, SessionReadCache, session_read_cache
from Meu_projeto.services.xano_client import XanoAuthClient, XanoServerError


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_FIELDS = (
    "solicitacao_id", "quantidade_solicitada", "urgencia",
    "solicitacao_status", "data_criacao_solicitacao",
)


def requested_item(*, restricted: bool = False, legacy: bool = False):
    item = {
        "produto_id": 41,
        "codigo": "TEST-41",
        "nome": "Produto de teste local",
        "unidade_medida": "KG",
        "quantidade_disponivel": 0,
        "estoque_minimo": 10,
        "situacao_estoque": "sem_estoque",
        "solicitacao_id": 81,
        "quantidade_solicitada": 10,
        "urgencia": "alta",
        "solicitacao_status": "aberta",
        "data_criacao_solicitacao": 1790000000000,
    }
    if not legacy:
        item["solicitacao_detalhes_disponiveis"] = not restricted
    if restricted:
        item.update({field: None for field in PRIVATE_FIELDS})
    return item


def response(item):
    return {
        "a_solicitar": {"items": [], "curPage": 1, "perPage": 10, "itemsTotal": 0},
        "compra_ja_solicitada": {
            "items": [item], "curPage": 2, "perPage": 10, "itemsTotal": 23,
        },
    }


class ReplenishmentBackendScopeStructureTests(unittest.TestCase):
    def test_read_authorization_precedes_scope_and_retains_admin_manage_policy(self):
        xs = (ROOT / "xano/api/inventory_stock/stock_replenishment_get.xs").read_text(encoding="utf-8")
        helper = (ROOT / "xano/function/inventory/purchase_request_notification_all_access.xs").read_text(encoding="utf-8")
        self.assertLess(
            xs.index('permission_code: "purchase_request.read"'),
            xs.index('function.run "Inventory/purchase_request_notification_all_access"'),
        )
        self.assertIn('permission_code: "stock.read"', xs)
        self.assertIn('$profile.code == "administrator"', helper)
        self.assertIn('field_value = "purchase_request.manage"', helper)
        self.assertIn("$db.inventory_profile_permission.profile_id == $profile.id", helper)
        self.assertIn("$db.inventory_profile_permission.permission_id == $manage_permission.id", helper)

    def test_only_owner_or_global_scope_can_fill_public_request_details(self):
        xs = (ROOT / "xano/api/inventory_stock/stock_replenishment_get.xs").read_text(encoding="utf-8")
        loop = xs.split("foreach ($requested_page.items)", 1)[1]
        defaults, guarded = loop.split("if ($can_view_request_details)", 1)
        self.assertIn("$scope.all_access || $item.solicitante_usuario_id == $auth.id", defaults)
        for field in PRIVATE_FIELDS:
            self.assertIn(f"{field}: null", defaults)
        self.assertIn("var.update $request_details", guarded)
        public = guarded.split("array.push $requested_items", 1)[1]
        self.assertIn("solicitacao_detalhes_disponiveis: $can_view_request_details", public)
        for field in PRIVATE_FIELDS:
            self.assertIn(f"{field}: $request_details.{field}", public)
            self.assertNotIn(f"{field}: $item.", public)
        self.assertNotIn("solicitante_usuario_id:", public)

    def test_stock_lists_totals_and_query_count_are_preserved(self):
        xs = (ROOT / "xano/api/inventory_stock/stock_replenishment_get.xs").read_text(encoding="utf-8")
        self.assertEqual(xs.count("db.query "), 3)
        self.assertIn("$db.active_request.id == null", xs)
        self.assertIn("$db.active_request.id != null", xs)
        self.assertIn("itemsTotal: $eligible_page.itemsTotal", xs)
        self.assertIn("itemsTotal: $requested_page.itemsTotal", xs)
        self.assertIn('error = "STOCK_BALANCE_NOT_FOUND"', xs)
        for loop in xs.split("foreach (")[1:]:
            self.assertNotIn("db.query ", loop.split("\n  response =", 1)[0])
        self.assertNotIn("db.edit", xs)
        self.assertNotIn("db.direct_query", xs)


class ReplenishmentVisibilityConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_loading_preserves_stock_guard_and_separates_read_scope(self):
        cases = (
            ("stockkeeper", {"stock.read", "purchase_request.read"}, False, True, False),
            ("stockkeeper", {"stock.read", "purchase_request.read"}, False, True, True),
            ("stockkeeper", {"stock.read", "purchase_request.read", "purchase_request.manage"}, True, True, False),
            ("administrator", set(), True, True, False),
            ("compras", {"purchase_request.read", "purchase_request.manage", "purchase_request.status.update"}, True, False, False),
        )
        for profile, grants, global_access, allowed, owned in cases:
            with self.subTest(profile=profile, global_access=global_access, owned=owned):
                session_read_cache.clear()
                state = object.__new__(ReplenishmentState)
                state._init_bookkeeping()
                state.is_loading = False
                state.session_fingerprint_cache = ""
                state.requestable_page = state.requested_page = 1
                state.page_size = 10
                auth = SimpleNamespace(
                    auth_token="local-profile-token", session_is_valid=True,
                    require_auth=AsyncMock(return_value=None),
                    has_permission=lambda code: profile == "administrator" or code in grants,
                )
                details_available = global_access or owned
                payload = response(requested_item(restricted=not details_available))
                with patch.object(ReplenishmentState, "get_state", new=AsyncMock(return_value=auth)), patch(
                    "Meu_projeto.pages.reposicao.auth_client.list_stock_replenishment",
                    new=AsyncMock(return_value=payload),
                ) as get:
                    _ = [event async for event in state._load_data()]
                self.assertEqual(get.await_count, 1 if allowed else 0)
                if allowed:
                    self.assertEqual(state.read_visibility_scope, "global" if global_access else "own")
                    self.assertEqual(state.requested_products[0]["detalhes_disponiveis"], "true" if details_available else "false")
                else:
                    self.assertEqual(state.requested_status, "access_denied")
                    self.assertEqual(state.requested_products, [])
        session_read_cache.clear()

    def test_cache_separates_own_global_and_legacy_visibility_without_changing_ttl(self):
        state = object.__new__(ReplenishmentState)
        state._init_bookkeeping()
        state.requestable_page = state.requested_page = 1
        state.page_size = 10
        cache = SessionReadCache()
        global_key = state._cache_key("same-local-token", global_access=True)
        own_key = state._cache_key("same-local-token", global_access=False)
        legacy_key = (own_key[0].split(":visibility-v2:", 1)[0], *own_key[1:])
        self.assertNotEqual(global_key, own_key)
        self.assertNotEqual(legacy_key, own_key)
        cache.set(global_key, response(requested_item()), 60)
        cache.set(legacy_key, response(requested_item()), 60)
        self.assertIs(cache.get(own_key, 60, allow_stale=True)[0], CACHE_MISS)
        self.assertTrue(cache.get(global_key, 60)[1])
        cache.invalidate(endpoint=global_key[1], token="same-local-token")
        self.assertIs(cache.get(global_key, 60)[0], CACHE_MISS)

    def test_permission_scope_change_discards_visible_rows_but_preserves_ambiguous_write_key(self):
        state = object.__new__(ReplenishmentState)
        state._init_bookkeeping()
        state.read_visibility_scope = "global"
        state.requested_products = [_map_item(requested_item(), requested=True)]
        state.requestable_products = []
        state.requestable_total = 0
        state.requested_total = 23
        state.data_stale = True
        state.cancel_form_open = True
        state.request_attempt_key = "same-logical-attempt"
        state.request_attempt_ambiguous = True
        state._set_read_visibility_scope(False)
        self.assertEqual(state.requested_products, [])
        self.assertEqual(state.requested_total, 0)
        self.assertFalse(state.data_stale)
        self.assertFalse(state.cancel_form_open)
        self.assertEqual(state.request_attempt_key, "same-logical-attempt")
        self.assertTrue(state.request_attempt_ambiguous)

    async def test_legacy_own_and_authorized_global_details_remain_compatible(self):
        client = XanoAuthClient()
        for label, item in (
            ("legacy", requested_item(legacy=True)),
            ("owner", requested_item()),
            ("read_and_manage", requested_item()),
            ("administrator", requested_item()),
        ):
            with self.subTest(visibility=label):
                payload = response(item)
                with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)) as get:
                    result = await client.list_stock_replenishment("local-token")
                row = _map_item(result["compra_ja_solicitada"]["items"][0], requested=True)
                self.assertEqual(row["solicitacao_id"], "81")
                self.assertEqual(row["status"], "aberta")
                self.assertEqual(row["detalhes_disponiveis"], "true")
                get.assert_awaited_once()

    async def test_foreign_request_keeps_stock_and_independent_totals_without_details(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new=AsyncMock(return_value=response(requested_item(restricted=True)))):
            result = await client.list_stock_replenishment("local-token", requested_page=2)
        page = result["compra_ja_solicitada"]
        self.assertEqual((page["curPage"], page["perPage"], page["itemsTotal"]), (2, 10, 23))
        self.assertEqual(result["a_solicitar"]["itemsTotal"], 0)
        row = _map_item(page["items"][0], requested=True)
        self.assertEqual((row["id"], row["codigo"], row["situacao"]), ("41", "TEST-41", "sem_estoque"))
        self.assertEqual(row["solicitacao_id"], "")
        self.assertEqual(row["status"], "Detalhes restritos")
        for field in ("quantidade_solicitada", "urgencia", "data_solicitacao"):
            self.assertEqual(row[field], "—")

    async def test_restricted_payload_with_private_values_is_rejected_without_logging_values(self):
        client = XanoAuthClient()
        for field in (*PRIVATE_FIELDS, "urgencia_solicitacao"):
            with self.subTest(field=field):
                item = requested_item(restricted=True)
                item[field] = "private-test-value"
                with patch.object(client, "_inventory_request", new=AsyncMock(return_value=response(item))):
                    with self.assertRaises(XanoServerError) as caught:
                        await client.list_stock_replenishment("local-token")
                self.assertEqual(caught.exception.contract_field, field)
                self.assertNotIn("private-test-value", str(caught.exception))

    async def test_visibility_flag_is_strictly_boolean(self):
        client = XanoAuthClient()
        for invalid in (None, "false", 0, 1, [], {}):
            with self.subTest(type=type(invalid).__name__):
                item = requested_item(restricted=True)
                item["solicitacao_detalhes_disponiveis"] = invalid
                with patch.object(client, "_inventory_request", new=AsyncMock(return_value=response(item))):
                    with self.assertRaises(XanoServerError) as caught:
                        await client.list_stock_replenishment("local-token")
                self.assertEqual(caught.exception.contract_field, "solicitacao_detalhes_disponiveis")

    async def test_restricted_row_cannot_open_cancel_even_with_cancel_grant(self):
        state = object.__new__(ReplenishmentState)
        state._init_bookkeeping()
        state.cancel_form_open = False
        state.cancel_attempt_ambiguous = False
        state.cancel_request_id = ""
        state.requested_products = [_map_item(requested_item(restricted=True), requested=True)]
        auth = SimpleNamespace(session_is_valid=True, has_permission=lambda _: True)
        with patch.object(ReplenishmentState, "get_state", new=AsyncMock(return_value=auth)):
            await state.open_cancel_request_form("81")
        self.assertFalse(state.cancel_form_open)
        self.assertIn('row["detalhes_disponiveis"] == "true"', inspect.getsource(_requested_content))


if __name__ == "__main__":
    unittest.main()
