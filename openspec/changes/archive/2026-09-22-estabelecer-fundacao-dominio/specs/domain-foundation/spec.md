# Spec

## Purpose

Esta capability estabelece o contrato comportamental comum do Sistema de Gerenciamento de Estoque. Ela define o vocabulário, os relacionamentos e as garantias mínimas que devem ser respeitados pelas mudanças de autenticação, cadastros, estoque, histórico, dashboard e relatórios.

## Requirements

### Requirement: O sistema MUST usar um vocabulário canônico de domínio

O sistema MUST reconhecer como conceitos distintos Usuário, Perfil, Categoria, Produto, Fornecedor, Estoque e Movimentação de Estoque.

Uma movimentação MUST possuir exatamente um tipo entre entrada e saída, estar associada a exatamente um produto e a exatamente um usuário responsável.

Um produto MUST estar associado a uma categoria.

#### Scenario: Relacionamentos mínimos de um produto

- **WHEN** um produto é consultado pelo sistema
- **THEN** sua categoria e seu estado atual de estoque MUST poder ser identificados
- **AND** suas movimentações MUST poder ser relacionadas ao produto

#### Scenario: Entrada relacionada a fornecedor

- **WHEN** uma movimentação do tipo entrada possui fornecedor informado
- **THEN** o fornecedor MUST ser identificável na movimentação
- **AND** uma movimentação do tipo saída MUST NOT exigir fornecedor

### Requirement: O sistema MUST representar a situação atual do estoque de forma verificável

Para cada produto controlado, o sistema MUST permitir identificar a quantidade disponível, o nível mínimo configurado e uma situação derivada que distinga, no mínimo, estoque normal, estoque abaixo do mínimo e produto sem estoque.

#### Scenario: Produto sem estoque

- **WHEN** a quantidade disponível de um produto é igual a zero
- **THEN** sua situação MUST ser identificada como sem estoque

#### Scenario: Produto abaixo do mínimo

- **WHEN** a quantidade disponível é maior que zero e menor que o estoque mínimo configurado
- **THEN** sua situação MUST ser identificada como abaixo do estoque mínimo

#### Scenario: Produto em situação normal

- **WHEN** a quantidade disponível é maior ou igual ao estoque mínimo configurado e maior que zero
- **THEN** sua situação MUST ser identificada como estoque normal

### Requirement: Movimentações MUST preservar rastreabilidade e integridade

Toda movimentação confirmada MUST registrar seu tipo, produto, quantidade positiva, data e hora, usuário responsável e motivo.

A movimentação MUST registrar também os dados contextuais aplicáveis. A observação poderá ser registrada quando necessário e uma entrada poderá registrar o fornecedor associado.

Uma saída MUST NOT ser confirmada quando sua quantidade exceder a quantidade disponível.

Quando uma movimentação for rejeitada, nenhuma alteração correspondente no estoque ou no histórico de movimentações MUST permanecer confirmada.

#### Scenario: Movimentação sem responsável

- **WHEN** uma tentativa de registrar entrada ou saída não identifica um usuário responsável válido
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma alteração de estoque MUST ser confirmada

#### Scenario: Saída maior que o estoque disponível

- **WHEN** uma saída solicita quantidade maior que a quantidade disponível do produto
- **THEN** a operação MUST ser rejeitada com erro de regra de negócio
- **AND** a quantidade disponível MUST permanecer inalterada
- **AND** nenhuma movimentação confirmada MUST ser criada

#### Scenario: Movimentação com quantidade inválida

- **WHEN** uma entrada ou saída é informada com quantidade menor ou igual a zero
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma movimentação confirmada MUST ser criada
- **AND** nenhuma alteração de estoque MUST ser confirmada

### Requirement: A integração MUST comunicar sucesso e falha de forma distinguível

As operações consumidas pelo frontend MUST permitir distinguir resultados de sucesso de falhas de autenticação, autorização, validação e regras de negócio.

As respostas de erro MUST fornecer informação suficiente para que o frontend apresente o resultado ao usuário sem precisar reproduzir as regras internas do backend.

#### Scenario: Usuário não autenticado

- **WHEN** uma operação protegida é chamada sem uma credencial válida
- **THEN** o backend MUST rejeitar a chamada como não autenticada

#### Scenario: Usuário sem permissão

- **WHEN** uma operação é chamada por um usuário autenticado sem a permissão necessária
- **THEN** o backend MUST rejeitar a chamada como não autorizada
- **AND** o frontend MUST NOT obter sucesso apenas ocultando ou exibindo controles

#### Scenario: Erro de regra de negócio

- **WHEN** uma operação é rejeitada por uma regra de integridade do domínio
- **THEN** o backend MUST retornar uma resposta identificável como erro de negócio
- **AND** o frontend MUST poder exibir o erro sem inferir a causa a partir de texto livre