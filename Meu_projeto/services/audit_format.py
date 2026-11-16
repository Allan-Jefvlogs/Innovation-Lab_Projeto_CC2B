"""Apresentação segura e legível dos eventos administrativos."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


FIELD_LABELS = {
    "codigo": "Código",
    "nome": "Nome",
    "descricao": "Descrição",
    "categoria_id": "Categoria (ID)",
    "fornecedor_padrao_id": "Fornecedor padrão (ID)",
    "unidade_medida": "Unidade de medida",
    "estoque_minimo": "Estoque mínimo",
    "status": "Status",
    "is_active": "Situação",
    "nome_razao_social": "Nome/razão social",
    "tipo_documento": "Tipo de documento",
    "documento": "Documento",
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "contato": "Contato",
    "telefone": "Telefone",
    "email": "E-mail",
    "endereco": "Endereço",
    "inventory_profile_id": "Perfil",
}

SENSITIVE_FIELDS = {
    "documento", "cpf", "cnpj", "contato", "telefone", "phone",
    "nome_razao_social",
    "email", "e-mail", "endereco", "address", "senha", "password",
    "hash", "token", "secret", "credential", "credencial", "chave", "mail", "key",
}

ACTION_LABELS = {
    "criado": "Criado",
    "atualizado": "Atualizado",
    "ativado": "Ativado",
    "inativado": "Inativado",
    "perfil_alterado": "Perfil alterado",
    "permissoes_alteradas": "Permissões alteradas",
    "credencial_redefinida": "Credencial redefinida",
}

ENTITY_LABELS = {
    "produto": "Produto",
    "categoria": "Categoria",
    "fornecedor": "Fornecedor",
    "usuario": "Usuário",
    "perfil": "Perfil",
    "permissao": "Permissão",
}

PERMISSION_LABELS = {
    "administrator": "Acesso administrativo",
    "category.read": "Consultar categorias",
    "category.create": "Criar categorias",
    "category.update": "Editar categorias",
    "category.inactivate": "Inativar categorias",
    "product.read": "Consultar produtos",
    "product.create": "Criar produtos",
    "product.update": "Editar produtos",
    "product.inactivate": "Ativar ou inativar produtos",
    "supplier.read": "Consultar fornecedores",
    "supplier.create": "Criar fornecedores",
    "supplier.update": "Editar fornecedores",
    "supplier.inactivate": "Inativar fornecedores",
    "stock.read": "Consultar estoque",
    "stock.entry": "Registrar entradas",
    "stock.exit": "Registrar saidas",
    "movement.read": "Consultar movimentacoes",
    "report.read": "Consultar relatorios",
    "purchase_request.read": "Consultar solicitações de compra",
    "purchase_request.manage": "Gerenciar solicitações de compra",
    "purchase_request.status.update": "Atualizar status de compras",
}

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def _label(key: Any) -> str:
    raw = str(key)
    return FIELD_LABELS.get(raw, "Campo alterado")


def _is_sensitive(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    if normalized == "tipo_documento":
        return False
    parts = set(normalized.split("_"))
    sensitive_parts = {
        "documento", "document", "cpf", "cnpj", "contato", "telefone",
        "phone", "email", "endereco", "address", "senha", "password",
        "hash", "token", "secret", "credential", "credencial", "chave", "mail", "key",
    }
    return normalized in SENSITIVE_FIELDS or bool(parts & sensitive_parts)


def _display_value(key: str, value: Any, profile_names: dict[int, str]) -> str:
    if value is None:
        return "vazio"
    if key == "inventory_profile_id":
        try:
            profile_id = int(value)
        except (ValueError, TypeError):
            return "Perfil identificado"
        return profile_names.get(profile_id, f"Perfil (ID {profile_id})")
    if key in {"status", "is_active"}:
        if value is True or value in {"ativo", "active"}:
            return "Ativo"
        if value is False or value in {"inativo", "inactive"}:
            return "Inativo"
    return str(value)


def _permission_names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [PERMISSION_LABELS.get(str(code), "Permissão do sistema") for code in values]


def format_changes(
    changes: Any,
    *,
    profile_names: dict[int, str] | None = None,
) -> str:
    """Formata somente informações permitidas; nunca serializa JSON bruto."""
    profile_names = profile_names or {}
    if isinstance(changes, str):
        try:
            changes = json.loads(changes)
        except (json.JSONDecodeError, TypeError):
            return "Detalhes registrados, sem campos seguros para exibir"
    if not isinstance(changes, dict) or not changes:
        return "Detalhes não registrados"

    if "revision_before" in changes or "revision_after" in changes:
        parts: list[str] = []
        before, after = changes.get("revision_before"), changes.get("revision_after")
        if before is not None and after is not None:
            parts.append(f"Revisão de permissões: {before} → {after}")
        added = _permission_names(changes.get("permissions_added"))
        removed = _permission_names(changes.get("permissions_removed"))
        if added:
            parts.append("Permissões adicionadas: " + ", ".join(added))
        if removed:
            parts.append("Permissões removidas: " + ", ".join(removed))
        return "; ".join(parts) or "Detalhes não registrados"

    before = changes.get("before")
    after = changes.get("after")
    if isinstance(before, dict) and isinstance(after, dict):
        parts = []
        for key in dict.fromkeys([*before.keys(), *after.keys()]):
            old, new = before.get(key), after.get(key)
            if old == new:
                continue
            label = _label(key)
            if _is_sensitive(key):
                parts.append(f"{label} atualizado (valores omitidos)")
            elif key not in FIELD_LABELS:
                parts.append("Campo alterado (valor omitido)")
            else:
                parts.append(
                    f"{label}: {_display_value(key, old, profile_names)} → "
                    f"{_display_value(key, new, profile_names)}"
                )
        return "; ".join(parts) or "Nenhuma diferença registrada"

    # Writers de fornecedor registram booleanos como indicadores de alteracao.
    boolean_changes = [key for key, value in changes.items() if isinstance(value, bool) and value]
    if boolean_changes or any(isinstance(value, bool) for value in changes.values()):
        parts = []
        for key in boolean_changes:
            label = _label(key)
            parts.append(
                f"{label} atualizado (valores omitidos)"
                if _is_sensitive(key)
                else f"{label} alterado"
            )
        return "; ".join(parts) or "Nenhuma diferença detectada"

    parts = []
    for key, value in changes.items():
        if key == "inventory_profile_id" and isinstance(value, (int, str)):
            parts.append("Perfil atribuído: " + _display_value(key, value, profile_names))
        elif key in FIELD_LABELS and not _is_sensitive(key):
            parts.append(f"{_label(key)}: {_display_value(key, value, profile_names)}")
        elif _is_sensitive(key):
            parts.append(f"{_label(key)} alterado (valores omitidos)")
    return "; ".join(parts) or "Detalhes registrados, sem campos seguros para exibir"


def present_event(
    item: dict[str, Any], *, profile_names: dict[int, str] | None = None
) -> dict[str, str]:
    timestamp = item.get("occurred_at")
    try:
        occurred = datetime.fromtimestamp(float(timestamp) / 1000, LOCAL_TZ).strftime("%d/%m/%Y %H:%M:%S")
    except (TypeError, ValueError, OverflowError, OSError):
        occurred = "Data indisponível"
    action = str(item.get("action_type") or "")
    entity = str(item.get("entity_type") or "")
    summary = str(item.get("summary") or "")
    # Resumos existentes de senha foram escritos sem incluir credenciais.
    return {
        "data": occurred,
        "usuario": str(item.get("actor_name") or "Usuário indisponível"),
        "acao": ACTION_LABELS.get(action, action or "Ação indisponível"),
        "entidade": ENTITY_LABELS.get(entity, entity or "Entidade indisponível"),
        "registro": str(item.get("entity_id") or "—"),
        "resumo": summary or "Resumo não registrado",
        "alteracoes": format_changes(
            item.get("changes", item.get("changes_summary")),
            profile_names=profile_names,
        ),
    }


def referenced_profile_ids(items: list[dict[str, Any]]) -> set[int]:
    ids: set[int] = set()
    for item in items:
        changes = item.get("changes")
        if isinstance(changes, dict):
            value = changes.get("inventory_profile_id")
            if isinstance(value, dict):
                value = value.get("after")
            try:
                if value is not None:
                    ids.add(int(value))
            except (ValueError, TypeError):
                continue
    return ids
