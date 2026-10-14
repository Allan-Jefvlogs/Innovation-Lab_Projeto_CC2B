# Specification: Segurança de concorrência do estoque

## ADDED Requirements

### Requirement: Operações concorrentes MUST preservar saldo e movimentações

As operações backend de Entrada e Saída para um mesmo Produto MUST impedir que atualizações
concorrentes percam saldo ou confirmem saídas acima da quantidade disponível. A alteração do
saldo e a criação do movimento MUST permanecer atômicas para cada operação. O mecanismo
MUST ser suportado pela instância Xano e validado em runtime antes de a proteção ser
declarada implementada. O uso de db.transaction sem prova adicional MUST NOT ser considerado
garantia de serialização.

#### Scenario: Duas saídas simultâneas disputam saldo insuficiente para ambas

- **WHEN** o saldo inicial é 5 e duas requisições simultâneas solicitam saída de 4 cada
- **THEN** no máximo uma saída MUST ser confirmada
- **AND** se uma saída for confirmada, o saldo final MUST ser 1
- **AND** deve existir somente o movimento da saída confirmada
- **AND** a soma dos movimentos confirmados MUST corresponder à redução líquida do saldo

#### Scenario: Entrada e saída simultâneas do mesmo Produto

- **WHEN** uma Entrada e uma Saída são processadas simultaneamente para o mesmo Produto
- **THEN** o saldo final MUST corresponder à soma algébrica das operações confirmadas
- **AND** cada operação confirmada MUST possuir seu movimento correspondente
- **AND** nenhuma operação rejeitada MUST deixar escrita parcial

#### Scenario: Falha após uma escrita da operação

- **WHEN** uma falha ocorre depois da atualização de saldo e antes da gravação do movimento
- **THEN** a operação MUST reverter a alteração parcial
- **AND** o saldo e o ledger MUST permanecer consistentes
