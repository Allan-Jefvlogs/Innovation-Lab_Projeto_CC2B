# Tarefas

- [x] Estender `GET /stock` com validação e filtro opcional por situação antes da paginação.
- [x] Criar `GET /stock_summary` autorizado por `stock.read` e com contagens reais por situação.
- [x] Adicionar métodos de consulta de estoque e resumo no XanoClient.
- [x] Criar StockState para resumo, paginação, erros e filtro atual.
- [x] Substituir mocks em `/estoque` e implementar páginas reutilizáveis de situação.
- [x] Manter a proteção de `/estoque` pela autorização já existente.
- [x] Substituir navegação por situação por filtro selecionável na própria `/estoque`.
- [x] Incluir busca paginada por código/nome combinável com situação.
- [x] Validar XanoScript via MCP; OpenSpec strict, `reflex compile --dry` e `git diff --check` passaram.
- [x] Executar e revisar os dry-runs isolados de GET /stock e GET /stock_summary, confirmando somente UPDATEs esperados, sem publicação.
