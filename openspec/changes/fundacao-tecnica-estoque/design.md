# Design: Fundação técnica de Estoque

## Decisões

### Um saldo por produto, com início em zero

`inventory_stock` terá `id`, `product_id` obrigatório e único, e `quantidade_disponivel` decimal obrigatório com mínimo zero. A referência única concretiza o relacionamento 1:1 do modelo de domínio. Decimal é coerente com `product.estoque_minimo`; regras de precisão operacional ficam para a change de movimentação.

Todo Produto terá um saldo. Produto recém-criado recebe saldo zero na mesma transação da criação cadastral. Produtos já existentes serão inicializados por `Inventory/initialize_stock_balances`, função interna idempotente e paginada (100 Produtos por chamada), que apenas cria saldo zero onde não há registro. O operador executará páginas em sequência até uma página retornar menos de 100 itens. Não existe tabela ou histórico de movimentações na implementação atual que permita inferir quantidade anterior; a função não deve ser executada em ambiente que possua saldos externos não reconciliados.

### Situação derivada

Não será persistida situação redundante. `GET /stock` calcula:

- `sem_estoque` quando quantidade é zero;
- `abaixo_minimo` quando quantidade é maior que zero e menor que `product.estoque_minimo`;
- `normal` quando quantidade é maior que zero e maior ou igual ao mínimo.

O caso de mínimo zero segue literalmente as condições: todo saldo positivo é `normal`.

### Autorização

O endpoint requer `auth = "user"` e `Inventory/authorize_permission` com `stock.read`. Administrador usa o bypass integral existente. `stock.read` será acrescentada ao catálogo; os grants iniciais de Almoxarife e Auxiliar serão acrescidos sem remover nem reescrever grants existentes. Permissões editadas manualmente permanecem sob a gestão já existente.

### Consulta

Novo grupo `Inventory Stock`, canonical `estoque`, com `GET /stock`, filtros de paginação no padrão do projeto (`page`, `per_page`, máximo 100) e resposta paginada `items`. A consulta parte de `inventory_stock`, associa Produto em uma consulta com JOIN e projeta `product_id`, `codigo`, `nome`, `quantidade_disponivel`, `estoque_minimo` e `situacao_estoque`. A situação é montada no backend para evitar cálculo de domínio no Reflex. Não há chamada por produto no frontend.

### Implantação e dados anteriores

Ordem: publicar tabela e função; publicar a criação transacional de Produto e a permissão; executar uma vez a inicialização idempotente dos Produtos existentes; publicar o grupo/endpoint. Nesta etapa não haverá push nem execução da função. O importador remoto deve ser verificado antes de publicar o endpoint, pois a validação local do MCP não garante aceitação remota.

## Arquivos Xano previstos

- Novo `xano/table/inventory_stock.xs`.
- Novo `xano/function/inventory/initialize_stock_balances.xs`.
- Novo `xano/api/inventory_stock/api_group.xs` e `stock_get.xs`.
- Alterados `xano/api/inventory_catalog/products_post.xs` e `xano/function/inventory/seed_initial_data.xs`.

## Riscos

- Produtos existentes sem saldo precisam ser inicializados antes da consulta remota; ausência inesperada após a migração causa omissão na listagem de saldos.
- Produto e saldo devem ser gravados na mesma transação para impedir cadastro sem saldo.
- JOINs são aceitos pela documentação/validador local, mas o histórico do workspace registra incompatibilidades no importador remoto; nenhum sucesso remoto é presumido.
- A inicialização com zero só é correta porque o backend local não possui movimentações/saldos anteriores. Ambientes com dados externos exigem reconciliação antes de executar a função.

## Limites

Nenhuma operação de entrada/saída, alteração de saldo após criação, histórico, UI Reflex, dashboard, relatório, sync, push ou commit é incluída.
