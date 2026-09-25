# fundacao-tecnica-cadastros Specification

## Purpose

Esta capability define os requisitos verificáveis para criar no Xano a fundação física de persistência de Categoria, Produto e Fornecedor. A criação das estruturas ocorrerá somente no Apply aprovado; esta specification não autoriza alterações durante Explore, Proposal ou Review.

## Requirements

### Requirement: O sistema MUST possuir estruturas persistentes distintas para Categoria, Produto e Fornecedor

A fundação técnica MUST representar Categoria, Produto e Fornecedor como entidades persistidas distintas, sem reutilizar automaticamente entidades de quick-start ou de outro domínio.

#### Scenario: Entidades de cadastro disponíveis

- **WHEN** a fundação técnica for aplicada ao Xano
- **THEN** Categoria, Produto e Fornecedor MUST possuir estruturas persistentes próprias
- **AND** nenhuma dessas entidades MUST depender semanticamente de uma estrutura de outro domínio apenas por conveniência de nomenclatura

#### Scenario: Estrutura ausente

- **WHEN** uma das três entidades não possuir estrutura persistente correspondente após o Apply
- **THEN** a fundação MUST ser considerada incompleta
- **AND** a implementação das operações de cadastro MUST permanecer impedida

### Requirement: Cada registro MUST possuir identificação estável

Categoria, Produto e Fornecedor MUST possuir uma identificação persistente estável, capaz de ser usada nas referências e consultas futuras.

A identificação MUST permanecer preservada enquanto o registro possuir referências válidas no domínio.

#### Scenario: Registro identificado

- **WHEN** um registro de Categoria, Produto ou Fornecedor for persistido
- **THEN** o registro MUST possuir uma identificação estável
- **AND** essa identificação MUST poder ser usada para relacionar o registro às futuras operações de domínio

#### Scenario: Registro referenciado

- **WHEN** um registro já estiver relacionado a Produto, Estoque, Movimentação ou entrada de estoque
- **THEN** sua identificação MUST permanecer disponível para preservar as referências históricas e funcionais

### Requirement: As entidades de cadastro MUST suportar estado ativo ou inativo

Categoria, Produto e Fornecedor MUST possuir uma representação persistente de estado compatível com ativo e inativo.

A representação de inatividade MUST ser distinta da remoção física do registro.

#### Scenario: Registro inativado

- **WHEN** um registro de Categoria, Produto ou Fornecedor for inativado
- **THEN** seu estado MUST poder ser identificado como inativo
- **AND** o registro MUST permanecer disponível para preservar referências existentes

#### Scenario: Registro ativo

- **WHEN** um registro possuir estado ativo
- **THEN** seu estado MUST poder ser identificado como ativo
- **AND** a futura operação de cadastro MUST poder avaliar esse estado sem depender de texto livre

### Requirement: Produto MUST possuir referência persistente a Categoria

A estrutura persistente de Produto MUST manter uma referência à Categoria correspondente.

A relação MUST permitir validar que o Produto possui Categoria válida para operação normal, conforme a specification de cadastros básicos.

#### Scenario: Produto relacionado a Categoria

- **WHEN** um Produto for persistido com uma Categoria válida
- **THEN** a relação Produto–Categoria MUST poder ser identificada
- **AND** a referência MUST permanecer disponível para futuras consultas e operações de cadastro

#### Scenario: Produto sem Categoria válida

- **WHEN** a estrutura de Produto não puder identificar uma Categoria válida
- **THEN** a persistência MUST rejeitar ou impedir o estado inválido conforme a regra de integridade aprovada
- **AND** o Produto MUST não ser considerado apto para operação normal

### Requirement: A fundação MUST preservar referências futuras de Produto para Estoque e Movimentação

A estrutura persistente de Produto MUST permitir que futuras estruturas de Estoque e Movimentação se relacionem ao Produto sem exigir alteração destrutiva da identificação ou da entidade de Produto.

Esta capability MUST NOT criar a estrutura de Estoque ou Movimentação.

#### Scenario: Referência futura ao Produto

- **WHEN** uma futura estrutura de Estoque ou Movimentação precisar referenciar um Produto
- **THEN** a identificação persistente do Produto MUST estar disponível para essa relação
- **AND** a fundação de Produto MUST não exigir duplicação da identidade do cadastro

#### Scenario: Produto já utilizado

- **WHEN** um Produto possuir referências futuras ou históricas
- **THEN** sua estrutura e identificação MUST permanecer compatíveis com a preservação dessas referências
- **AND** a inativação MUST ser preferida à remoção destrutiva enquanto a política de exclusão não estiver definida

### Requirement: A fundação MUST preservar a relação contextual de Fornecedor com entradas

A estrutura persistente de Fornecedor MUST permitir que futuras entradas de estoque o referenciem quando esse contexto for aplicável.

A fundação MUST NOT criar uma relação que transforme Fornecedor em requisito universal de Produto ou de toda movimentação.

#### Scenario: Fornecedor relacionado a entrada

- **WHEN** uma futura entrada de estoque possuir Fornecedor aplicável
- **THEN** a identificação persistente do Fornecedor MUST poder ser referenciada pela entrada
- **AND** a relação MUST permanecer contextual à entrada

#### Scenario: Operação sem Fornecedor

- **WHEN** uma futura operação não exigir Fornecedor
- **THEN** a ausência dessa referência MUST continuar representável
- **AND** a estrutura de Fornecedor MUST não impedir a operação por ausência de relação universal

### Requirement: A fundação MUST preservar integridade referencial e histórica

As relações persistentes entre Produto e Categoria devem impedir referências inválidas conforme as regras aprovadas. Categoria, Produto e Fornecedor já utilizados MUST permanecer identificáveis para preservar histórico e referências futuras.

A fundação MUST NOT introduzir exclusão destrutiva incompatível com registros já utilizados.

#### Scenario: Registro com referência existente

- **WHEN** uma Categoria, Produto ou Fornecedor já possuir referência válida no domínio
- **THEN** a fundação MUST preservar a identificação do registro
- **AND** a remoção física MUST ser impedida ou condicionada à regra de negócio explicitamente aprovada

#### Scenario: Relação inválida

- **WHEN** uma referência persistente apontar para registro inexistente ou incompatível
- **THEN** a operação de persistência MUST ser rejeitada
- **AND** nenhum estado referencial inválido MUST ser confirmado

### Requirement: A fundação MUST ser compatível com autenticação e autorização

As estruturas persistentes MUST permitir que futuras operações de cadastro sejam protegidas pelo contrato de autenticação e autorização, sem incorporar a matriz detalhada de permissões nesta capability.

O Xano MUST permanecer como autoridade para validar identidade, autorização e integridade das operações futuras.

#### Scenario: Operação futura protegida

- **WHEN** uma futura operação de cadastro for executada por usuário não autenticado ou não autorizado
- **THEN** o backend MUST poder rejeitar a operação sem depender da interface Reflex
- **AND** a estrutura persistente MUST não ser usada para contornar a autorização

#### Scenario: Identidade e contexto

- **WHEN** a implementação futura precisar aplicar autorização ou rastreabilidade
- **THEN** a fundação MUST permanecer compatível com a identidade e o contexto definidos pelo backend
- **AND** esta change MUST não criar novos perfis ou permissões específicas

### Requirement: A fundação MUST ser compatível com futuras operações de backend

As estruturas persistentes MUST ser suficientes para sustentar futuramente as operações de criação, consulta, alteração e inativação de Categoria, Produto e Fornecedor, sem incluir essas operações nesta change.

#### Scenario: Operações futuras de cadastro

- **WHEN** as operações de backend forem implementadas em change posterior
- **THEN** as estruturas MUST permitir consultar o estado, alterar o estado permitido e preservar as relações válidas
- **AND** a implementação futura MUST poder aplicar as regras funcionais dos cadastros básicos

#### Scenario: Apply fora do escopo atual

- **WHEN** a etapa atual for Explore, Proposal ou Review
- **THEN** nenhuma estrutura física MUST ser criada ou alterada
- **AND** a criação física MUST ocorrer somente no Apply após aprovação