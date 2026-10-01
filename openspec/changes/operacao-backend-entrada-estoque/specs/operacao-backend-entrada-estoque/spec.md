# Specification: Operação backend de Entrada de Estoque

## ADDED Requirements

### Requirement: O backend MUST persistir movimentações de estoque com referências íntegras

O Xano MUST manter uma tabela `inventory_movement` com identificador, `product_id`, tipo (`entrada` ou `saida`), quantidade decimal, data/hora, `user_id`, `supplier_id` opcional, motivo obrigatório e observação opcional. Referências MUST apontar para registros existentes. Uma movimentação confirmada MUST ter quantidade maior que zero. Esta change MUST criar somente movimentações do tipo `entrada`.

#### Scenario: Entrada confirmada é rastreável
- **WHEN** uma entrada é confirmada
- **THEN** o histórico MUST identificar produto, tipo, quantidade, data/hora, usuário responsável, motivo e Fornecedor quando fornecido

#### Scenario: Fornecedor opcional
- **WHEN** uma entrada válida não informa Fornecedor
- **THEN** a entrada MUST poder ser confirmada com `supplier_id` nulo

### Requirement: POST /entries MUST exigir autenticação e autorização de entrada

O endpoint `POST /entries` do grupo `Inventory Stock` MUST exigir usuário autenticado e autorização backend `stock.entry` dentro da transação. O seed MUST adicionar `stock.entry` ao catálogo idempotentemente e conceder o grant inicial somente ao perfil `stockkeeper`. O perfil `administrator` MUST usar o bypass integral existente sem grant persistido; `read_only` MUST ser rejeitado enquanto não possuir grant. Grants preexistentes MUST ser preservados pelo seed.

#### Scenario: Líder e Almoxarife autorizados
- **WHEN** Administrador/Líder ou Almoxarife autorizado solicita uma entrada
- **THEN** o endpoint MUST prosseguir para as validações da operação

#### Scenario: Auxiliar sem grant
- **WHEN** Auxiliar sem `stock.entry` solicita uma entrada
- **THEN** o backend MUST rejeitar com `PERMISSION_DENIED` sem alterar saldo ou histórico

#### Scenario: Usuário não autenticado ou sem perfil válido
- **WHEN** a solicitação não possui autenticação/perfil autorizado
- **THEN** o backend MUST rejeitar antes de confirmar qualquer escrita

### Requirement: A entrada MUST validar produto, quantidade, Fornecedor e motivo

O corpo MUST exigir `product_id`, `quantidade` decimal maior que zero e `motivo` não vazio. O Produto MUST existir e estar ativo. `supplier_id` MAY ser omitido; quando informado, o Fornecedor MUST existir e estar ativo. O Fornecedor padrão do Produto MUST NOT ser obrigatório nem imposto pelo backend. `observacao` MAY ser omitida ou nula. `user_id` MUST NOT ser aceito como autoridade do cliente.

#### Scenario: Produto inexistente ou inativo
- **WHEN** o `product_id` não existe ou referencia Produto inativo
- **THEN** a operação MUST ser rejeitada com `PRODUCT_NOT_FOUND` ou `PRODUCT_INACTIVE`
- **AND** saldo e histórico MUST permanecer inalterados

#### Scenario: Quantidade ou motivo inválido
- **WHEN** quantidade é menor ou igual a zero ou o motivo está vazio após trim
- **THEN** a operação MUST ser rejeitada como `INVALID_INPUT`
- **AND** nenhuma movimentação MUST ser criada nem saldo alterado

#### Scenario: Tipo de input incompatível
- **WHEN** `product_id`, `quantidade` ou `data_hora` não pode ser convertido pelo tipo declarado no input Xano
- **THEN** a validação nativa do Xano MUST rejeitar a requisição antes do stack
- **AND** nenhuma movimentação MUST ser criada nem saldo alterado

#### Scenario: Fornecedor inválido
- **WHEN** `supplier_id` informado não existe ou está inativo
- **THEN** a operação MUST ser rejeitada com `SUPPLIER_NOT_FOUND` ou `SUPPLIER_INACTIVE`
- **AND** nenhuma movimentação MUST ser criada nem saldo alterado

#### Scenario: Fornecedor padrão diferente
- **WHEN** o cliente informa outro Fornecedor existente e ativo, ou não informa Fornecedor, ainda que Produto possua Fornecedor padrão
- **THEN** o backend MUST aceitar o contexto escolhido se as demais regras forem satisfeitas

### Requirement: A data/hora da entrada MUST usar valor informado ou horário do backend

`data_hora` MUST ser opcional e validada como timestamp pelo Xano. Quando informada, a movimentação MUST persistir o timestamp enviado. Quando omitida, o backend MUST obter a hora atual do servidor durante a conclusão da entrada. Valor inválido MUST ser rejeitado antes de qualquer escrita.

#### Scenario: Timestamp informado
- **WHEN** a entrada recebe timestamp válido
- **THEN** o valor informado MUST ser persistido

#### Scenario: Timestamp omitido
- **WHEN** a entrada não informa `data_hora`
- **THEN** o backend MUST persistir `now` do servidor e MUST NOT depender de preenchimento do frontend

#### Scenario: Timestamp inválido
- **WHEN** o valor recebido não pode ser interpretado como timestamp
- **THEN** a validação nativa do input `timestamp` MUST rejeitar a entrada antes do stack
- **AND** nenhuma movimentação MUST ser gravada nem saldo alterado

### Requirement: A confirmação da entrada MUST atualizar saldo e histórico atomicamente

O endpoint MUST validar Produto ativo e Fornecedor, atualizar o saldo persistido para `saldo_lido + quantidade` usando `db.get` e `db.edit` suportados pela instância e criar o registro histórico dentro da mesma `db.transaction`. O saldo MUST existir previamente; sua ausência MUST rejeitar com `STOCK_BALANCE_NOT_FOUND`, sem criar saldo implicitamente. Falha em qualquer escrita MUST reverter todas as escritas da transação. A estratégia atual MUST documentar que read-modify-write não garante preservar incrementos concorrentes para o mesmo Produto.

#### Scenario: Entrada confirmada
- **WHEN** uma entrada válida é confirmada
- **THEN** o saldo MUST aumentar exatamente pela quantidade solicitada
- **AND** uma movimentação `entrada` MUST ser registrada com o mesmo Produto, quantidade, data/hora, usuário e contexto
- **AND** a resposta MUST incluir `movement_id`, `product_id`, `quantidade`, `saldo_anterior`, `saldo_atual`, `data_hora`, `supplier_id` e `user_id`
- **AND** a resposta MUST incluir também `motivo` e `observacao`

#### Scenario: Deadlock ao editar o saldo
- **WHEN** a edição do saldo falha por deadlock
- **THEN** o endpoint MUST retornar `STOCK_CONCURRENCY_CONFLICT`

#### Scenario: Outro erro ao editar o saldo
- **WHEN** a edição do saldo falha por outro erro
- **THEN** o endpoint MUST retornar `STOCK_UPDATE_FAILED`
- **AND** a transação MUST reverter sem movimento nem alteração parcial do saldo

#### Scenario: Falha ao registrar movimento ou saldo
- **WHEN** qualquer gravação dentro da transação falha
- **THEN** saldo e histórico MUST permanecer como antes da operação

#### Scenario: Saldo não inicializado
- **WHEN** Produto existe mas não possui linha `inventory_stock`
- **THEN** o endpoint MUST rejeitar com `STOCK_BALANCE_NOT_FOUND`
- **AND** MUST NOT inserir movimento nem criar saldo automaticamente

### Requirement: A implementação MUST explicitar a limitação de atualização concorrente

Na instância Xano atual, a operação MUST usar apenas `db.get`, `db.edit` e `db.transaction` suportados, sem depender de `db.direct_query` que exige upgrade. A estratégia de leitura e edição MUST manter atualização do saldo e criação da movimentação atomicamente por requisição, mas a especificação MUST deixar claro que duas entradas simultâneas podem ler o mesmo saldo e sobrescrever um incremento. Nenhuma garantia de lost-update prevention ou serialização MUST ser alegada até haver mecanismo suportado e validado.

#### Scenario: Duas entradas concorrentes no mesmo Produto
- **WHEN** duas entradas válidas concorrentes leem o mesmo saldo antes de qualquer uma gravar
- **THEN** a implementação atual MAY perder um incremento por read-modify-write
- **AND** essa limitação MUST permanecer documentada e a concorrência MUST permanecer como validação pendente

#### Scenario: Falha em uma transação concorrente
- **WHEN** uma das entradas falha antes da confirmação
- **THEN** as escritas daquela transação MUST ser revertidas sem movimento ou saldo parcial

