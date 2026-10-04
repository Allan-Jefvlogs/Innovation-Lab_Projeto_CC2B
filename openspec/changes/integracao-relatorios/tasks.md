## Especificação

- [x] 1.1 Inspecionar contratos e permissões de movimentações e resumo de estoque existentes.
- [x] 1.2 Validar a change OpenSpec em modo strict antes da implementação.

## Xano

- [x] 2.1 Acrescentar filtros nullable de data inicial, data final e Fornecedor em `GET /movements`, preservando filtros, joins, ordenação e paginação.
- [x] 2.2 Criar `GET /movements_summary` para total de registros e soma de quantidades de entradas/saídas sobre todo o conjunto filtrado.
- [ ] 2.3 Validar os XanoScripts alterados/criados pelo MCP, quando disponível, e preparar dry-run isolado; não publicar.

## Cliente e tela Reflex

- [x] 3.1 Estender `XanoClient.list_movements` com filtros de data e Fornecedor, omitindo valores vazios.
- [x] 3.2 Adicionar `XanoClient.get_movements_summary` com validação do contrato.
- [x] 3.3 Criar `ReportState` com filtros combináveis, opções paginadas, indicadores, estados e navegação.
- [x] 3.4 Substituir conteúdo mockado de `/relatorios` por filtros, cards e tabela paginada reais.
- [x] 3.5 Formatar os intervalos de datas como dias completos em `America/Sao_Paulo` e validar a ordem.

## Verificação

- [x] 4.1 Validar `reflex compile --dry`.
- [x] 4.2 Validar `openspec validate integracao-relatorios --strict`.
- [x] 4.3 Validar `git diff --check`.
- [ ] 4.4 Revisar os artefatos Xano do dry-run e registrar que não foram publicados.
