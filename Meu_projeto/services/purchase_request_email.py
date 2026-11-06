"""E-mail da solicitação de compra para o destinatário informado na Reposição."""

import html
import logging
from typing import Any

from .email_service import EmailEnvioError, enviar_email

logger = logging.getLogger(__name__)

# Destinatário fixo do aviso de cancelamento (conta de teste do Resend).
CANCELAMENTO_DESTINATARIO = "mateus.dotta@aluno.impacta.edu.br"


async def enviar_email_cancelamento_compra(
    *,
    solicitacao_id: Any,
    produto: str,
    justificativa: str,
    usuario: str,
) -> bool:
    """Avisa por e-mail que a solicitação foi cancelada. Retorna True se o provedor aceitou."""
    linhas = [
        ("Solicitação", str(solicitacao_id)),
        ("Produto", produto or "-"),
        ("Justificativa", justificativa or "-"),
        ("Cancelada por", usuario or "-"),
    ]
    assunto = f"[NexStock] Solicitação de compra {solicitacao_id} cancelada"
    corpo_html = (
        "<h2>NexStock</h2><p>A solicitação de compra abaixo foi <strong>cancelada</strong>.</p><table>"
        + "".join(
            f"<tr><td><strong>{html.escape(rotulo)}</strong></td><td>{html.escape(valor)}</td></tr>"
            for rotulo, valor in linhas
        )
        + "</table>"
    )
    corpo_texto = "A solicitação de compra abaixo foi cancelada.\n\n" + "\n".join(
        f"{rotulo}: {valor}" for rotulo, valor in linhas
    )
    try:
        await enviar_email(
            para=CANCELAMENTO_DESTINATARIO,
            assunto=assunto,
            html=corpo_html,
            texto=corpo_texto,
            chave_idempotencia=f"cancelamento-compra-{solicitacao_id}",
        )
    except EmailEnvioError as erro:
        logger.warning("E-mail de cancelamento não enviado: codigo=%s", erro.codigo)
        return False
    except Exception:
        logger.exception("Falha inesperada ao enviar e-mail de cancelamento")
        return False
    return True


async def enviar_email_solicitacao_compra(
    *,
    destinatario: str,
    solicitacao_id: Any,
    codigo: str,
    nome: str,
    quantidade: str,
    unidade: str,
    urgencia: str,
    usuario: str,
) -> bool:
    """Envia o pedido ao destinatário. Retorna True se o provedor aceitou o envio."""
    produto = f"{codigo} - {nome}".strip(" -")
    quantidade_texto = f"{quantidade} {unidade}".strip()
    linhas = [
        ("Solicitação", str(solicitacao_id)),
        ("Produto", produto),
        ("Quantidade solicitada", quantidade_texto),
        ("Urgência", urgencia),
        ("Solicitante", usuario or "-"),
    ]
    assunto = f"[NexStock] Solicitação de compra {solicitacao_id}: {produto}"
    corpo_html = (
        f"<h2>NexStock</h2><p>Foi registrada uma solicitação de compra para "
        f"<strong>{html.escape(produto)}</strong>.</p><table>"
        + "".join(
            f"<tr><td><strong>{html.escape(rotulo)}</strong></td><td>{html.escape(valor)}</td></tr>"
            for rotulo, valor in linhas
        )
        + "</table>"
    )
    corpo_texto = f"Foi registrada uma solicitação de compra para {produto}.\n\n" + "\n".join(
        f"{rotulo}: {valor}" for rotulo, valor in linhas
    )
    try:
        await enviar_email(
            para=destinatario,
            assunto=assunto,
            html=corpo_html,
            texto=corpo_texto,
            chave_idempotencia=f"solicitacao-compra-{solicitacao_id}",
        )
    except EmailEnvioError as erro:
        logger.warning("E-mail da solicitação de compra não enviado: codigo=%s", erro.codigo)
        return False
    except Exception:
        logger.exception("Falha inesperada ao enviar e-mail da solicitação de compra")
        return False
    return True
