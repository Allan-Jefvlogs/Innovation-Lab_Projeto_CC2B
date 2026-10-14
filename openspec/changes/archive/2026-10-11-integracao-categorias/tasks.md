# Tasks

- [x] 1. Atualizar `POST /categories` para trim, rejeitar nome vazio e manter verificação de duplicidade/status inicial.
- [x] 2. Criar `PATCH /categories/by_id/{category_id}/activate` com `category.update` e retorno do estado persistido.
- [x] 3. Validar os XanoScripts alterados com Xano Developer MCP.
- [x] 4. Adicionar `create_category`, `activate_category` e `inactivate_category` ao XanoClient; reutilizar `list_categories`.
- [x] 5. Implementar `CategoryState` com carregamento paginado, busca local, criação, alternância confirmada e tratamento de erros.
- [x] 6. Substituir a tabela mock de `/categorias` por ID, nome, status e switch; remover coluna Produtos.
- [x] 7. Ligar a rota `/categorias` ao carregamento autenticado do novo State.
- [x] 8. Confirmar que o módulo de Produtos mantém o filtro de Categorias ativas e a referência inativa na edição sem alterações desnecessárias.
- [x] 9. Executar `reflex compile --dry`, OpenSpec strict e `git diff --check`.
- [x] 10. Executar e revisar dry-runs isolados dos endpoints de cadastro e ativação de Categorias, confirmando somente UPDATEs, sem publicação.
