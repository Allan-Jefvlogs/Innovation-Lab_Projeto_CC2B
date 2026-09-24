# Design

## Context

A fundação do domínio consolidou Produto, Estoque e Movimentação de Estoque, incluindo os tipos entrada e saída, a identificação do usuário responsável, a quantidade positiva, a impossibilidade de saída acima do saldo disponível e a preservação do estado confirmado quando uma operação é rejeitada.

As capabilities de autenticação/autorização e cadastros básicos fornecem as dependências para proteger a operação e validar Produto, Categoria e Fornecedor. Esta change transforma essas decisões consolidadas em um contrato funcional específico para movimentações, sem implementar persistência, endpoints, telas ou regras técnicas do Xano.

## Goals / Non-Goals

### Goals

- Definir um contrato observável para entradas e saídas de estoque.
- Preservar os invariantes de tipo, Produto, quantidade positiva e usuário responsável.
- Definir a atualização conceitual do saldo após confirmação.
- Impedir saldo negativo e saídas acima do saldo disponível.
- Preservar o histórico das movimentações confirmadas.
- Manter Fornecedor como relação contextual das entradas.
- Relacionar o saldo à situação do estoque e ao estoque mínimo.
- Preservar as fronteiras entre contrato funcional, Xano, Reflex, consultas e capabilities gerenciais futuras.

### Non-Goals

- Implementar código ou XanoScript.
- Criar tabelas, schemas, campos físicos, chaves, endpoints ou APIs.
- Criar telas ou alterar o frontend Reflex.
- Definir transações, concorrência, persistência ou implantação.
- Definir matriz detalhada de permissões ou novos perfis.
- Redefinir autenticação, cadastros básicos, gestão de usuários, dashboard ou relatórios.
- Definir política de correção, cancelamento, estorno, imutabilidade ou auditoria de rejeições.

## Decisions

### Entrada e saída são tipos de uma movimentação comum

Entrada e saída compartilham a identidade de uma movimentação, a relação com Produto, quantidade positiva, usuário responsável, motivo e rastreabilidade. O tipo determina o efeito conceitual no saldo: entrada aumenta e saída reduz.

**Alternativa considerada:** tratar entrada e saída como contratos sem conceito comum. Essa alternativa foi rejeitada porque duplicaria invariantes e dificultaria a rastreabilidade histórica.

### A confirmação é o limite entre tentativa e alteração do estado

Somente uma movimentação confirmada pode alterar conceitualmente o saldo e aparecer como movimentação confirmada no histórico. Uma tentativa rejeitada não confirma saldo nem histórico.

**Alternativa considerada:** registrar tentativas rejeitadas como movimentações confirmadas. Essa alternativa foi rejeitada porque confundiria eventos válidos com operações não aceitas e comprometeria o histórico operacional.

### Produto é a referência central da operação

Toda movimentação deve estar relacionada a Produto. A relação do Produto com Categoria, Estoque e histórico de movimentações é preservada pelas capabilities consolidadas. Esta change não recria manutenção de cadastros nem define todos os critérios ainda pendentes sobre Produto inativo ou Categoria inativa.

**Alternativa considerada:** permitir movimentação sem Produto identificado. Essa alternativa foi rejeitada porque impediria atribuir saldo e histórico a um item do domínio.

### Fornecedor permanece contextual às entradas

Fornecedor pode contextualizar uma entrada quando aplicável, mas não é requisito universal e não é exigido por uma saída. A obrigatoriedade em tipos específicos de entrada e o uso de Fornecedor inativo permanecem pendentes.

**Alternativa considerada:** exigir Fornecedor em todas as movimentações. Essa alternativa foi rejeitada porque contradiz o domínio consolidado.

### O saldo atual e o histórico são resultados relacionados, mas conceitualmente distintos

O saldo representa o estado atual da disponibilidade do Produto. O histórico representa as movimentações confirmadas que explicam alterações nesse estado. A Specification exige coerência observável entre ambos, mas não escolhe estratégia física de transação, persistência ou concorrência.

**Alternativa considerada:** tratar o histórico como simples cópia do saldo. Essa alternativa foi rejeitada porque perderia a rastreabilidade dos eventos individuais.

### Motivo é obrigatório; observação é contextual

O motivo integra o registro obrigatório da movimentação confirmada por decisão já consolidada na fundação do domínio. A observação pode acompanhar a movimentação quando fornecida, mas sua obrigatoriedade permanece pendente.

**Alternativa considerada:** tornar motivo e observação igualmente opcionais. Essa alternativa foi rejeitada para o motivo porque conflitaria com a specification consolidada; não foi aplicada à observação porque essa decisão ainda não está consolidada.

### O estoque mínimo fundamenta a situação do estoque

A movimentação atualiza conceitualmente o saldo, e a situação do estoque é derivada da relação entre saldo disponível e estoque mínimo. Dashboard e relatórios apenas consumirão essas informações em capabilities futuras.

**Alternativa considerada:** calcular indicadores gerenciais dentro da movimentação. Essa alternativa foi rejeitada porque ampliaria o escopo para dashboard e relatórios.

### A arquitetura mantém o Xano como autoridade

O Xano será responsável futuramente por validar, confirmar ou rejeitar operações, preservar integridade e controlar o estado do estoque. O Reflex apresentará estados, enviará informações e exibirá resultados, sem substituir a segurança ou as regras do backend. OpenSpec mantém o contrato e Git mantém o versionamento.

**Alternativa considerada:** permitir que a interface decida autorização ou integridade. Essa alternativa foi rejeitada pela capability de autenticação/autorização e pelas regras do projeto.

## Conceptual Model

Uma movimentação confirmada possui um tipo único, referencia um Produto, registra quantidade positiva, usuário responsável, motivo, data e hora e dados contextuais aplicáveis. A observação pode estar presente. Uma entrada pode possuir Fornecedor quando aplicável; uma saída não exige Fornecedor.

A entrada aumenta o saldo disponível do Produto. A saída reduz o saldo, desde que não exceda o saldo disponível e não resulte em saldo negativo. O histórico preserva cada movimentação confirmada e a situação do estoque considera o saldo e o estoque mínimo.

## Confirmation and Rejection

A confirmação representa a aceitação da operação após as validações aplicáveis. Uma rejeição por autenticação, autorização, Produto, quantidade, saldo ou outra regra de integridade não pode deixar alteração de estoque ou movimentação confirmada no histórico.

A Specification não define como o backend obterá atomicidade, tratará concorrência ou registrará auditoria separada de tentativas rejeitadas. Esses pontos permanecem pendentes.

## Architecture Boundaries

- **Xano:** autoridade para autenticação/autorização aplicada à operação, validação, integridade, confirmação ou rejeição e estado do estoque.
- **Reflex:** apresentação, interação, envio de informações e exibição dos resultados, sem ser mecanismo suficiente de segurança.
- **OpenSpec:** contrato funcional de movimentações e registro das decisões aprovadas e pendentes.
- **Git:** versionamento dos artefatos e futuras implementações.

## Risks / Trade-offs

- **[Risco]** Saldo e histórico podem divergir em uma implementação futura. **Mitigação:** o contrato exige que rejeições não confirmem nenhum dos dois e que confirmações permaneçam rastreáveis.
- **[Risco]** Operações concorrentes podem disputar o mesmo saldo. **Mitigação:** a estratégia técnica permanece pendente e deve ser resolvida antes da implementação.
- **[Risco]** Regras pendentes sobre Produto, Categoria, Fornecedor, motivo e observação podem gerar interpretações diferentes. **Mitigação:** somente o motivo é normativo; os demais pontos estão explicitamente delimitados como pendentes.
- **[Risco]** O Fornecedor ser tratado como obrigatório para toda movimentação. **Mitigação:** o contrato o mantém contextual às entradas e exclui sua exigência para saídas.
- **[Trade-off]** Manter consultas, dashboard e relatórios fora desta change reduz o escopo imediato, mas exige capabilities posteriores para consumo do saldo e histórico.
- **[Trade-off]** Não definir tecnologia física preserva flexibilidade, mas exige decisões técnicas específicas antes do Apply de implementação.

## Scope Boundaries

Esta change não implementa backend, frontend, Xano, Reflex, tabelas, schemas, endpoints, APIs, telas ou integrações. Não define autenticação como tema principal, gestão de usuários, matriz detalhada de permissões, cadastros básicos, dashboard, relatórios, vendas, pagamentos, notas fiscais, financeiro, múltiplos depósitos, filiais ou importação em massa.

Também não decide política definitiva para Produto inativo, Categoria inativa, Fornecedor inativo, unidade e precisão, data/hora, imutabilidade, correção, cancelamento, estorno, auditoria separada, concorrência, transação, categorias detalhadas de erro ou consulta completa do histórico.
