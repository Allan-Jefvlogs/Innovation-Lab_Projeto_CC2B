# Design

## Context

A fundação do domínio do Sistema de Gerenciamento de Estoque já consolidou os conceitos principais dos cadastros e das movimentações de estoque. A presente change estabelece o contrato funcional dos cadastros básicos de Categoria, Produto e Fornecedor, definindo os relacionamentos que sustentam o catálogo, o estoque e o histórico do sistema.

A arquitetura do projeto exige que o Reflex seja usado como frontend de apresentação e interação, enquanto o Xano seja a autoridade de integridade, regras de negócio e persistência. Esta change não deve introduzir regras técnicas de implementação nem substituir a separação de responsabilidades entre camada de apresentação e camada de negócio.

## Goals / Non-Goals

### Goals

- Definir o contrato funcional de categorias, produtos e fornecedores.
- Preservar a consistência entre Produto e Categoria.
- Definir que Produto deve ser rastreável em estoque e movimentações sem incorporar a regra operacional das movimentações em si.
- Reconhecer o Fornecedor como contexto relevante para entradas de estoque quando aplicável.
- Estabelecer critérios mínimos de criação, consulta, alteração, inativação e integridade histórica.
- Manter a separação clara entre cadastro básico, operação de estoque e autenticação/autorização.

### Non-Goals

- Implementar código ou lógica funcional fora do contrato de cadastro.
- Criar tabelas, schemas físicos, chaves, índices ou estruturas de banco.
- Definir endpoints, APIs concretas ou fluxos de interface.
- Determinar uma matriz final de permissões por perfil.
- Incorporar a regra operacional de entrada e saída de estoque neste contrato.
- Definir uma política definitiva de exclusão destrutiva antes da revisão do grupo.

## Decisions

### Cadastro básico deve ser tratado como contrato funcional, não como detalhe operacional

A change define o comportamento mínimo dos registros essenciais do sistema, incluindo criação, consulta, alteração, inativação e preservação de integridade. Essa definição será usada como base para futuras implementações e validações, mas não substitui a decisão técnica da implementação final.

**Alternativa considerada:** incorporar regras de operação de estoque, permissões detalhadas e tecnologia de persistência nesta mesma etapa. Essa alternativa foi rejeitada porque dilui o escopo e mistura responsabilidades distintas do domínio.

### Xano continuará sendo a autoridade de integridade e regras de negócio

Qualquer regra que garanta a validade de Produto, Categoria, Fornecedor e a preservação de integridade dos registros deverá ser aplicada no backend Xano. O Reflex deve consumir o resultado dessas regras, sem tentar substituir a validação no backend.

**Alternativa considerada:** aplicar regras de consistência apenas na interface. Essa alternativa foi rejeitada porque a apresentação não pode garantir integridade de dados nem impedir chamadas indevidas ou bypass do cliente.

### Produto deve manter vínculo explícito com Categoria e com o histórico do estoque

O contrato funcional deve exigir que Produto tenha uma Categoria válida para operação normal. Isso preserva a consistência do catálogo e evita que produtos sem suporte organizacional sejam utilizados como registros válidos em operações de negócio.

**Alternativa considerada:** permitir produto sem categoria válida como uma condição aceitável por default. Essa alternativa foi rejeitada porque compromete a rastreabilidade, a organização do catálogo e a consistência com estoque e movimentações.

### Produto inativo ou desabilitado deve ser tratado como estado de uso limitado

O estado do produto deve ser reconhecido como um fator de uso normal em estoque e movimentações, mas sem definir aqui a regra operacional detalhada dessas operações. Isso preserva o escopo da change e evita misturar a decisão de cadastro com a lógica de movimentação em si.

**Alternativa considerada:** definir regras completas de bloqueio e compensação de estoque dentro desta change. Essa alternativa foi rejeitada porque esse comportamento é da operação de movimentação e não do contrato de cadastro.

### Fornecedor deve ser tratado como relacionamento contextual

O fornecedor deve ser reconhecido como referência relevante para entradas de estoque quando aplicável, sem se transformar em requisito universal para todos os produtos e movimentações. Esse ajuste preserva a diferença entre catalogação básica e contexto funcional de compra e origem dos itens.

**Alternativa considerada:** exigir fornecedor obrigatório para qualquer produto ou movimentação. Essa alternativa foi rejeitada porque ela mistura o cadastro básico com regras de operação e não reflete a natureza contextual da relação.

### Preservação histórica deve preceder remoção destrutiva

Qualquer registro que já tenha sido utilizado em estoque ou movimentações não deve sofrer remoção destrutiva sem regra de negócio explicitamente definida. Essa regra preserva a rastreabilidade e evita perda de histórico e inconsistência de saldo e movimentações.

**Alternativa considerada:** permitir exclusão imediata de registros já relacionados. Essa alternativa foi rejeitada porque compromete a integridade histórica e a confiabilidade do domínio.

### Exclusão definitiva permanece como decisão pendente

A mudança registra que a exclusão definitiva dos registros não é um comportamento do contrato funcional atual. Essa decisão deve permanecer pendente para revisão do grupo, preservando o contrato funcional sem congelar a regra de negócio antes da análise adequada.

**Alternativa considerada:** definir uma política final de exclusão nesta change. Essa alternativa foi rejeitada porque existe risco de antecipar uma regra que depende de avaliação de impacto e de decisão de negócio mais ampla.

### Autenticação e autorização continuam sendo dependências do contrato, não parte do escopo funcional do cadastro

A capability de autenticação e autorização já consolidada permanece como dependência para qualquer operação de cadastro, consulta, inativação ou alteração. A change não redefine a matriz detalhada de permissões, mas exige que o estado do usuário e a autorização sejam respeitados por todas as ações do contrato funcional de cadastros básicos.

**Alternativa considerada:** reescrever a matriz detalhada de permissões dentro desta change. Essa alternativa foi rejeitada porque a arquitetura do projeto já separou o contrato de acesso e o contrato funcional de domínio.

## Risks / Trade-offs

- **[Risco]** A ausência de regras detalhadas de exclusão pode gerar dúvidas de decisão. **Mitigação:** a design mantém a integridade histórica como regra central e reconhece a exclusão definitiva como pendente.

- **[Risco]** O produto pode ser tratado sem categoria válida se a dependência não for reforçada. **Mitigação:** a design exige uma categoria válida para operação normal e reforça o vínculo entre catálogo e negócio.

- **[Risco]** O frontend pode interpretar o cadastro como regra final de negócio. **Mitigação:** a architecture boundary deixa claro que o Xano é o responsável pela integridade e decisão final.

- **[Risco]** O fornecedor pode ser tratado como requisito universal. **Mitigação:** a design reconhece sua natureza contextual e dependente da operação de entrada de estoque.

- **[Trade-off]** Adiar a política de exclusão definitiva reduz a chance de decisões prematuras, mas exige que a implementação futura retorne ao tema com a análise de impacto correta. **Mitigação:** a design explicitamente marca essa decisão como pendente e não definitiva.

## Architecture Boundaries

- **Reflex:** apresentar os registros, permitir interação do usuário e consumir os resultados do backend sem reproduzir regras de negócio.
- **Xano:** validar integridade, aplicar regras de relacionamento, proteger registros em uso, e decidir sobre criação, atualização, inativação e preservação histórica.
- **OpenSpec:** manter o contrato funcional coerente entre a fundação do domínio, os cadastros básicos e as capabilities futuras de estoque, relatórios e dashboard.

A change não deve criar estrutura física, modelagem de banco, endpoints ou telas. Seu papel funcional é estabelecer uma base verificável para a implementação posterior, preservando a separação entre cadastro básico, operação de estoque e autenticação/autorização.
