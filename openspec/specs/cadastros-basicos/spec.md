# Spec

## Purpose

Esta capability estabelece o contrato funcional dos cadastros básicos do Sistema de Gerenciamento de Estoque: Categoria, Produto e Fornecedor. Ela define os relacionamentos mínimos com o estoque e o histórico de movimentações, sem incorporar a lógica operacional de movimentação de estoque nem a definição detalhada de permissões por perfil.

## Requirements

### Requirement: O sistema MUST manter um contrato funcional claro para Categoria

O sistema MUST reconhecer Categoria como um registro funcional do domínio, vinculado ao conjunto de produtos do sistema e ao agrupamento de itens relevantes para a organização do catálogo.

A Categoria MUST poder ser criada, consultada, alterada e inativada conforme o ciclo funcional do cadastro básico, sem que isso transforme a categoria em mecanismo de operação de estoque.

#### Scenario: Categoria em uso no catálogo

- **WHEN** uma Categoria estiver associada a produtos válidos no sistema
- **THEN** o sistema MUST preservar essa associação como parte do catálogo funcional do domínio
- **AND** a remoção destrutiva da categoria MUST ser impedida quando essa remoção comprometer a integridade do catálogo sem regra de negócio explicitamente definida

#### Scenario: Categoria em mudança de estado

- **WHEN** uma Categoria for alterada ou inativada
- **THEN** o sistema MUST manter a consistência do cadastro e do relacionamento com Produto
- **AND** o status da categoria MUST permanecer verificável para as operações do sistema que dependam desse registro

### Requirement: O sistema MUST manter Produto dependente de Categoria válida para operação normal

Produto MUST possuir uma Categoria válida para operação normal no sistema.

A dependência entre Produto e Categoria MUST ser tratada como parte do contrato funcional do domínio e não como requisito opcional ou apenas de apresentação.

#### Scenario: Produto criado sem categoria válida

- **WHEN** uma operação de criação ou atualização de Produto não identificar uma Categoria válida
- **THEN** o sistema MUST rejeitar a operação como inadequada para a integridade do domínio
- **AND** o Produto MUST permanecer sem um estado válido de operação normal

#### Scenario: Produto em operação normal

- **WHEN** um Produto estiver ativo e associado a uma Categoria válida
- **THEN** o sistema MUST permitir que o Produto seja usado como referência válida em contexto de catálogo, estoque e movimentações
- **AND** o vínculo com a Categoria MUST permanecer verificável pelo sistema

### Requirement: O sistema MUST reconhecer o estado de Produto como fator de uso em estoque

Produto MUST possuir um estado funcional que permita distinguir registros ativos e registros inativos ou desabilitados, sem definir aqui a lógica operacional detalhada das movimentações.

Produto inativo ou desabilitado MUST NOT ser utilizado normalmente em operações de estoque, sem que esta change determine a regra operacional específica dessas operações.

#### Scenario: Produto inativo

- **WHEN** um Produto for marcado como inativo ou desabilitado
- **THEN** o sistema MUST registrar esse estado como condição de uso limitado
- **AND** o Produto MUST permanecer identificado como não adequado para uso normal em operações de estoque

#### Scenario: Produto ativo

- **WHEN** um Produto estiver ativo e compatível com o catálogo do sistema
- **THEN** o sistema MUST reconhecê-lo como candidato normal para uso em contexto de estoque e movimentação, respeitando as regras operacionais futuras

### Requirement: O sistema MUST tratar o relacionamento Produto–Estoque como dependência funcional do cadastro

O relacionamento entre Produto e Estoque MUST ser reconhecido como parte do contrato funcional do sistema.

Esse relacionamento MUST permitir que a situação atual do Produto e seu uso em estoque sejam identificados, sem incorporar a lógica de cálculo detalhada da operação de entrada e saída.

#### Scenario: Produto associado ao estoque

- **WHEN** um Produto estiver vinculado ao sistema de estoque
- **THEN** o sistema MUST permitir identificar sua associação com o estoque atual
- **AND** esse vínculo MUST permanecer coerente com a categoria e o estado do Produto

#### Scenario: Produto sem uso em estoque

- **WHEN** um Produto ainda não tiver associação funcional de estoque
- **THEN** o sistema MUST manter esse estado como condição válida do cadastro
- **AND** a ausência de vínculo em estoque MUST permanecer identificável na consulta do Produto

### Requirement: O sistema MUST tratar o relacionamento Produto–Movimentação como base de rastreabilidade

O relacionamento entre Produto e Movimentação de Estoque MUST ser preservado como requisito funcional do domínio.

As movimentações de estoque registradas no domínio MUST poder ser relacionadas ao Produto correspondente, e o histórico de movimentações MUST permanecer rastreável sem incorporar a lógica operacional de entrada e saída nesta change.

#### Scenario: Movimentação relacionada a Produto

- **WHEN** uma movimentação for registrada ou consultada
- **THEN** o sistema MUST permitir identificar o Produto relacionado
- **AND** o histórico de movimentações MUST permanecer associado ao Produto sem perder a integridade do registro

#### Scenario: Produto sem histórico

- **WHEN** um Produto ainda não possuir movimentações registradas
- **THEN** o sistema MUST manter esse estado como condição válida do cadastro
- **AND** o sistema MUST continuar a permitir consulta e manutenção do Produto sem depender de históricos inexistentes

### Requirement: O sistema MUST tratar Fornecedor como contexto aplicável às entradas de estoque

Fornecedor MUST ser reconhecido como parte do contrato de domínio quando a operação de entrada de estoque exigir esse contexto.

Fornecedor MUST NOT ser tratado como um requisito universal para todos os produtos, todas as movimentações ou todos os registros do sistema. A associação de Fornecedor deve ser contextual e aplicável conforme a necessidade do domínio.

#### Scenario: Entrada de estoque com fornecedor

- **WHEN** uma entrada de estoque for associada a um fornecedor aplicável
- **THEN** o sistema MUST manter essa referência como contexto relevante da operação
- **AND** a referência ao fornecedor MUST ser verificável sem transformar o fornecedor em requisito obrigatório para outros tipos de operação

#### Scenario: Movimentação sem fornecedor

- **WHEN** uma movimentação não exigir fornecedor
- **THEN** o sistema MUST tratá-la como válida conforme a regra do contexto operacional
- **AND** a ausência de fornecedor MUST não ser interpretada como falha do cadastro básico quando esse contexto não for aplicável

### Requirement: O sistema MUST manter um ciclo funcional mínimo para Categoria, Produto e Fornecedor

Categoria, Produto e Fornecedor MUST admitir, pelo menos, os seguintes comportamentos funcionais mínimos:

- criação;
- consulta;
- alteração;
- inativação.

A definição desses ciclos MUST ser mantida como contrato funcional do domínio e não como regra de implementação física específica.

#### Scenario: Criação de registro

- **WHEN** um novo registro do domínio for criado
- **THEN** o registro MUST poder ser consultado após a criação
- **AND** seu estado MUST poder ser identificado
- **AND** seus vínculos válidos MUST permanecer preservados
- **AND** a criação MUST respeitar a consistência do domínio, incluindo a validade da Categoria quando aplicável

#### Scenario: Consulta de registro

- **WHEN** um cadastro for consultado
- **THEN** o sistema MUST permitir a consulta do estado do registro e dos vínculos relevantes com o domínio
- **AND** a consulta MUST permanecer coerente com a integridade do catálogo, do estoque e do histórico

#### Scenario: Alteração de registro

- **WHEN** um cadastro for alterado
- **THEN** o novo estado do registro MUST poder ser identificado
- **AND** os vínculos válidos do registro MUST permanecer preservados
- **AND** a alteração MUST ser rejeitada quando comprometer a consistência do domínio sem regra de negócio explicitamente definida

#### Scenario: Inativação de registro

- **WHEN** um cadastro for inativado
- **THEN** o sistema MUST reconhecê-lo como registro desabilitado para uso normal
- **AND** a inativação MUST não substituir a regra de preservação da integridade histórica das operações já registradas

### Requirement: O sistema MUST preservar a integridade histórica dos registros já utilizados

Registros de Categoria e Produto que já tenham sido utilizados em estoque ou movimentações MUST preservar sua integridade histórica. Um Fornecedor já utilizado MUST preservar sua integridade histórica quando estiver associado a uma entrada de estoque.

A remoção destrutiva de registros já utilizados em estoque ou movimentações MUST ser proibida sem regra de negócio explicitamente definida.

#### Scenario: Registro em uso em estoque

- **WHEN** um registro já estiver relacionado a estoque ou movimentações do sistema
- **THEN** o sistema MUST impedir remoção destrutiva sem regra de negócio definida
- **AND** a preservação histórica MUST continuar como prioridade antes da exclusão definitiva

#### Scenario: Registro inativado e não removido

- **WHEN** um registro for inativado em vez de removido
- **THEN** o sistema MUST manter o registro como desabilitado sem perder a rastreabilidade do histórico
- **AND** o status inativo MUST permanecer verificável para futuras operações
