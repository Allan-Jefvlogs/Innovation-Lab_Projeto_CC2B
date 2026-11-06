"""Cobertura local do alerta por e-mail de estoque abaixo do mínimo.

enviar_email e create_stock_exit são substituídos por mocks. Nenhuma chamada
real ao Xano ou ao Resend é feita por estes testes.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from Meu_projeto.pages.movimentacoes import ExitState
from Meu_projeto.services.email_service import EmailEnvioError
from Meu_projeto.services.stock_alert import (
    STATUS_ENVIADO,
    STATUS_FALHOU,
    STATUS_NAO_APLICAVEL,
    STATUS_SEM_DESTINATARIO,
    deve_alertar,
    enviar_alerta_estoque_minimo,
    montar_alerta,
)



SEND_PATH = "Meu_projeto.services.stock_alert.enviar_email"


def _context(**overrides) -> dict:
    context = {
        "destinatario": "almoxarife@exemplo.com",
        "movement_id": 42,
        "codigo": "P-001",
        "nome": "Parafuso",
        "saldo_atual": "8",
        "estoque_minimo": "10",
        "quantidade": "4",
        "usuario": "Almoxarife Teste",
        "data_hora": "2026-11-04T10:00:00",
    }
    context.update(overrides)
    return context


class DeveAlertarTest(unittest.TestCase):
    def test_regra(self):
        casos = [
            ("8", "10", True),
            ("6", "10", True),
            ("0", "10", True),
            ("9.99", "10.00", True),
            ("10", "10", False),
            ("12", "10", False),
            ("0", "0", False),
            (None, "10", False),
            ("8", None, False),
            ("abc", "10", False),
            ("8", "", False),
            ("NaN", "10", False),
        ]
        for saldo, minimo, esperado in casos:
            with self.subTest(saldo=saldo, minimo=minimo):
                self.assertEqual(deve_alertar(saldo, minimo), esperado)


class MontarAlertaTest(unittest.TestCase):
    def test_assunto_abaixo_do_minimo(self):
        assunto, html, texto = montar_alerta(**{k: v for k, v in _context().items() if k not in {"destinatario", "movement_id"}})
        self.assertEqual(assunto, "[NexStock] Estoque abaixo do mínimo: P-001 - Parafuso")
        self.assertIn("Saldo atual: 8", texto)
        self.assertIn("Estoque mínimo: 10", texto)
        self.assertIn("Almoxarife Teste", html)

    def test_assunto_sem_estoque(self):
        assunto, _, _ = montar_alerta(**{k: v for k, v in _context(saldo_atual="0.000").items() if k not in {"destinatario", "movement_id"}})
        self.assertEqual(assunto, "[NexStock] Sem estoque: P-001 - Parafuso")

    def test_html_escapa_dados_do_produto(self):
        _, html, _ = montar_alerta(**{k: v for k, v in _context(nome="<script>x</script>").items() if k not in {"destinatario", "movement_id"}})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_quantidade_decimal_formatada(self):
        _, _, texto = montar_alerta(**{k: v for k, v in _context(saldo_atual="8.50").items() if k not in {"destinatario", "movement_id"}})
        self.assertIn("Saldo atual: 8,50", texto)


class EnviarAlertaTest(unittest.IsolatedAsyncioTestCase):
    async def test_envia_ao_usuario_logado_com_idempotencia(self):
        with patch(SEND_PATH, new_callable=AsyncMock, return_value="msg-1") as send:
            status = await enviar_alerta_estoque_minimo(**_context())
        self.assertEqual(status, STATUS_ENVIADO)
        kwargs = send.await_args.kwargs
        self.assertEqual(kwargs["para"], "almoxarife@exemplo.com")
        self.assertEqual(kwargs["chave_idempotencia"], "alerta-estoque-42")
        self.assertIn("P-001", kwargs["assunto"])

    async def test_produto_ja_abaixo_do_minimo_gera_novo_alerta(self):
        with patch(SEND_PATH, new_callable=AsyncMock, return_value="msg-1") as send:
            status = await enviar_alerta_estoque_minimo(**_context(saldo_atual="6"))
        self.assertEqual(status, STATUS_ENVIADO)
        send.assert_awaited_once()

    async def test_saldo_no_minimo_nao_envia(self):
        with patch(SEND_PATH, new_callable=AsyncMock) as send:
            status = await enviar_alerta_estoque_minimo(**_context(saldo_atual="10"))
        self.assertEqual(status, STATUS_NAO_APLICAVEL)
        send.assert_not_awaited()

    async def test_dados_invalidos_nao_envia(self):
        with patch(SEND_PATH, new_callable=AsyncMock) as send:
            status = await enviar_alerta_estoque_minimo(**_context(estoque_minimo=None))
        self.assertEqual(status, STATUS_NAO_APLICAVEL)
        send.assert_not_awaited()

    async def test_usuario_sem_email_nao_envia(self):
        with patch(SEND_PATH, new_callable=AsyncMock) as send:
            status = await enviar_alerta_estoque_minimo(**_context(destinatario="  "))
        self.assertEqual(status, STATUS_SEM_DESTINATARIO)
        send.assert_not_awaited()

    async def test_falha_de_envio(self):
        erro = EmailEnvioError("EMAIL_PROVIDER_REJECTED", "recusado", status_code=403)
        with patch(SEND_PATH, new_callable=AsyncMock, side_effect=erro):
            status = await enviar_alerta_estoque_minimo(**_context())
        self.assertEqual(status, STATUS_FALHOU)

    async def test_sem_movement_id_envia_sem_chave(self):
        with patch(SEND_PATH, new_callable=AsyncMock, return_value="msg-1") as send:
            await enviar_alerta_estoque_minimo(**_context(movement_id=None))
        self.assertIsNone(send.await_args.kwargs["chave_idempotencia"])


def _auth_state() -> SimpleNamespace:
    return SimpleNamespace(
        auth_token="test-token-not-real",
        user_name="Almoxarife Teste",
        user_email="almoxarife@exemplo.com",
        session_is_valid=True,
        session_validation="valid",
        session_status_message="",
        has_permission=lambda code: code == "stock.exit",
    )


def _exit_state(auth_state: SimpleNamespace, *, saldo: str = "12", minimo: str = "10") -> ExitState:
    state = object.__new__(ExitState)
    object.__setattr__(state, "dirty_vars", set())
    for name, value in {
        "is_submitting": False,
        "error_message": "",
        "success_message": "",
        "alert_message": "",
        "alert_error": "",
        "product_id": "5",
        "product_code": "P-001",
        "product_name": "Parafuso",
        "product_query": "P-001 - Parafuso",
        "barcode_value": "P-001",
        "product_options_open": False,
        "quantidade": "4",
        "motivo": "Consumo",
        "observacao": "",
        "exit_date_time": "",
        "saldo_disponivel": saldo,
        "stock_balance_found": True,
        "has_available_stock": True,
        "product_error": "",
        "stock_by_product": {"5": {"quantidade_disponivel": saldo, "codigo": "P-001", "nome": "Parafuso", "estoque_minimo": minimo}},
    }.items():
        setattr(state, name, value)
    object.__setattr__(state, "get_state", AsyncMock(return_value=auth_state))
    return state


async def _run(state: ExitState) -> None:
    async for _ in state.register_exit():
        pass


class RegisterExitAlertTest(unittest.IsolatedAsyncioTestCase):
    def _patch_exit(self, **result):
        response = {"movement_id": 42, "saldo_anterior": "12", "saldo_atual": "8", "data_hora": 1762250400000}
        response.update(result)
        return patch(
            "Meu_projeto.pages.movimentacoes.auth_client.create_stock_exit",
            new_callable=AsyncMock,
            return_value=response,
        )

    async def test_saida_abaixo_do_minimo_envia_alerta_ao_usuario_logado(self):
        auth_state = _auth_state()
        state = _exit_state(auth_state)
        with (
            self._patch_exit(),
            patch(SEND_PATH, new_callable=AsyncMock, return_value="msg-1") as send,
        ):
            await _run(state)
        self.assertEqual(state.error_message, "")
        self.assertTrue(state.success_message.startswith("Saída registrada com sucesso."))
        self.assertEqual(state.alert_message, "Alerta de estoque mínimo enviado para almoxarife@exemplo.com.")
        self.assertEqual(send.await_args.kwargs["para"], "almoxarife@exemplo.com")
        self.assertEqual(send.await_args.kwargs["chave_idempotencia"], "alerta-estoque-42")

    async def test_sem_saldo_atual_usa_quantidade_disponivel_menos_saida(self):
        auth_state = _auth_state()
        state = _exit_state(auth_state)
        with (
            self._patch_exit(saldo_atual=None),
            patch(SEND_PATH, new_callable=AsyncMock, return_value="msg-1") as send,
        ):
            await _run(state)
        send.assert_awaited_once()
        self.assertIn("Saldo atual: 8", send.await_args.kwargs["texto"])

    async def test_saldo_acima_do_minimo_nao_envia(self):
        auth_state = _auth_state()
        state = _exit_state(auth_state, saldo="20")
        with (
            self._patch_exit(saldo_atual="16"),
            patch(SEND_PATH, new_callable=AsyncMock) as send,
        ):
            await _run(state)
        send.assert_not_awaited()
        self.assertEqual(state.alert_message, "")
        self.assertEqual(state.alert_error, "")

    async def test_falha_do_alerta_mantem_saida_registrada(self):
        auth_state = _auth_state()
        state = _exit_state(auth_state)
        erro = EmailEnvioError("EMAIL_PROVIDER_REJECTED", "recusado", status_code=403)
        with (
            self._patch_exit(),
            patch(SEND_PATH, new_callable=AsyncMock, side_effect=erro),
        ):
            await _run(state)
        self.assertEqual(state.error_message, "")
        self.assertTrue(state.success_message.startswith("Saída registrada com sucesso."))
        self.assertEqual(state.alert_error, "Saída registrada, mas o alerta por e-mail não foi enviado.")

    async def test_saida_rejeitada_nao_envia_alerta(self):
        from Meu_projeto.services.xano_client import XanoRequestError

        auth_state = _auth_state()
        state = _exit_state(auth_state)
        rejeicao = XanoRequestError("INSUFFICIENT_STOCK", "INSUFFICIENT_STOCK", 400, {})
        with (
            patch(
                "Meu_projeto.pages.movimentacoes.auth_client.create_stock_exit",
                new_callable=AsyncMock,
                side_effect=rejeicao,
            ),
            patch(SEND_PATH, new_callable=AsyncMock) as send,
        ):
            await _run(state)
        send.assert_not_awaited()
        self.assertEqual(state.error_message, "Estoque insuficiente para esta saída.")


if __name__ == "__main__":
    unittest.main()
