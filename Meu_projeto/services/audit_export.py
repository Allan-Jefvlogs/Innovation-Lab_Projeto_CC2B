"""Coleta paginada e limitada para exportação administrativa."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


MAX_AUDIT_EXPORT_RECORDS = 500
AUDIT_EXPORT_PAGE_SIZE = 100


class AuditExportLimitError(ValueError):
    """A quantidade filtrada excede o limite de exportação completa."""


class AuditExportConsistencyError(ValueError):
    """O conjunto mudou ou a paginacao retornou uma colecao incompleta."""


async def collect_all_audit_logs(
    fetch_page: Callable[..., Awaitable[dict[str, Any]]],
    *,
    filters: dict[str, Any],
    max_records: int = MAX_AUDIT_EXPORT_RECORDS,
) -> list[dict[str, Any]]:
    first = await fetch_page(page=1, per_page=AUDIT_EXPORT_PAGE_SIZE, **filters)
    total = first.get("itemsTotal")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise AuditExportConsistencyError("Total de auditoria inválido")
    if total > max_records:
        raise AuditExportLimitError("A exportação completa excede o limite configurado")
    if not isinstance(first.get("items"), list):
        raise AuditExportConsistencyError("Página de auditoria inválida")
    if total == 0:
        if first["items"]:
            raise AuditExportConsistencyError("Lista vazia inconsistente")
        return []

    rows = list(first["items"])
    seen_ids = {
        item.get("id")
        for item in rows
        if isinstance(item, dict)
        and isinstance(item.get("id"), int)
        and not isinstance(item.get("id"), bool)
        and item.get("id") > 0
    }
    if len(seen_ids) != len(rows):
        raise AuditExportConsistencyError("IDs de auditoria duplicados ou inválidos")
    page_count = (total + AUDIT_EXPORT_PAGE_SIZE - 1) // AUDIT_EXPORT_PAGE_SIZE
    if first.get("curPage") != 1 or first.get("perPage") != AUDIT_EXPORT_PAGE_SIZE:
        raise AuditExportConsistencyError("Metadados de paginação inconsistentes")

    for page in range(2, page_count + 1):
        result = await fetch_page(
            page=page,
            per_page=AUDIT_EXPORT_PAGE_SIZE,
            **filters,
        )
        items = result.get("items")
        if (
            not isinstance(items, list)
            or result.get("itemsTotal") != total
            or result.get("curPage") != page
            or result.get("perPage") != AUDIT_EXPORT_PAGE_SIZE
        ):
            raise AuditExportConsistencyError("O conjunto de auditoria mudou durante a exportação")
        for item in items:
            if (
                not isinstance(item, dict)
                or isinstance(item.get("id"), bool)
                or not isinstance(item.get("id"), int)
                or item.get("id") < 1
                or item.get("id") in seen_ids
            ):
                raise AuditExportConsistencyError("Páginas repetidas ou inválidas")
            seen_ids.add(item["id"])
        rows.extend(items)

    if len(rows) != total or len(seen_ids) != total:
        raise AuditExportConsistencyError("A coleta não contém todos os eventos filtrados")
    return rows
