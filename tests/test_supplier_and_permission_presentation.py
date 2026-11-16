from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages import perfis as profiles_module
from Meu_projeto.pages.perfis import PermissionState, _permission_label, _permission_row
from Meu_projeto.pages.fornecedores import _supplier_modal
from Meu_projeto.services.xano_client import XanoAuthClient


class SupplierFormPresentationTests(unittest.IsolatedAsyncioTestCase):
    def test_supplier_modal_keeps_required_fields_and_hides_address(self):
        source = inspect.getsource(_supplier_modal)
        for label in ("Nome / Razão social", "Tipo de documento", "Documento", "Contato (opcional)"):
            self.assertIn(label, source)
        self.assertNotIn("Endereço", source)

    async def test_supplier_update_omits_address_unless_explicitly_requested(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value={}) as request:
            await client.update_supplier(
                "test-token",
                12,
                nome_razao_social="Fornecedor teste",
                tipo_documento="CNPJ",
                documento="12345678000190",
                contato="Contato existente",
            )

        payload = request.await_args.kwargs["json_payload"]
        self.assertEqual(payload["nome_razao_social"], "Fornecedor teste")
        self.assertEqual(payload["tipo_documento"], "CNPJ")
        self.assertEqual(payload["documento"], "12345678000190")
        self.assertEqual(payload["contato"], "Contato existente")
        self.assertNotIn("endereco", payload)
        self.assertNotIn("limpar_endereco", payload)

    async def test_supplier_update_can_clear_address_only_when_explicit(self):
        client = XanoAuthClient()
        with patch.object(client, "_inventory_request", new_callable=AsyncMock, return_value={}) as request:
            await client.update_supplier(
                "test-token",
                12,
                nome_razao_social="Fornecedor teste",
                tipo_documento="CNPJ",
                documento="12345678000190",
                limpar_endereco=True,
            )

        self.assertTrue(request.await_args.kwargs["json_payload"]["limpar_endereco"])


class PermissionPresentationTests(unittest.IsolatedAsyncioTestCase):
    def test_permission_row_displays_label_but_keeps_code_in_toggle_callback(self):
        source = inspect.getsource(_permission_row)
        self.assertIn('item["label"]', source)
        self.assertIn('PermissionState.toggle_permission(item["code"], checked)', source)
        self.assertNotIn('rx.text(item["code"]', source)
        self.assertIn('spacing="2"', source)
        self.assertNotIn('width="100%"', source)
        self.assertNotIn('white_space="nowrap"', source)
        self.assertEqual(_permission_label("product.create", "product", "create"), "Criar produtos")

    def test_permission_state_keeps_technical_codes_for_selection_and_save(self):
        state = object.__new__(PermissionState)
        state._init_bookkeeping()
        state.selected_profile_code = "stockkeeper"
        state.catalog = [
            {"code": "product.read", "resource": "product", "action": "read"},
            {"code": "product.create", "resource": "product", "action": "create"},
        ]
        state.saved_codes = ["product.read"]
        state.draft_codes = ["product.read"]
        state.profile_revisions = {"stockkeeper": 1}
        state.is_saving = False
        state.error_message = ""
        state.success_message = ""
        state.info_message = ""

        state.toggle_permission("product.create", True)

        self.assertEqual(state.draft_codes, ["product.read", "product.create"])
        self.assertEqual(_permission_label("product.read", "product", "read"), "Visualizar produtos")

    async def test_permission_save_sends_selected_technical_codes(self):
        state = object.__new__(PermissionState)
        state._init_bookkeeping()
        state.selected_profile_code = "stockkeeper"
        state.saved_codes = ["product.read"]
        state.draft_codes = ["product.read", "product.create"]
        state.profile_revisions = {"stockkeeper": 1}
        state.profile_grants = {"stockkeeper": ["product.read"]}
        state.is_saving = False
        state.error_message = ""
        state.success_message = ""
        state.info_message = ""
        auth = type("Auth", (), {
            "auth_token": "test-token",
            "session_is_valid": True,
            "is_administrator": True,
            "inventory_profile_id": 1,
        })()
        response = {
            "profiles": [
                {"code": "administrator", "display_name": "Líder"},
                {"code": "stockkeeper", "display_name": "Almoxarife"},
            ],
            "permissions": [
                {"code": "product.read", "resource": "product", "action": "read"},
                {"code": "product.create", "resource": "product", "action": "create"},
            ],
            "permission_matrix": [
                {"profile_code": "administrator", "permissions": [], "permission_revision": 1},
                {"profile_code": "stockkeeper", "permissions": ["product.read", "product.create"], "permission_revision": 2},
            ],
        }

        with patch.object(PermissionState, "get_state", new=AsyncMock(return_value=auth)), patch.object(
            profiles_module.auth_client,
            "update_profile_permissions",
            new=AsyncMock(return_value={
                "profile_code": "stockkeeper",
                "permissions": ["product.read", "product.create"],
                "permission_revision": 2,
            }),
        ) as update, patch.object(
            profiles_module.auth_client,
            "get_permissions",
            new=AsyncMock(return_value=response),
        ):
            async for _event in state.save_permissions():
                pass

        update.assert_awaited_once_with("test-token", "stockkeeper", ["product.read", "product.create"], 1)
        self.assertEqual(state.saved_codes, ["product.read", "product.create"])


if __name__ == "__main__":
    unittest.main()
