# Tarefas

- [x] Estender `GET /stock` com validação e filtro opcional por situação antes da paginação.
- [x] Criar `GET /stock_summary` autorizado por `stock.read` e com contagens reais por situação.
- [x] Adicionar métodos de consulta de estoque e resumo no XanoClient.
- [x] Criar StockState para resumo, paginação, erros e filtro atual.
- [x] Substituir mocks em `/estoque` e implementar páginas reutilizáveis de situação.
- [x] Manter a proteção de `/estoque` pela autorização já existente.
- [x] Substituir navegação por situação por filtro selecionável na própria `/estoque`.
- [x] Incluir busca paginada por código/nome combinável com situação.
- [ ] Validar XanoScript via MCP (indisponível nesta sessão); OpenSpec strict, `reflex compile --dry` e `git diff --check` passaram.
- [ ] Executar dry-run isolado do Xano; CLI não iniciou por erro `uv_os_get_passwd returned ENOMEM`.
