# Tasks

- [ ] 1. Atualizar `POST /categories` para trim, rejeitar nome vazio e manter verificação de duplicidade/status inicial.
- [ ] 2. Criar `PATCH /categories/by_id/{category_id}/activate` com `category.update` e retorno do estado persistido.
- [ ] 3. Validar os XanoScripts alterados com Xano Developer MCP.
- [ ] 4. Adicionar `create_category`, `activate_category` e `inactivate_category` ao XanoClient; reutilizar `list_categories`.
- [ ] 5. Implementar `CategoryState` com carregamento paginado, busca local, criação, alternância confirmada e tratamento de erros.
- [ ] 6. Substituir a tabela mock de `/categorias` por ID, nome, status e switch; remover coluna Produtos.
- [ ] 7. Ligar a rota `/categorias` ao carregamento autenticado do novo State.
- [ ] 8. Confirmar que o módulo de Produtos mantém o filtro de Categorias ativas e a referência inativa na edição sem alterações desnecessárias.
- [ ] 9. Executar `reflex compile --dry`, OpenSpec strict e `git diff --check`.
- [ ] 10. Executar dry-run Xano isolado para os objetos alterados e revisar CREATE/UPDATE; aguardar revisão antes do push.
