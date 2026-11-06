"""Cobertura local de enviar_email.

Todas as requisições usam httpx.MockTransport. Nenhuma chamada real ao Resend
é feita por estes testes.
"""

from __future__ import annotations

import asyncio
import json
import os
import unittest
from unittest.mock import patch

import httpx

from Meu_projeto.services.email_service import (
    _carregar_env,
    DEFAULT_FROM_EMAIL,
    RESEND_EMAILS_URL,
    EmailEnvioError,
    enviar_email,
)


MOCK_TOKEN = "re_test_token_not_real"


class _Recorder:
    def __init__(self, response: httpx.Response | Exception):
        self.response = response
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _send(recorder: _Recorder, **kwargs):
    params = {"para": "dono@example.com", "assunto": "Teste", "texto": "Olá"}
    params.update(kwargs)
    return asyncio.run(enviar_email(**params, transport=httpx.MockTransport(recorder)))


class EnviarEmailTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {"EMAIL_TOKEN": MOCK_TOKEN}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("RESEND_FROM_EMAIL", None)

    def _assert_error(self, codigo: str, recorder: _Recorder, **kwargs) -> EmailEnvioError:
        with self.assertRaises(EmailEnvioError) as ctx:
            _send(recorder, **kwargs)
        self.assertEqual(ctx.exception.codigo, codigo)
        self.assertNotIn(MOCK_TOKEN, str(ctx.exception))
        return ctx.exception

    def test_envio_aceito_retorna_id_e_envia_contrato(self):
        recorder = _Recorder(httpx.Response(200, json={"id": "msg-123"}))

        message_id = _send(recorder, html="<p>Olá</p>")

        self.assertEqual(message_id, "msg-123")
        self.assertEqual(len(recorder.requests), 1)
        request = recorder.requests[0]
        self.assertEqual(str(request.url), RESEND_EMAILS_URL)
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["Authorization"], f"Bearer {MOCK_TOKEN}")
        self.assertNotIn("Idempotency-Key", request.headers)
        body = json.loads(request.content)
        self.assertEqual(body["from"], DEFAULT_FROM_EMAIL)
        self.assertEqual(body["to"], ["dono@example.com"])
        self.assertEqual(body["subject"], "Teste")
        self.assertEqual(body["html"], "<p>Olá</p>")
        self.assertEqual(body["text"], "Olá")
        self.assertNotIn("reply_to", body)

    def test_remetente_do_ambiente(self):
        recorder = _Recorder(httpx.Response(200, json={"id": "msg-1"}))
        with patch.dict(os.environ, {"RESEND_FROM_EMAIL": "NexStock <nao-responda@exemplo.com>"}):
            _send(recorder)
        self.assertEqual(json.loads(recorder.requests[0].content)["from"], "NexStock <nao-responda@exemplo.com>")

    def test_reply_to_e_idempotencia(self):
        recorder = _Recorder(httpx.Response(200, json={"id": "msg-1"}))
        _send(recorder, responder_para="aluno@dominio.net", chave_idempotencia="pedido-42")
        request = recorder.requests[0]
        self.assertEqual(request.headers["Idempotency-Key"], "pedido-42")
        self.assertEqual(json.loads(request.content)["reply_to"], "aluno@dominio.net")

    def test_entradas_invalidas_nao_chamam_provedor(self):
        casos = [
            {"texto": None},
            {"texto": "   "},
            {"assunto": " "},
            {"para": []},
            {"para": "sem-arroba"},
            {"para": ["ok@example.com", ""]},
            {"para": [f"u{i}@example.com" for i in range(51)]},
            {"responder_para": "invalido"},
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                recorder = _Recorder(httpx.Response(200, json={"id": "x"}))
                self._assert_error("INVALID_INPUT", recorder, **caso)
                self.assertEqual(recorder.requests, [])

    def test_chave_ausente(self):
        recorder = _Recorder(httpx.Response(200, json={"id": "x"}))
        with patch.dict(os.environ, {"EMAIL_TOKEN": ""}):
            self._assert_error("EMAIL_CONFIGURATION_MISSING", recorder)
        self.assertEqual(recorder.requests, [])

    def test_rejeicao_do_provedor_nao_expoe_chave(self):
        recorder = _Recorder(httpx.Response(403, json={"message": f"chave {MOCK_TOKEN} sem permissão"}))
        erro = self._assert_error("EMAIL_PROVIDER_REJECTED", recorder)
        self.assertEqual(erro.status_code, 403)

    def test_validacao_do_provedor(self):
        self._assert_error("EMAIL_PROVIDER_REJECTED", _Recorder(httpx.Response(422, json={"message": "invalid"})))

    def test_limite_de_envio(self):
        self._assert_error("EMAIL_RATE_LIMITED", _Recorder(httpx.Response(429, json={"message": "slow down"})))

    def test_provedor_indisponivel_sem_retry(self):
        for response in (httpx.Response(503, text="down"), httpx.ConnectError("offline"), httpx.ReadTimeout("timeout")):
            with self.subTest(response=response):
                recorder = _Recorder(response)
                self._assert_error("EMAIL_PROVIDER_UNAVAILABLE", recorder)
                self.assertEqual(len(recorder.requests), 1)


class CarregarEnvTest(unittest.TestCase):
    def test_le_env_sem_sobrescrever_ambiente(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / ".env"
            caminho.write_text(
                '# comentario\nTESTE_ENV_NOVO="valor"\nTESTE_ENV_EXISTENTE=do_arquivo\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"TESTE_ENV_EXISTENTE": "do_ambiente"}, clear=False):
                _carregar_env(caminho)
                self.assertEqual(os.environ["TESTE_ENV_NOVO"], "valor")
                self.assertEqual(os.environ["TESTE_ENV_EXISTENTE"], "do_ambiente")
            os.environ.pop("TESTE_ENV_NOVO", None)

    def test_arquivo_ausente_nao_falha(self):
        from pathlib import Path

        _carregar_env(Path("/caminho/inexistente/.env"))


if __name__ == "__main__":
    unittest.main()
