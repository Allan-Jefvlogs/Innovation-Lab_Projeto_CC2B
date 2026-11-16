"""Pré-validação e apresentação; o Xano continua sendo a autoridade de recebimento."""

import os
from decimal import Decimal, InvalidOperation
from typing import Any


PURCHASE_RECEIPTS_ENABLED = os.getenv("NEXSTOCK_PURCHASE_RECEIPTS_ENABLED", "true").lower() == "true"


def receipt_preview(order: dict[str, Any], product_id: int, quantity: object) -> dict[str, str]:
    """Usa decimais sem inferir unidades legadas ou vínculo pelo produto."""
    if order.get("produto_id") != product_id:
        raise ValueError("O pedido não pertence ao produto selecionado.")
    if order.get("status") not in {"aguardando_recebimento", "recebimento_parcial"}:
        raise ValueError("O pedido não está disponível para recebimento.")
    unit = order.get("unidade_medida_solicitada")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("Unidade histórica não confirmada. Use entrada avulsa ou solicite conferência autorizada.")
    try:
        requested = Decimal(str(order["quantidade_solicitada"]))
        received = Decimal(str(order["quantidade_recebida"]))
        amount = Decimal(str(quantity).replace(",", "."))
        if not all(v.is_finite() for v in (requested, received, amount)):
            raise InvalidOperation
        if requested <= 0 or received < 0 or received >= requested or amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, KeyError, ValueError, TypeError):
        raise ValueError("Quantidades de recebimento inválidas.") from None
    remaining = requested - received
    if amount > remaining:
        raise ValueError("A quantidade excede o restante do pedido.")
    accumulated = received + amount
    return {
        "solicitada": str(requested), "recebida": str(received),
        "restante": str(remaining), "unidade": unit,
        "acumulado": str(accumulated),
        "status": "concluida" if accumulated == requested else "recebimento_parcial",
    }
