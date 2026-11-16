"""Verificação GET explícita, sem login, auth/me, payloads ou retries.

A identidade Compras deve ser confirmada pelo operador na sessão já aberta.
Sem --execute, apenas mostra o plano e não acessa a rede.
"""

import argparse
import ast
import logging
import os
from pathlib import Path
import time

import httpx


ROOT = Path(__file__).resolve().parents[1]
TOKEN_ENV = "NEXSTOCK_COMPRAS_TEST_TOKEN"
INTERVAL_SECONDS = 4.5


def project_urls():
    """Lê só constantes do cliente, sem importá-lo ou carregar credenciais/.env."""
    names = {"DEFAULT_XANO_URL", "INVENTORY_CANONICAL_GROUP", "STOCK_CANONICAL_GROUP"}
    values = {}
    tree = ast.parse((ROOT / "Meu_projeto/services/xano_client.py").read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    values[target.id] = ast.literal_eval(node.value)
    base = values["DEFAULT_XANO_URL"].rstrip("/")
    url = httpx.URL(base)
    if url.scheme != "https" or url.userinfo or url.query or url.fragment:
        raise ValueError("Configuração de URL incompatível com o teste.")
    configured = os.getenv("XANO_API_BASE_URL", base).rstrip("/")
    if configured != base:
        raise ValueError("URL de ambiente difere da configuração padrão; revisar antes do teste.")
    return {"catalog": f"{base}/{values['INVENTORY_CANONICAL_GROUP']}",
            "stock": f"{base}/{values['STOCK_CANONICAL_GROUP']}"}


def cases(urls):
    return [
        ("Solicitações", urls["stock"], "/purchase_requests", {"page": 1, "per_page": 1}, 200),
        ("Detalhes e histórico", urls["stock"], "/purchase_requests/by_id/{request_id}",
         {"history_page": 1, "history_per_page": 1}, 200),
        ("Usuários", urls["catalog"], "/users", {"page": 1, "per_page": 1}, 403),
        ("Produtos", urls["catalog"], "/products", {"page": 1, "per_page": 1}, 403),
        ("Estoque", urls["stock"], "/stock", {"page": 1, "per_page": 1}, 403),
        ("Perfis e permissões", urls["catalog"], "/permissions", {}, 403),
    ]


def classify(status, expected, body):
    if status == 401:
        return "INCONCLUSIVO: sessão ausente/inválida"
    if status == 404:
        return "INCONCLUSIVO: rota/registro ausente ou ocultação; investigar"
    if status == 429:
        return "INCONCLUSIVO: limite de requisições; parar, sem retry"
    if status == 403 and expected == 403:
        # Don't mistake an inactive account or another generic refusal for a grant check.
        if isinstance(body, dict) and any(body.get(k) == "PERMISSION_DENIED" for k in ("code", "message", "error")):
            return "APROVADO"
        return "INCONCLUSIVO: 403 sem PERMISSION_DENIED reconhecido"
    if status == expected == 200:
        return "APROVADO" if isinstance(body, dict) else "INCONCLUSIVO: contrato inválido"
    if 200 <= status < 300 and expected == 403:
        return "REPROVADO: acesso indevido"
    if status == 403:
        return "REPROVADO: acesso permitido foi negado"
    return "INCONCLUSIVO: resposta inesperada"


def run_checks(client, urls, pause=time.sleep):
    selected_id = None
    all_passed = True
    requested = False
    for name, base, route, params, expected in cases(urls):
        if "{request_id}" in route:
            if selected_id is None:
                print(f"{name} | GET {route} | HTTP — | esperado {expected} | INCONCLUSIVO: sem ID obtido na lista")
                all_passed = False
                continue
            route = route.replace("{request_id}", str(selected_id))
        if requested:
            pause(INTERVAL_SECONDS)
        requested = True
        try:
            # The only HTTP operation in this script. Redirects/retries are disabled.
            response = client.get(base + route, params=params)
        except httpx.HTTPError:
            print(f"{name} | GET {route} | HTTP — | esperado {expected} | INCONCLUSIVO: transporte")
            return 2
        try:
            body = response.json()
        except ValueError:
            body = None
        outcome = classify(response.status_code, expected, body)
        if response.status_code == 200 and expected == 200 and isinstance(body, dict):
            if route == "/purchase_requests":
                items = body.get("items")
                if (not isinstance(items, list) or any(type(body.get(k)) is not int for k in ("itemsTotal", "curPage", "perPage"))):
                    outcome = "INCONCLUSIVO: contrato de lista inválido"
                elif items and isinstance(items[0], dict) and type(items[0].get("id")) is int and items[0]["id"] > 0:
                    selected_id = items[0]["id"]
            elif not isinstance(body.get("solicitacao"), dict) or body["solicitacao"].get("id") != selected_id:
                outcome = "INCONCLUSIVO: contrato de detalhes inválido"
        print(f"{name} | GET {route} | HTTP {response.status_code} | esperado {expected} | {outcome}")
        all_passed &= outcome == "APROVADO"
        if response.status_code in (401, 429) or outcome.startswith("REPROVADO: acesso indevido"):
            return 2
    return 0 if all_passed else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Autoriza as chamadas GET desta execução.")
    parser.add_argument("--confirm-compras-session", action="store_true", help="Operador conferiu que o token é da sessão Compras, perfil ID 4, sem grants extras.")
    args = parser.parse_args()
    try:
        urls = project_urls()
    except (ValueError, KeyError, OSError):
        print("Configuração inválida. Nenhuma chamada executada.")
        return 2
    if not args.execute:
        for name, base, route, params, expected in cases(urls):
            print(f"{name} | GET {base}{route} | parâmetros {params} | esperado {expected} | NÃO EXECUTADO")
        return 0
    token = os.environ.pop(TOKEN_ENV, "").strip()
    if not args.confirm_compras_session or not token or any(c.isspace() for c in token):
        print("Exige confirmação manual da sessão Compras e token temporário válido. Nenhuma chamada executada.")
        return 2
    logging.disable(logging.CRITICAL)
    try:
        with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=15,
                          follow_redirects=False, trust_env=False,
                          transport=httpx.HTTPTransport(retries=0)) as client:
            return run_checks(client, urls)
    except Exception:
        # Never expose an exception containing request headers or response data.
        print("Teste interrompido por falha local; nenhum detalhe sensível foi exibido.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
