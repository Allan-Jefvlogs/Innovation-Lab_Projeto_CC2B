# fundacao-tecnica-estoque Specification

## Purpose
TBD - created by archiving change fundacao-tecnica-estoque. Update Purpose after archive.

## Requirements

### Requirement: Cada Produto deve possuir um saldo único e não negativo

O Xano MUST manter no máximo um registro de `inventory_stock` por Produto. `quantidade_disponivel` MUST ser decimal, iniciar em zero e nunca ser menor que zero. A situação do estoque MUST ser derivada e MUST NOT ser persistida como estado redundante.

#### Scenario: Produto novo
- **WHEN** um Produto é criado
- **THEN** o Xano cria seu saldo inicial igual a zero na mesma transação
- **AND** falha na criação do saldo MUST reverter também a criação do Produto

#### Scenario: Produto existente sem saldo
- **WHEN** a rotina interna idempotente de inicialização é executada
- **THEN** cada Produto sem registro de saldo recebe quantidade zero
- **AND** registros de saldo existentes permanecem inalterados

#### Scenario: Quantidade negativa
- **WHEN** uma gravação tenta definir quantidade menor que zero
- **THEN** o backend rejeita a gravação

### Requirement: Situação do estoque deve ser calculada pelo backend

O backend MUST calcular `situacao_estoque` a partir da quantidade disponível e `product.estoque_minimo`: `sem_estoque` para zero; `abaixo_minimo` para saldo positivo menor que o mínimo; `normal` para saldo positivo maior ou igual ao mínimo.

#### Scenario: Saldo zero
- **WHEN** a quantidade disponível é zero
- **THEN** `situacao_estoque` é `sem_estoque`

#### Scenario: Saldo positivo abaixo do mínimo
- **WHEN** a quantidade é maior que zero e menor que o mínimo
- **THEN** `situacao_estoque` é `abaixo_minimo`

#### Scenario: Saldo positivo no mínimo ou acima
- **WHEN** a quantidade é maior que zero e maior ou igual ao mínimo
- **THEN** `situacao_estoque` é `normal`

### Requirement: Consulta de estoque deve ser autenticada, autorizada e paginada

O endpoint `GET /stock` do grupo `Inventory Stock` MUST exigir autenticação e a permissão `stock.read`. MUST retornar listagem paginada, com até 100 registros por página, contendo `product_id`, `codigo`, `nome`, `quantidade_disponivel`, `estoque_minimo` e `situacao_estoque`. A consulta MUST usar o saldo persistido no Xano e não reconstruir quantidade no Reflex.

#### Scenario: Usuário autorizado consulta estoque
- **WHEN** usuário autenticado possui `stock.read` e consulta uma página válida
- **THEN** o endpoint retorna `items` com os campos de saldo e produto e metadados de paginação

#### Scenario: Usuário sem grant consulta estoque
- **WHEN** usuário autenticado não possui `stock.read`
- **THEN** o Xano rejeita a consulta sem revelar os saldos

#### Scenario: Requisição sem autenticação
- **WHEN** a consulta é feita sem autenticação válida
- **THEN** o Xano rejeita a requisição

### Requirement: Permissão de leitura de estoque integra o catálogo sem apagar grants

O catálogo MUST incluir `stock.read`. A provisão inicial MUST acrescentar o grant a Almoxarife e Auxiliar de almoxarifado sem remover ou substituir grants existentes. Administrador MUST manter acesso integral implícito sem grant editável.

#### Scenario: Provisionamento repetido
- **WHEN** a função de seed é executada mais de uma vez
- **THEN** `stock.read` e os grants iniciais ausentes são criados sem duplicidade e grants já existentes são preservados
