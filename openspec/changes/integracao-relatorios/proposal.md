# Integrar relatórios operacionais de estoque

## Problema

A rota `/relatorios` ainda apresenta conteúdo estático do protótipo e não permite analisar movimentações registradas nem a situação atual do estoque.

## Objetivo

Integrar a página a dados reais do Xano, permitindo combinar período, tipo, Produto e Fornecedor, exibir totais corretos e consultar as movimentações em páginas.

## Escopo

- Criar `ReportState` isolado para filtros, opções, indicadores, paginação, carregamento e erros.
- Reutilizar autenticação, `GET /products`, `GET /suppliers`, `GET /stock_summary` e `GET /movements`.
- Acrescentar ao `GET /movements` filtros opcionais de período e Fornecedor.
- Criar `GET /movements_summary` protegido por `stock.read` para totais do conjunto filtrado, sem limitar os totais à página visível.
- Substituir mocks por filtros, cards e tabela paginada de dados reais.
- Registrar requisitos e cenários verificáveis nesta change.

## Fora do escopo

- Exportação PDF, Excel ou CSV.
- Escritas de movimentação, alteração de estoque ou mudanças de grants.
- Alterações em Entrada, Saída ou Histórico.
- Publicação Xano ou Git.

## Dependências e limites

- `GET /movements` já fornece dados relacionados por joins e suporta `tipo`, `product_id` e paginação.
- O resumo de movimentos precisa considerar todo o conjunto filtrado, independente da página da tabela.
- Os indicadores de abaixo do mínimo e sem estoque descrevem a situação atual e reutilizam `GET /stock_summary`.
- A autorização do backend permanece em `stock.read`; a interface não substitui essa autorização.

## Impactos esperados

- Tela `/relatorios` passa de placeholder para relatório real.
- `movements_get.xs` recebe filtros temporais e de Fornecedor.
- Um endpoint de leitura de resumo de movimentações será acrescentado.
- Alterações Xano serão preparadas e validadas localmente; nenhuma publicação faz parte desta change.
