# Consultar histórico de movimentações no backend

## Problema

O sistema grava entradas e saídas reais em `inventory_movement`, mas ainda não oferece uma consulta paginada e enriquecida para exibir o histórico sem chamadas adicionais por movimentação.

## Objetivo

Criar `GET /movements` no grupo `Inventory Stock` (`api:estoque`), autenticado e autorizado pela permissão existente `stock.read`. A resposta deve incluir dados da movimentação, Produto, usuário responsável e Fornecedor quando relacionado.

## Escopo

- Consultar apenas dados persistidos em `inventory_movement`.
- Enriquecer itens com joins de Produto, usuário e Fornecedor.
- Ordenar por data/hora decrescente e desempatar pelo ID decrescente.
- Paginar com `page` e `per_page`, limitado a 100.
- Permitir filtros opcionais por tipo, Produto e usuário responsável (`user_id`).
- Expor lista paginada e segura de usuários para os filtros do Histórico, sem dados sensíveis.
- Preservar registros ligados a cadastros inativos e não alterar movimentos existentes.

## Fora do escopo

- Alterar o frontend ou os endpoints de Entrada, Saída e Estoque.
- Criar nova permissão ou alterar grants.
- Filtros por usuário, Fornecedor ou período nesta versão.
- Publicar ou executar chamadas runtime.
