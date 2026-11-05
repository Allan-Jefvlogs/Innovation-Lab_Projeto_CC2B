"""Envio de e-mail transacional pela API HTTP do Resend."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)

# Carrega variáveis do arquivo .env caso exista na raiz do projeto
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass


RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_FROM_EMAIL = "onboarding@resend.dev"
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_RECIPIENTS = 50


class EmailEnvioError(Exception):
    """Falha identificável no envio de e-mail."""

    def __init__(self, codigo: str, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.codigo = codigo
        self.message = message
        self.status_code = status_code


def _endereco_valido(endereco: str) -> bool:
    """Validação básica: a validação definitiva fica com o provedor."""
    endereco = endereco.strip()
    if "<" in endereco and endereco.endswith(">"):
        endereco = endereco[endereco.rfind("<") + 1:-1].strip()
    local, separador, dominio = endereco.rpartition("@")
    return bool(separador and local and "." in dominio and " " not in endereco)


def _texto_preenchido(valor: Optional[str]) -> bool:
    return valor is not None and valor.strip() != ""


def _timeout_configurado() -> float:
    try:
        return max(0.1, float(os.getenv("RESEND_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _sem_chave(texto: str, chave: str) -> str:
    return texto.replace(chave, "[REDACTED]") if chave else texto


def _mensagem_do_provedor(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("name") or payload)
    return str(payload)


async def enviar_email(
    para: Union[str, List[str]],
    assunto: str,
    html: Optional[str] = None,
    texto: Optional[str] = None,
    remetente: Optional[str] = None,
    responder_para: Optional[str] = None,
    chave_idempotencia: Optional[str] = None,
    *,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> str:
    """Envia um e-mail pelo Resend e retorna o id da mensagem.

    Levanta ``EmailEnvioError`` com ``codigo`` em ``INVALID_INPUT``,
    ``EMAIL_CONFIGURATION_MISSING``, ``EMAIL_PROVIDER_REJECTED``,
    ``EMAIL_RATE_LIMITED`` ou ``EMAIL_PROVIDER_UNAVAILABLE``.
    """
    destinatarios = [para] if isinstance(para, str) else list(para or [])
    destinatarios = [str(item).strip() for item in destinatarios]
    if not destinatarios or len(destinatarios) > MAX_RECIPIENTS:
        raise EmailEnvioError("INVALID_INPUT", f"Informe de 1 a {MAX_RECIPIENTS} destinatários.")
    if any(not _endereco_valido(item) for item in destinatarios):
        raise EmailEnvioError("INVALID_INPUT", "Informe destinatários com e-mail válido.")
    if not _texto_preenchido(assunto):
        raise EmailEnvioError("INVALID_INPUT", "Informe o assunto do e-mail.")
    if not _texto_preenchido(html) and not _texto_preenchido(texto):
        raise EmailEnvioError("INVALID_INPUT", "Informe o conteúdo HTML ou texto do e-mail.")

    remetente_efetivo = (remetente or os.getenv("RESEND_FROM_EMAIL") or DEFAULT_FROM_EMAIL).strip()
    if not _endereco_valido(remetente_efetivo):
        raise EmailEnvioError("INVALID_INPUT", "Informe um remetente com e-mail válido.")
    if _texto_preenchido(responder_para) and not _endereco_valido(responder_para):
        raise EmailEnvioError("INVALID_INPUT", "Informe um endereço de resposta válido.")

    chave = (os.getenv("EMAIL_TOKEN") or "").strip()
    if not chave:
        raise EmailEnvioError(
            "EMAIL_CONFIGURATION_MISSING",
            "Envio de e-mail não configurado: defina EMAIL_TOKEN no ambiente.",
        )

    payload: Dict[str, Any] = {
        "from": remetente_efetivo,
        "to": destinatarios,
        "subject": assunto.strip(),
    }
    if _texto_preenchido(html):
        payload["html"] = html
    if _texto_preenchido(texto):
        payload["text"] = texto
    if _texto_preenchido(responder_para):
        payload["reply_to"] = responder_para.strip()

    headers = {
        "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
    }
    if _texto_preenchido(chave_idempotencia):
        headers["Idempotency-Key"] = chave_idempotencia.strip()

    try:
        async with httpx.AsyncClient(timeout=_timeout_configurado(), transport=transport) as client:
            response = await client.post(RESEND_EMAILS_URL, json=payload, headers=headers)
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        logger.warning("Falha de transporte ao enviar e-mail: %s", type(exc).__name__)
        raise EmailEnvioError(
            "EMAIL_PROVIDER_UNAVAILABLE",
            "Não foi possível conectar ao serviço de e-mail. Tente novamente mais tarde.",
        ) from None

    status = response.status_code
    if 200 <= status < 300:
        try:
            message_id = response.json().get("id")
        except (ValueError, AttributeError):
            message_id = None
        if not message_id:
            raise EmailEnvioError(
                "EMAIL_PROVIDER_UNAVAILABLE",
                "O serviço de e-mail respondeu sem identificador da mensagem.",
                status_code=status,
            )
        return str(message_id)

    detalhe = _sem_chave(_mensagem_do_provedor(response), chave)
    logger.warning("Resend recusou o envio (HTTP %s): %s", status, detalhe)
    if status == 429:
        raise EmailEnvioError("EMAIL_RATE_LIMITED", f"Limite de envio atingido: {detalhe}", status_code=status)
    if 400 <= status < 500:
        raise EmailEnvioError("EMAIL_PROVIDER_REJECTED", f"E-mail recusado pelo provedor: {detalhe}", status_code=status)
    raise EmailEnvioError(
        "EMAIL_PROVIDER_UNAVAILABLE",
        f"Serviço de e-mail indisponível (HTTP {status}).",
        status_code=status,
    )
