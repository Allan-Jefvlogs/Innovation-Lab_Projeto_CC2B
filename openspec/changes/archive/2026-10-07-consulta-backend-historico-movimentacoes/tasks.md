# Tasks: Consulta backend do histórico de movimentações

## 1. Consulta do histórico

- [x] 1.1 Adicionar `GET /movements` no grupo `Inventory Stock` com autenticação e `stock.read`.
- [x] 1.2 Enriquecer os resultados com joins de Produto, usuário e Fornecedor e projetar os campos seguros.
- [x] 1.3 Implementar filtros `tipo` e `product_id`, validação de tipo, ordenação e paginação limitada.
- [x] 1.4 Adicionar índice cronológico composto para `data_hora DESC, id DESC`.
- [x] 1.5 Validar todos os XanoScripts alterados pelo MCP, OpenSpec strict e `git diff --check`.
- [x] 1.6 Revisar o diff antes de qualquer publicação; não publicar nesta mudança.

## 2. Filtro por usuário

- [x] 2.1 Adicionar `user_id` opcional positivo em `GET /movements` e combinar com os filtros existentes na consulta única.
- [x] 2.2 Atualizar a especificação para documentar combinação e resultados sem correspondência.
- [x] 2.3 Criar `GET /movement_users` autenticado, paginado, protegido por `stock.read` e com projeção somente de ID e nome.
- [x] 2.4 Validar XanoScripts pelo MCP, OpenSpec strict e `git diff --check`; não publicar nesta mudança.
