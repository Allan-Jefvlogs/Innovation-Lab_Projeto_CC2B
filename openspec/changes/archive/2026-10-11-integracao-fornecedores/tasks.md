# Tarefas

- [x] 1. Ajustar POST/PATCH existentes para trim e validação de campos cadastrais, preservando unicidade de documento.
- [x] 2. Validar os XanoScripts de cadastro e edição de fornecedores pelo Xano Developer MCP e executar os respectivos dry-runs isolados.
- [x] 3. Adicionar `create_supplier` e `update_supplier` ao XanoClient; reutilizar listagem e detalhe.
- [x] 4. Implementar `SupplierState` com listagem paginada, busca, criação, edição e mensagens.
- [x] 5. Substituir mocks por tabela ID, nome, documento, contato e ação Editar; sem status/exclusão.
- [x] 6. Ligar `/fornecedores` ao carregamento autenticado do State.
- [x] 7. Ajustar seletores relacionados para carregar todos os fornecedores sem filtro pelo status legado.
- [x] 8. Confirmar os grants atuais e que histórico conserva `supplier_id`.
- [x] 9. Executar Reflex compile, OpenSpec strict e `git diff --check`.
- [x] 10. Revisar os previews dos dry-runs de POST e PATCH de fornecedores, confirmando somente UPDATEs, sem realizar publicação nesta Change.