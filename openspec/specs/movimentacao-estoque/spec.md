# Spec

## Purpose
Esta capability estabelece o contrato funcional das movimentações de estoque do Sistema de Gerenciamento de Estoque. Ela define o comportamento observável de entradas, saídas, atualização conceitual do saldo, histórico, rastreabilidade, rejeições e relação com o estoque mínimo, sem definir implementação física ou regras detalhadas de consulta gerencial.

## Requirements

### Requirement: O sistema MUST tratar entrada e saída como tipos de uma movimentação comum

Toda movimentação de estoque MUST possuir exatamente um tipo entre entrada e saída, estar relacionada a um Produto e identificar um usuário responsável.

#### Scenario: Movimentação com tipo válido

- **WHEN** uma movimentação de estoque for confirmada
- **THEN** seu tipo MUST ser identificável como entrada ou saída
- **AND** o Produto relacionado MUST ser identificável
- **AND** o usuário responsável MUST ser identificável

#### Scenario: Movimentação sem tipo único

- **WHEN** uma operação não identificar exatamente um tipo de movimentação entre entrada e saída
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma alteração confirmada no estoque MUST permanecer
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

### Requirement: O sistema MUST exigir um Produto relacionado à movimentação

Toda movimentação confirmada MUST estar relacionada a um Produto existente no domínio.

O Produto relacionado MUST possuir Categoria, conforme o contrato dos cadastros básicos, e a movimentação MUST preservar a relação entre Produto, Estoque e histórico. Produto inativo ou desabilitado MUST NOT ser utilizado normalmente em operações de estoque; os critérios exatos para esse tratamento permanecem pendentes.

#### Scenario: Movimentação relacionada a Produto

- **WHEN** uma entrada ou saída for confirmada
- **THEN** o Produto relacionado MUST poder ser identificado
- **AND** a movimentação MUST poder ser associada ao estado de estoque do Produto
- **AND** a movimentação MUST poder ser associada ao histórico do Produto

#### Scenario: Produto não identificável

- **WHEN** uma tentativa de movimentação não identificar um Produto válido
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma alteração confirmada no estoque MUST permanecer
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

#### Scenario: Produto inativo ou desabilitado

- **WHEN** uma tentativa de movimentação utilizar Produto inativo ou desabilitado
- **THEN** o Produto MUST ser identificado como não adequado para uso normal em operações de estoque
- **AND** o tratamento operacional específico MUST permanecer dependente das regras ainda pendentes do grupo

### Requirement: O sistema MUST aceitar somente quantidade positiva

A quantidade informada para uma entrada ou saída MUST ser maior que zero.

Este requisito define a validade conceitual da quantidade, sem definir unidade, escala ou precisão física.

#### Scenario: Quantidade positiva

- **WHEN** uma entrada ou saída for informada com quantidade maior que zero
- **THEN** a quantidade MUST ser considerada válida para a avaliação da movimentação

#### Scenario: Quantidade inválida

- **WHEN** uma entrada ou saída for informada com quantidade menor ou igual a zero
- **THEN** a operação MUST ser rejeitada
- **AND** o saldo confirmado MUST permanecer inalterado
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

### Requirement: O sistema MUST exigir usuário responsável autenticado e autorizado

Toda movimentação confirmada MUST identificar o usuário responsável pela operação. A operação MUST estar sujeita à autenticação e à autorização definidas pela capability consolidada de autenticação e autorização.

A decisão de autorização MUST ser aplicada no backend, sem depender apenas da apresentação do Reflex.

#### Scenario: Usuário responsável válido

- **WHEN** uma entrada ou saída for solicitada por um usuário autenticado e autorizado
- **THEN** a identidade do usuário MUST ser associada à movimentação confirmada
- **AND** essa identidade MUST permanecer identificável no histórico

#### Scenario: Usuário ausente ou não autorizado

- **WHEN** uma operação de entrada ou saída não identificar usuário autenticado e autorizado
- **THEN** o backend MUST rejeitar a operação
- **AND** nenhuma alteração confirmada no estoque MUST permanecer
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

### Requirement: O sistema MUST registrar o motivo da movimentação confirmada

Toda movimentação confirmada MUST registrar o motivo da operação, conforme a regra já consolidada na fundação do domínio.

A obrigatoriedade do motivo não deve ser substituída por texto livre de erro nem por decisão exclusiva da interface.

#### Scenario: Movimentação com motivo

- **WHEN** uma entrada ou saída atender às demais condições de confirmação e possuir motivo identificável
- **THEN** o motivo MUST permanecer associado à movimentação confirmada
- **AND** o motivo MUST poder ser consultado junto ao histórico da operação

#### Scenario: Movimentação sem motivo

- **WHEN** uma tentativa de confirmar uma movimentação não possuir motivo identificável
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma alteração confirmada no estoque MUST permanecer
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

### Requirement: O sistema MUST tratar observação como dado contextual quando aplicável

O sistema MUST permitir que uma movimentação registre observação quando esse contexto for fornecido, sem estabelecer a obrigatoriedade da observação para toda entrada ou saída.

#### Scenario: Movimentação com observação

- **WHEN** uma movimentação confirmada possuir uma observação
- **THEN** a observação MUST permanecer associada à movimentação
- **AND** a observação MUST poder ser identificada junto aos demais dados históricos da operação

#### Scenario: Movimentação sem observação

- **WHEN** uma movimentação confirmada não possuir observação
- **THEN** a ausência de observação MUST não impedir a confirmação por si só
- **AND** os demais dados obrigatórios MUST permanecer identificáveis

### Requirement: O sistema MUST tratar Fornecedor como contexto das entradas quando aplicável

Uma entrada de estoque poderá estar associada a um Fornecedor quando esse contexto for aplicável. Fornecedor MUST NOT ser requisito universal para toda movimentação, e uma saída MUST NOT exigir Fornecedor.

#### Scenario: Entrada com Fornecedor

- **WHEN** uma entrada de estoque for confirmada com Fornecedor aplicável
- **THEN** o Fornecedor MUST permanecer identificável como contexto da entrada
- **AND** a entrada MUST continuar relacionada ao Produto e ao usuário responsável

#### Scenario: Operação sem Fornecedor obrigatório

- **WHEN** uma movimentação não exigir Fornecedor pelo seu contexto
- **THEN** a ausência de Fornecedor MUST não impedir a confirmação por si só
- **AND** uma saída MUST poder ser avaliada sem exigir Fornecedor

### Requirement: O sistema MUST atualizar conceitualmente o saldo após confirmação

Uma entrada confirmada MUST aumentar a quantidade disponível do Produto. Uma saída confirmada MUST reduzir a quantidade disponível do Produto.

A atualização conceitual do saldo MUST ocorrer somente para movimentações confirmadas.

#### Scenario: Entrada confirmada

- **WHEN** uma entrada for confirmada
- **THEN** a quantidade disponível do Produto MUST aumentar pela quantidade da entrada
- **AND** a movimentação confirmada MUST permanecer registrada no histórico

#### Scenario: Saída confirmada

- **WHEN** uma saída for confirmada
- **THEN** a quantidade disponível do Produto MUST reduzir pela quantidade da saída
- **AND** a movimentação confirmada MUST permanecer registrada no histórico

### Requirement: O sistema MUST impedir saldo negativo

Uma saída MUST NOT ser confirmada quando sua quantidade exceder a quantidade disponível do Produto.

A confirmação de uma saída MUST NOT produzir quantidade disponível negativa.

#### Scenario: Saída dentro do saldo disponível

- **WHEN** uma saída solicitar quantidade inferior à quantidade disponível
- **THEN** a operação MUST poder prosseguir para avaliação das demais regras de confirmação
- **AND** a quantidade disponível MUST permanecer não negativa após a aplicação da saída

#### Scenario: Saída acima do saldo disponível

- **WHEN** uma saída solicitar quantidade maior que a quantidade disponível
- **THEN** a operação MUST ser rejeitada como regra de negócio
- **AND** a quantidade disponível MUST permanecer inalterada
- **AND** nenhuma movimentação confirmada MUST ser criada no histórico

### Requirement: O sistema MUST registrar no histórico somente movimentações confirmadas

Cada movimentação confirmada MUST permanecer identificável por tipo, Produto, quantidade, data e hora, usuário responsável e motivo, além dos dados contextuais aplicáveis.

O histórico MUST preservar a relação da movimentação com o Produto, o usuário e, quando aplicável, o Fornecedor da entrada.

#### Scenario: Registro histórico de movimentação confirmada

- **WHEN** uma entrada ou saída for confirmada
- **THEN** o histórico MUST permitir identificar o tipo da movimentação
- **AND** o Produto, a quantidade, o usuário responsável, a data e hora e o motivo MUST permanecer identificáveis
- **AND** o Fornecedor MUST ser identificável quando aplicável à entrada

#### Scenario: Tentativa rejeitada

- **WHEN** uma entrada ou saída for rejeitada
- **THEN** nenhuma movimentação confirmada MUST ser criada no histórico
- **AND** registros históricos confirmados anteriormente MUST permanecer preservados

### Requirement: O sistema MUST manter a integridade entre confirmação, saldo e histórico

Uma operação rejeitada MUST NOT confirmar alteração no saldo nem criar movimentação confirmada no histórico. Uma movimentação confirmada MUST permanecer relacionada ao estado de estoque e ao histórico do Produto.

A estratégia técnica para transação, concorrência e persistência permanece fora desta specification e deve ser definida em etapa apropriada.

#### Scenario: Rejeição sem efeito confirmado

- **WHEN** uma operação falhar por autenticação, autorização, validação ou regra de negócio
- **THEN** o saldo confirmado MUST permanecer inalterado
- **AND** nenhuma movimentação confirmada MUST ser criada
- **AND** o frontend MUST poder distinguir a falha sem reproduzir a regra do backend

#### Scenario: Confirmação com rastreabilidade

- **WHEN** uma movimentação for confirmada
- **THEN** a alteração conceitual do saldo MUST corresponder ao tipo e à quantidade da movimentação
- **AND** o registro histórico MUST permanecer relacionado ao Produto

### Requirement: O sistema MUST relacionar o estoque mínimo à situação do estoque

A situação do estoque MUST considerar a quantidade disponível e o estoque mínimo definido para o Produto.

A movimentação deve atualizar conceitualmente o saldo que fundamenta essa situação, sem incorporar dashboard ou relatórios gerenciais nesta capability.

#### Scenario: Saldo abaixo do estoque mínimo

- **WHEN** a quantidade disponível de um Produto estiver maior que zero e menor que seu estoque mínimo
- **THEN** a situação do estoque MUST ser identificada como abaixo do estoque mínimo

#### Scenario: Saldo sem estoque

- **WHEN** a quantidade disponível de um Produto for igual a zero
- **THEN** a situação do estoque MUST ser identificada como sem estoque

#### Scenario: Saldo em situação normal

- **WHEN** a quantidade disponível de um Produto for maior ou igual ao estoque mínimo e maior que zero
- **THEN** a situação do estoque MUST ser identificada como estoque normal

### Requirement: O sistema MUST manter a separação de responsabilidades da arquitetura

O Xano MUST permanecer como autoridade para validação, integridade, confirmação ou rejeição da movimentação e estado do estoque. O Reflex MUST atuar como camada de apresentação e interação, sem ser mecanismo suficiente de segurança ou integridade. O OpenSpec MUST manter o contrato funcional e o Git MUST manter o versionamento do projeto.

#### Scenario: Backend como autoridade

- **WHEN** uma operação de movimentação for solicitada
- **THEN** a decisão final sobre autenticação, autorização, validação, integridade e confirmação MUST ser tomada pelo backend
- **AND** o frontend MUST apresentar o resultado recebido sem substituir essa decisão

#### Scenario: Cliente sem autorização

- **WHEN** uma operação for chamada por cliente sem autorização válida
- **THEN** o backend MUST rejeitar a operação
- **AND** a ocultação ou exibição de controles no frontend MUST NOT produzir sucesso por si só
