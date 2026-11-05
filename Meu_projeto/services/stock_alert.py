"""Alerta por e-mail de estoque abaixo do mínimo após uma Saída confirmada."""

import html
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple

from .email_service import EmailEnvioError, enviar_email

logger = logging.getLogger(__name__)

STATUS_NAO_APLICAVEL = "nao_aplicavel"
STATUS_SEM_DESTINATARIO = "sem_destinatario"
STATUS_ENVIADO = "enviado"
STATUS_FALHOU = "falhou"


def _decimal(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _formatar(value: Any) -> str:
    number = _decimal(value)
    if number is None:
        return str(value or "")
    texto = format(number.normalize(), "f") if number == number.to_integral() else format(number, "f")
    return texto.replace(".", ",")


def deve_alertar(saldo_atual: Any, estoque_minimo: Any) -> bool:
    """Toda Saída que deixa o saldo abaixo do mínimo gera alerta."""
    saldo = _decimal(saldo_atual)
    minimo = _decimal(estoque_minimo)
    if saldo is None or minimo is None:
        return False
    return saldo < minimo


def montar_alerta(
    *,
    codigo: str,
    nome: str,
    saldo_atual: Any,
    estoque_minimo: Any,
    quantidade: Any,
    usuario: str,
    data_hora: Any,
) -> Tuple[str, str, str]:
    """Retorna assunto, HTML e texto do alerta."""
    produto = f"{codigo} - {nome}".strip(" -")
    sem_estoque = _decimal(saldo_atual) == 0
    assunto = f"[NexStock] {'Sem estoque' if sem_estoque else 'Estoque abaixo do mínimo'}: {produto}"

    linhas = [
        ("Produto", produto),
        ("Saldo atual", _formatar(saldo_atual)),
        ("Estoque mínimo", _formatar(estoque_minimo)),
        ("Quantidade da saída", _formatar(quantidade)),
        ("Responsável", usuario or "-"),
        ("Data/hora da saída", str(data_hora or "-")),
    ]
    situacao = "está sem estoque" if sem_estoque else "ficou abaixo do estoque mínimo"
    corpo_html = (
        f"<h2>NexStock</h2><p>O produto <strong>{html.escape(produto)}</strong> {situacao} após uma saída.</p>"
        "<table>"
        + "".join(
            f"<tr><td><strong>{html.escape(rotulo)}</strong></td><td>{html.escape(valor)}</td></tr>"
            for rotulo, valor in linhas
        )
        + "</table><p>Avalie a reposição na página de Reposição do NexStock.</p>"
    )
    corpo_texto = (
        f"O produto {produto} {situacao} após uma saída.\n\n"
        + "\n".join(f"{rotulo}: {valor}" for rotulo, valor in linhas)
        + "\n\nAvalie a reposição na página de Reposição do NexStock."
    )
    return assunto, corpo_html, corpo_texto


async def enviar_alerta_estoque_minimo(
    *,
    destinatario: str,
    movement_id: Any,
    codigo: str,
    nome: str,
    saldo_atual: Any,
    estoque_minimo: Any,
    quantidade: Any,
    usuario: str,
    data_hora: Any,
) -> str:
    """Envia o alerta quando aplicável e retorna o status do envio."""
    if not deve_alertar(saldo_atual, estoque_minimo):
        return STATUS_NAO_APLICAVEL
    if not (destinatario or "").strip():
        logger.info("Alerta de estoque mínimo não enviado: usuário logado sem e-mail.")
        return STATUS_SEM_DESTINATARIO

    assunto, corpo_html, corpo_texto = montar_alerta(
        codigo=codigo,
        nome=nome,
        saldo_atual=saldo_atual,
        estoque_minimo=estoque_minimo,
        quantidade=quantidade,
        usuario=usuario,
        data_hora=data_hora,
    )
    chave = f"alerta-estoque-{movement_id}" if movement_id not in (None, "") else None
    try:
        await enviar_email(
            para=destinatario.strip(),
            assunto=assunto,
            html=corpo_html,
            texto=corpo_texto,
            chave_idempotencia=chave,
        )
    except EmailEnvioError as erro:
        logger.warning("Alerta de estoque mínimo não enviado: codigo=%s", erro.codigo)
        return STATUS_FALHOU
    return STATUS_ENVIADO
