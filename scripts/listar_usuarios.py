"""Busca todos os usuários no Xano pelo GET /users, percorrendo todas as páginas.

Uso, a partir da raiz do projeto:

    python scripts/listar_usuarios.py --token SEU_TOKEN
    python scripts/listar_usuarios.py --token SEU_TOKEN --saida usuarios.json

O token é o authToken de uma sessão autenticada. No NexStock logado, ele fica
no localStorage do navegador, na chave `auth_token` (DevTools → Application →
Local Storage). O token precisa ser de um usuário com permissão de leitura de
usuários (por exemplo, o Administrador). Também aceita XANO_TOKEN no ambiente.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Meu_projeto.services.xano_client import XanoError, auth_client  # noqa: E402

POR_PAGINA = 100


async def buscar_todos(token: str) -> list:
    usuarios = []
    pagina = 1
    while True:
        resposta = await auth_client.list_users(token, page=pagina, per_page=POR_PAGINA)
        itens = resposta["items"]
        usuarios.extend(itens)
        print(f"Página {pagina}: {len(itens)} usuário(s)", file=sys.stderr)
        if len(itens) < POR_PAGINA or not resposta.get("nextPage"):
            break
        pagina += 1
    return usuarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca todos os usuários do Xano.")
    parser.add_argument("--token", default=os.getenv("XANO_TOKEN"))
    parser.add_argument("--saida", default=None, help="Arquivo JSON de saída (opcional).")
    args = parser.parse_args()
    if not args.token:
        parser.error("Informe --token (ou XANO_TOKEN).")

    try:
        usuarios = asyncio.run(buscar_todos(args.token))
    except XanoError as erro:
        print(f"FALHOU: {erro.message}", file=sys.stderr)
        return 1

    conteudo = json.dumps(usuarios, ensure_ascii=False, indent=2, default=str)
    if args.saida:
        Path(args.saida).write_text(conteudo, encoding="utf-8")
        print(f"{len(usuarios)} usuário(s) salvos em {args.saida}", file=sys.stderr)
    else:
        print(conteudo)
        print(f"Total: {len(usuarios)} usuário(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
