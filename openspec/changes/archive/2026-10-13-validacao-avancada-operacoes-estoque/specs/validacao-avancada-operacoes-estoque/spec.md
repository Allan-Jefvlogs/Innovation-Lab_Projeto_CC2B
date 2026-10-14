# Specification: Validacao avancada das operacoes de estoque

## ADDED Requirements

### Requirement: Testes avancados MUST exigir pre-condicoes seguras e evidencia de estado

Validacoes de rollback ou de linha de saldo ausente MUST ocorrer em ambiente isolado ou
harness aprovado. A conta Xano Free utilizada nao disponibiliza Sandbox nem Data Source
adicional. Escritas no datasource compartilhado MUST exigir autorizacao explicita e dados
ficticios identificados. Cada teste MUST registrar estado anterior, chamada, resposta e estado
posterior sem credenciais. Teste nao executado MUST permanecer pendente.

#### Scenario: Ambiente isolado ou autorizacao nao disponivel
- **WHEN** o caso exige escrita e nao ha ambiente isolado/harness nem autorizacao explicita
- **THEN** a chamada MUST NOT ser executada e o criterio MUST permanecer pendente

### Requirement: Falha posterior a escrita MUST deixar saldo e movimento atomicos

Uma falha controlada depois da primeira escrita de Entrada ou Saida MUST ser testada somente
em ambiente isolado ou harness aprovado. A falha MUST deixar saldo igual ao valor anterior e
nao MUST deixar movimento parcial.

#### Scenario: Falha entre atualizacao do saldo e criacao do movimento
- **WHEN** a escrita do saldo ocorre e uma falha impede a criacao do movimento
- **THEN** o saldo MUST retornar ao valor anterior
- **AND** nenhum movimento da operacao MUST permanecer

### Requirement: Operacao com linha de saldo ausente MUST rejeitar sem escrita

Para Produto existente e ativo sem linha `inventory_stock`, Entrada e Saida MUST rejeitar com
`STOCK_BALANCE_NOT_FOUND` e MUST NOT alterar saldo ou criar movimento.

#### Scenario: Entrada ou Saida sem registro de saldo
- **WHEN** o Produto ativo nao possui linha em `inventory_stock`
- **THEN** a operacao MUST retornar `STOCK_BALANCE_NOT_FOUND`
- **AND** saldo e movimentos MUST permanecer inalterados

### Requirement: Timestamp e respostas MUST corresponder aos registros persistidos

Para Entrada e Saida validas, `data_hora` personalizada MUST representar o mesmo instante na
resposta e no movimento persistido. A validacao MUST conferir todos os campos de resposta
contra o movimento e o saldo correspondente.

#### Scenario: Timestamp personalizado
- **WHEN** a chamada envia `data_hora` conhecida e valida
- **THEN** a resposta e o movimento persistido MUST conter o mesmo instante normalizado

#### Scenario: Resposta completa de Entrada ou Saida
- **WHEN** uma operacao e confirmada
- **THEN** a resposta MUST conter `movement_id`, `product_id`, `tipo`, `quantidade`,
  `saldo_anterior`, `saldo_atual`, `data_hora`, `supplier_id`, `user_id`, `motivo` e
  `observacao` de acordo com o movimento e o saldo persistidos

### Requirement: Falhas MUST preservar os invariantes entre saldo e ledger

Cada falha ou rejeicao MUST deixar saldo e movimentos inalterados em relacao ao estado
anterior. Operacoes confirmadas MUST preservar a igualdade entre saldo inicial, Entradas,
Saidas e movimentos correspondentes. Esta verificacao sequencial nao MUST ser considerada
prova de concorrencia ou de prevencao contra overselling, que esta fora do escopo academico
atual. A Change `seguranca-concorrencia-estoque` foi cancelada/adiada por depender de
recursos pagos do Xano; nenhuma protecao contra lost update ou overselling foi implementada
ou comprovada.

#### Scenario: Rejeicao sem escrita parcial
- **WHEN** uma operacao de Entrada ou Saida e rejeitada ou revertida
- **THEN** o saldo MUST permanecer igual ao anterior
- **AND** nenhum movimento MUST ser adicionado
