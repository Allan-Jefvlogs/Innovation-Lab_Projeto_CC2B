# Design: Operação backend de Saída de Estoque

## Modelo existente

Reutilizar `inventory_movement`, que já possui `product_id`, `tipo` com valores `entrada` e `saida`, `quantidade` decimal, `data_hora`, `user_id`, `supplier_id` nullable, `motivo` e `observacao`. Não criar tabela nova. A linha de saldo oficial continua sendo `inventory_stock`, com unicidade por `product_id`.

## Endpoint e contrato

- Grupo: `Inventory Stock`, identificador canônico `api:estoque`.
- Rota: `POST /exits`.
- Autenticação: `auth = "user"`.
- Permissão: `stock.exit`, verificada por `Inventory/authorize_permission` dentro da transação.
- Inputs obrigatórios: `product_id` inteiro, `quantidade` decimal, `motivo` texto trimado.
- Inputs opcionais: `data_hora` timestamp e `observacao` texto nullable.
- O endpoint não aceita `user_id` nem `supplier_id` como inputs.

O perfil `administrator` mantém acesso integral implícito pela função central. O seed adiciona `stock.exit` ao catálogo e ao conjunto inicial de grants de `stockkeeper`, de forma idempotente e aditiva. `read_only` não recebe grant inicial. Grants já existentes não são removidos nem reescritos.

## Validação e efeitos

Dentro de uma única `db.transaction`, o endpoint:

1. exige `stock.exit` para o usuário autenticado;
2. rejeita quantidade menor ou igual a zero ou motivo vazio com `INVALID_INPUT`;
3. exige Produto existente e ativo (`PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE`);
4. carrega a linha `inventory_stock` do Produto e rejeita ausência com `STOCK_BALANCE_NOT_FOUND`;
5. compara `quantidade` ao saldo lido e rejeita quantidade maior com `INSUFFICIENT_STOCK`, antes de qualquer escrita;
6. calcula `saldo_atual - quantidade` e atualiza o saldo com `db.edit`;
7. cria `inventory_movement` com `tipo = "saida"`, `$auth.id`, o motivo, a observação e `supplier_id = null`;
8. retorna movimento, saldo anterior e saldo atual.

O input `decimal` e as preconditions nativas fazem a validação numérica; `quantidade > 0` rejeita zero, negativos e valores que não satisfaçam a comparação. `quantidade <= saldo` impede que a operação, isoladamente, calcule saldo negativo. A precisão segue o tipo decimal já usado em `inventory_stock`.

Para `data_hora`, a variável efetiva inicia com `now` do backend e recebe o timestamp informado quando presente. O usuário responsável sempre vem de `$auth.id`. Saída não usa Fornecedor; o campo da movimentação recebe `null`.

## Atomicidade e concorrência

`db.edit inventory_stock` e `db.add inventory_movement` executam sob o mesmo `db.transaction`. Falha em qualquer escrita propaga erro e desfaz a atualização/inserção da transação. Deadlock detectado ao editar o saldo retorna `STOCK_CONCURRENCY_CONFLICT`; outra falha dessa edição retorna `STOCK_UPDATE_FAILED`.

A estratégia disponível para esta instância é read-modify-write (`db.get` → validar/calcular → `db.edit`). `db.direct_query` não é utilizável nesta instância e não será usado. A documentação MCP XanoScript 2.7.1 lista níveis de isolamento transacional, mas a validação MCP de um bloco mínimo com `isolation = "serializable"` falhou com `Expecting --> stack <-- but found --> '\n' <--`; há também evidência anterior do parser/importador do workspace rejeitando essa construção. A sintaxe, portanto, não está confirmada como utilizável nesta instância. Não há lock/CAS ou incremento condicional de linha confirmado para esta instância, e essa sintaxe de isolamento não será introduzida.

Consequentemente, a transação garante atomicidade das escritas da requisição, mas não serializa mudanças concorrentes entre Saídas e Entradas. Duas Saídas podem ler o mesmo saldo, ambas passar pela precondition e sobrescrever uma à outra; os movimentos poderiam exceder a quantidade líquida refletida no saldo. O saldo calculado por uma execução isolada nunca é negativo, mas não se declara proteção contra overselling/lost update concorrente. Uma garantia forte depende de mecanismo de concorrência suportado e verificado no workspace antes da publicação.

## Resposta

Retorna `movement_id`, `product_id`, `tipo`, `quantidade`, `saldo_anterior`, `saldo_atual`, `data_hora`, `supplier_id` nulo, `user_id`, `motivo` e `observacao`.

## Erros

- `PERMISSION_DENIED` e erros de perfil: função central de autorização.
- `INVALID_INPUT`: quantidade não positiva ou motivo vazio; tipos fora do input declarado são rejeitados pelo validador Xano.
- `PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE`.
- `STOCK_BALANCE_NOT_FOUND`.
- `INSUFFICIENT_STOCK`.
- `STOCK_CONCURRENCY_CONFLICT` para deadlock do `db.edit`.
- `STOCK_UPDATE_FAILED` para outra falha ao editar o saldo.

Falha na gravação do movimento propaga a exceção para fora da transação, provocando rollback do `db.edit`.

## Testes e publicação

Validação estática MCP e OpenSpec não provam comportamento de runtime nem concorrência. Testes funcionais devem ser executados depois, em datasource isolada: autorização por perfil, saldo exato/insuficiente, decimal, Produto inexistente/inativo, saldo ausente, timestamps, movimento com ator, rollback e concorrência. Nenhum runtime ou publicação faz parte desta etapa local.
