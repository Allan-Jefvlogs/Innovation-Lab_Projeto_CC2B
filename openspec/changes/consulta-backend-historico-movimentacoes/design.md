# Design: Consulta do histórico de movimentações

## Endpoint e autorização

Adicionar `GET /movements` ao grupo `Inventory Stock`, cujo caminho canônico é `api:estoque`. O endpoint exige autenticação Xano e chama `Inventory/authorize_permission` com `stock.read`. Essa permissão já representa leitura de estoque e é atribuída aos perfis Almoxarife e Auxiliar; o perfil Líder recebe acesso integral pela regra central de autorização. Nenhuma permissão, matriz ou seed precisa ser alterado.

## Consulta enriquecida

Uma única `db.query inventory_movement` faz joins `left` com `product`, `user` e `supplier`, usando os IDs persistidos na movimentação. Os campos `product_code`, `product_name`, `user_name` e `supplier_name` são projeções `eval`. Os joins `left` preservam movimentos mesmo quando uma referência não puder ser resolvida; não se filtra status de Produto ou Fornecedor, portanto a inativação não oculta histórico. Para Saída ou entrada sem Fornecedor, `supplier_id` e `supplier_name` ficam nulos.

O resultado é projetado para `items` com `movement_id`, `product_id`, `product_code`, `product_name`, `tipo`, `quantidade`, `data_hora`, `user_id`, `user_name`, `supplier_id`, `supplier_name`, `motivo` e `observacao`. O metadata de paginação nativo do Xano é preservado.

Os joins ocorrem no banco na consulta paginada; não há consulta de Produto, usuário ou Fornecedor por item e, portanto, não há N+1. `user.name` é o único dado do usuário exposto; senha, token, hash e e-mail não são retornados.

## Filtros, ordenação e paginação

Filtros desta versão: `tipo` (`entrada` ou `saida`), `product_id` e `user_id`. `tipo` inválido retorna `INVALID_INPUT`; `user_id` deve ser inteiro positivo. IDs sem movimentações retornam lista vazia. O filtro `user_id` usa `inventory_movement.user_id` na mesma consulta que aplica `tipo` e `product_id`, sem consulta adicional a usuários nem novo join. Período e Fornecedor ficam para evolução futura.

Para alimentar a seleção de usuários sem depender dos usuários visíveis na página corrente de movimentos, o grupo `Inventory Stock` expõe também `GET /movement_users`, autenticado e autorizado por `stock.read`. Essa consulta separada é paginada, ordenada por nome e ID, e projeta somente `id` e `name`. Ela não exige `inventory_profile_id`, que é anulável e poderia excluir usuários históricos ainda resolvidos pelo join de `inventory_movement`; não altera o endpoint de movimentações nem cria N+1.

`page` começa em 1; `per_page` assume 20 por padrão e aceita no máximo 100. A ordenação é `data_hora DESC, id DESC`. Foi adicionado índice composto nessa ordem para apoiar listagem cronológica paginada.

## Leitura e segurança

O endpoint não escreve nem altera registros. A autenticação ausente é tratada pelo requisito `auth = "user"`; falha de grant usa o erro `PERMISSION_DENIED` produzido pelo autorizador. Erros inesperados seguem o envelope seguro padrão do Xano, sem lógica que exponha traceback.

## Validação

Validar o XanoScript do endpoint e da definição de tabela alterada com o Xano Developer MCP, validar esta change com OpenSpec strict e executar `git diff --check`. Não executar endpoint runtime nem publicar nesta etapa.
