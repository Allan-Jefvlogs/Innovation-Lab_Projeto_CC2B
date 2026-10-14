# Design: integração da tela de Estoque

## Dados e situação

`GET /stock` continua sendo a fonte das linhas da tabela. Seu filtro opcional `situacao` é aplicado na consulta antes da paginação usando o saldo em `inventory_stock` e `product.estoque_minimo`; a situação retornada permanece calculada no backend.

Um endpoint `GET /stock_summary` consulta a mesma junção e obtém os totais por situação com consultas paginadas que retornam `itemsTotal`, sem transferir a lista completa ao navegador. `total` é a soma das três classes mutuamente exclusivas.

O frontend oferece busca por código/nome via parâmetro opcional `search`. O Xano aplica contains case-insensitive antes da paginação, em combinação com `situacao`; a normalização accent-insensitive depende de suporte confirmado no XanoScript desta instância.

Ambos exigem autenticação e permissão existente `stock.read`. Nenhum grant muda.

## Frontend

`StockState` mantém uma página de linhas, metadados de paginação, resumo, situação selecionada, termo de busca, loading e erro. A página principal carrega resumo e primeira página; os cards selecionam ou removem filtros na mesma rota e a busca combina com o filtro ativo.

O guard de perfil mantém a proteção existente em `/estoque`; as rotas de situação separadas foram removidas.

## Limites

Esta mudança não altera tabelas, saldos, entradas, saídas ou status de Produto. Validação estática e dry-run local não confirmam comportamento remoto; publicação ficará pendente de revisão.
