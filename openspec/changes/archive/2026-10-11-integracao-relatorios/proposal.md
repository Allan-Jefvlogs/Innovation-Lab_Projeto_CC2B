# Integrar relatórios operacionais de estoque

## Problema

A tela `/relatorios` precisa manter a leitura operacional real e tornar os filtros, indicadores e exportações coerentes entre si.

## Objetivo

Aplicar filtros de data, tipo, Produto e Fornecedor à tabela e aos indicadores, apresentar somente Movimentações/Entradas/Saídas e exportar todos os registros filtrados para PDF e XLSX.

## Escopo

- Preservar a implementação existente de `ReportState` e `XanoClient`.
- Distinguir filtros editados de filtros aplicados.
- Incluir `tipo` no resumo de movimentações.
- Exportar em memória, percorrendo a paginação do endpoint.
- Documentar layout, filtros, indicadores, erros e exportação.

## Fora do escopo

- Publicação Xano, Git commit ou push.
- Escritas de estoque/movimentação e alterações nos módulos de cadastro.
- Exportação CSV.
