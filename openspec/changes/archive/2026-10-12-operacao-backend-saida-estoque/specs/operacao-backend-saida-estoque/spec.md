# Specification: Operação backend de Saída de Estoque

## ADDED Requirements

### Requirement: POST /exits MUST autenticar e autorizar a Saída

O endpoint `POST /exits` do grupo `Inventory Stock` MUST exigir autenticação e verificar `stock.exit` no backend dentro da transação. `administrator` MUST manter o bypass integral implícito. O seed MUST adicionar `stock.exit` e o grant inicial de `stockkeeper` idempotentemente, sem apagar grants existentes; `read_only` MUST NOT receber grant inicial.

#### Scenario: Líder e Almoxarife autorizados
- **WHEN** Administrador/Líder ou Almoxarife com a autorização aplicável solicita uma Saída
- **THEN** o backend MUST prosseguir com as validações da operação

#### Scenario: Auxiliar não autorizado
- **WHEN** Auxiliar sem `stock.exit` solicita uma Saída
- **THEN** o backend MUST rejeitar com `PERMISSION_DENIED` e MUST NOT alterar saldo ou histórico

#### Scenario: Usuário não autenticado ou perfil inválido
- **WHEN** a requisição não possui sessão/perfil válido
- **THEN** o backend MUST rejeitar antes de confirmar qualquer escrita

### Requirement: A Saída MUST validar Produto, quantidade e motivo

O corpo MUST exigir `product_id`, `quantidade` decimal e `motivo` trimado. O Produto MUST existir e estar ativo. A quantidade MUST ser finita e maior que zero; o motivo MUST permanecer não vazio após trim. O endpoint MUST NOT aceitar `user_id` ou `supplier_id` do cliente.

#### Scenario: Produto inexistente ou inativo
- **WHEN** o Produto não existe ou está inativo
- **THEN** o endpoint MUST rejeitar com `PRODUCT_NOT_FOUND` ou `PRODUCT_INACTIVE`
- **AND** saldo e histórico MUST permanecer inalterados

#### Scenario: Quantidade ou motivo inválido
- **WHEN** quantidade é zero, negativa, não numérica/não finita ou motivo está vazio após trim
- **THEN** o endpoint MUST rejeitar sem alterar saldo nem criar movimento
- **AND** a resposta MUST identificar `INVALID_INPUT` quando a validação do stack for executada

### Requirement: A Saída MUST exigir saldo suficiente e não produzir saldo negativo

O backend MUST carregar `inventory_stock` pelo Produto e MUST rejeitar ausência com `STOCK_BALANCE_NOT_FOUND`. Antes de qualquer escrita, MUST exigir `quantidade <= quantidade_disponivel`; se não houver saldo suficiente, MUST rejeitar com `INSUFFICIENT_STOCK`. Para uma execução sem concorrência, o novo saldo MUST ser `saldo_anterior - quantidade` e MUST ser maior ou igual a zero.

#### Scenario: Saída menor que o saldo
- **WHEN** o saldo é 5 e a Saída é 3
- **THEN** o saldo MUST passar a 2 e o movimento MUST ser registrado

#### Scenario: Saída igual ao saldo
- **WHEN** o saldo é 5 e a Saída é 5
- **THEN** o saldo MUST passar a 0 e o movimento MUST ser registrado

#### Scenario: Saída acima do saldo
- **WHEN** o saldo é 5 e a Saída solicitada é 6
- **THEN** o backend MUST rejeitar com `INSUFFICIENT_STOCK`
- **AND** saldo e histórico MUST permanecer inalterados

### Requirement: A Saída MUST atualizar saldo e histórico na mesma transação

O endpoint MUST usar `db.transaction`, `db.get`, `db.edit` e `db.add` compatíveis com a instância. Deve editar `inventory_stock` e criar `inventory_movement` com `tipo = "saida"` e `supplier_id = null` na mesma transação. Falha de qualquer escrita MUST reverter todas as escritas da requisição.

#### Scenario: Saída confirmada
- **WHEN** uma Saída válida é confirmada
- **THEN** o backend MUST reduzir o saldo pelo valor solicitado
- **AND** MUST criar movimento com Produto, quantidade, data/hora, `$auth.id`, motivo e observação
- **AND** a resposta MUST retornar movimento, `saldo_anterior`, `saldo_atual` e `supplier_id` nulo

#### Scenario: Falha ao editar saldo
- **WHEN** `db.edit` do saldo falha por deadlock
- **THEN** o endpoint MUST retornar `STOCK_CONCURRENCY_CONFLICT` e MUST reverter a transação

#### Scenario: Falha ao editar saldo por outra causa
- **WHEN** `db.edit` falha sem deadlock
- **THEN** o endpoint MUST retornar `STOCK_UPDATE_FAILED` e MUST reverter a transação

#### Scenario: Falha ao criar movimento
- **WHEN** a inserção em `inventory_movement` falha depois da edição do saldo
- **THEN** a transação MUST reverter o saldo e nenhum movimento MUST permanecer

### Requirement: A Saída MUST definir data/hora e usuário no backend

`data_hora` MUST ser opcional. Se for informada e validada pelo input `timestamp`, o movimento MUST usar o valor informado; se omitida, MUST usar `now` do backend. `user_id` MUST sempre vir de `$auth.id`, nunca de payload do cliente.

#### Scenario: Data/hora omitida
- **WHEN** a requisição omite `data_hora`
- **THEN** o movimento MUST receber o timestamp `now` do backend

#### Scenario: Ator autenticado
- **WHEN** a Saída é autorizada e registrada
- **THEN** `inventory_movement.user_id` MUST ser igual a `$auth.id`

### Requirement: A estratégia MUST documentar concorrência sem alegar garantia inexistente

O endpoint MUST usar read-modify-write com `db.get` + `db.edit` dentro da transação e MUST NOT usar `db.direct_query`. Até que um mecanismo de lock, compare-and-set ou isolamento seja aceito pelo parser/importador do workspace, a solução MUST declarar que transações simultâneas podem ler o mesmo saldo e perder atualização ou aceitar Saídas cujo total exceda o saldo inicial. A atomicidade por transação não MUST ser descrita como serialização entre requisições.

#### Scenario: Saídas simultâneas sobre o mesmo saldo
- **WHEN** duas Saídas leem o mesmo saldo antes que qualquer uma grave
- **THEN** a implementação atual MAY sofrer lost update ou overselling
- **AND** a limitação MUST permanecer registrada até ser resolvida por mecanismo suportado e validado

A implementação atual não possui garantia comprovada contra lost update ou overselling.
A atomicidade de uma transação individual não constitui prova de serialização entre
requisições concorrentes. A investigação, implementação e teste simultâneo da proteção
foram transferidos para seguranca-concorrencia-estoque; esta referência não afirma que
essa proteção exista.
