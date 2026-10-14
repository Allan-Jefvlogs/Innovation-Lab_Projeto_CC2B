## Especificação

- [x] 1.1 Inspecionar contratos e permissões de movimentações e resumo existentes.
- [x] 1.2 Atualizar filtros, cards, layout e exportação da tela de Relatórios.

## Xano

- [x] 2.1 Acrescentar filtros de data e Fornecedor em `GET /movements`.
- [x] 2.2 Criar resumo de movimentos protegido por `report.read`.
- [x] 2.3 Aplicar filtro opcional `tipo` em `GET /movements_summary`.
- [x] 2.4 Validar os XanoScripts alterados pelo MCP e preparar dry-run isolado; não publicar.

## Cliente e tela Reflex

- [x] 3.1 Compartilhar contrato de filtros entre listagem e resumo.
- [x] 3.2 Manter filtros editáveis separados dos filtros aplicados.
- [x] 3.3 Exibir somente indicadores de registros, unidades de entrada e unidades de saída.
- [x] 3.4 Organizar datas na mesma linha, com quebra responsiva.
- [x] 3.5 Exportar XLSX completo em memória percorrendo páginas.
- [x] 3.6 Exportar PDF em paisagem usando bibliotecas padrão Python.
- [x] 3.7 Registrar respostas Xano sem expor token e manter mensagens amigáveis UTF-8.

## Verificação

- [x] 4.1 Validar `reflex compile --dry`.
- [x] 4.2 Validar `openspec validate integracao-relatorios --strict`.
- [x] 4.3 Validar `git diff --check`.
- [x] 4.4 Revisar os quatro previews de dry-run (`movements_get.xs`, `movements_summary_get.xs`, `report_options_get.xs` e `authorize_permission.xs`): todos indicaram `UPDATE`, sem `CREATE`, `DELETE` ou `Unresolved References`; nenhuma publicação foi feita.
