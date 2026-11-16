from __future__ import annotations

import inspect
import unittest

from Meu_projeto.components.operation_feedback import success_dialog
from Meu_projeto.pages.compras import _justification_dialog, compra_detalhe
from Meu_projeto.pages.fornecedores import _supplier_modal
from Meu_projeto.pages.movimentacoes import entrada, saida
from Meu_projeto.pages.produtos import _form_fields, _product_form
from Meu_projeto.pages.produtos import _status_action, editar_produto, novo_produto
from Meu_projeto.pages.reposicao import _cancel_form
from Meu_projeto.pages.usuarios import _user_modal


class OperationFeedbackPresentationTests(unittest.TestCase):
    def test_success_dialog_has_success_icon_accessible_close_and_responsive_width(self):
        source = inspect.getsource(success_dialog)
        self.assertIn('tag="circle-check"', source)
        self.assertIn('"Fechar"', source)
        self.assertIn("on_open_change(False)", source)
        self.assertIn('max_width="min(440px, calc(100vw - 32px))"', source)

    def test_product_form_uses_two_columns_only_above_mobile_breakpoint(self):
        source = inspect.getsource(_form_fields)
        self.assertIn('"0px": "minmax(0, 1fr)"', source)
        self.assertIn('"760px": "repeat(2, minmax(0, 1fr))"', source)
        self.assertIn('grid_column="1 / -1"', source)

    def test_supplier_and_user_forms_are_wide_and_responsive(self):
        supplier = inspect.getsource(_supplier_modal)
        user = inspect.getsource(_user_modal)
        self.assertIn('max_width="min(42rem, calc(100vw - 32px))"', supplier)
        self.assertIn('"640px": "10rem minmax(0, 1fr)"', supplier)
        self.assertIn('"640px": "22rem"', supplier)
        self.assertIn('"640px": "20rem"', supplier)
        self.assertIn('height="38px"', supplier)
        self.assertIn('max_width="min(42rem, calc(100vw - 32px))"', user)
        self.assertIn('"700px": "repeat(2, minmax(0, 1fr))"', user)
        self.assertIn('grid_column="1 / -1"', user)
        self.assertIn('"700px": "22rem"', user)
        self.assertIn('height="38px"', user)

    def test_purchase_cancellation_dialog_is_compact_and_sensitive(self):
        for source in (inspect.getsource(_cancel_form), inspect.getsource(_justification_dialog)):
            self.assertIn('"Cancelar solicitação"', source)
            self.assertIn('"Motivo do cancelamento"', source)
            self.assertIn('"Descreva brevemente o motivo..."', source)
            self.assertIn('min_height="72px"', source)
            self.assertIn('max_width="min(32rem, calc(100vw - 32px))"', source)
            self.assertIn('color=ERROR_TEXT', source)
            self.assertIn('variant="soft"', source)

        replenishment = inspect.getsource(_cancel_form)
        purchases = inspect.getsource(_justification_dialog)
        self.assertIn("ReplenishmentState.cancel_product_label", replenishment)
        self.assertIn('PurchaseManagementState.product_data["codigo"]', purchases)
        self.assertIn('PurchaseManagementState.product_data["nome"]', purchases)
        self.assertIn("PurchaseManagementState.confirm_justification", purchases)
        self.assertIn("ReplenishmentState.confirm_cancel_request", replenishment)

    def test_product_status_action_is_compact_and_keeps_confirmation(self):
        source = inspect.getsource(_status_action)
        page_source = inspect.getsource(editar_produto)
        purchase_detail = inspect.getsource(compra_detalhe)
        self.assertIn('width="fit-content"', source)
        self.assertIn('variant="outline"', source)
        self.assertIn("rx.spacer()", page_source)
        self.assertIn("ProductsState.change_product_status", source)
        self.assertIn('width="fit-content"', purchase_detail)
        self.assertIn('width="100%", align="center", spacing="3", wrap="wrap"', purchase_detail)

    def test_product_form_cards_are_constrained_and_actions_compact(self):
        create = inspect.getsource(novo_produto)
        edit = inspect.getsource(editar_produto)
        form = inspect.getsource(_product_form)
        self.assertIn('max_width="60rem"', create)
        self.assertIn('max_width="60rem"', edit)
        self.assertIn('max_width="58rem"', form)
        self.assertIn('justify="end"', form)
        self.assertIn('size="2"', form)

    def test_entry_and_exit_forms_use_responsive_compact_grids_without_removing_fields(self):
        entry = inspect.getsource(entrada)
        exit_page = inspect.getsource(saida)
        for source in (entry, exit_page):
            self.assertIn('"0px": "minmax(0, 1fr)"', source)
            self.assertIn('"760px": "repeat(2, minmax(0, 1fr))"', source)
            self.assertIn('max_width="54rem"', source)
            self.assertIn('grid_column="1 / -1"', source)
            self.assertIn('"Código do produto"', source)
            self.assertIn('"Produto"', source)
            self.assertIn('"Quantidade"', source)
            self.assertIn('"Data e hora (opcional)"', source)
            self.assertIn('"Motivo"', source)
            self.assertIn('"Observação"', source)
            self.assertIn('on_click=', source)
        self.assertIn("EntryState.load_receipt_orders(False)", entry)
        self.assertIn('placeholder="Entrada avulsa"', entry)
        self.assertIn("EntryState.register_entry", entry)
        self.assertIn("ExitState.has_available_stock", exit_page)
        self.assertIn("ExitState.register_exit", exit_page)


if __name__ == "__main__":
    unittest.main()
