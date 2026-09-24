# Proposal

## Why

A fundação do domínio já consolidou os conceitos de Produto, Estoque e Movimentação de Estoque, e as changes de autenticação/autorização e cadastros básicos estabeleceram as dependências necessárias para operar o estoque com identidade, integridade e rastreabilidade.

O sistema ainda precisa definir de forma explícita o contrato funcional das entradas e saídas de estoque. Sem esse contrato, podem surgir comportamentos divergentes para validação de quantidade, atualização do saldo, registro do histórico, identificação do usuário responsável e tratamento de operações rejeitadas.

Esta change propõe estabelecer o contrato funcional das movimentações de estoque, preservando a arquitetura do projeto: Xano como autoridade de negócio, integridade e estado do estoque; Reflex como camada exclusiva de apresentação e interação; OpenSpec como contrato; e Git como mecanismo de versionamento.

## What Changes

- Definir o contrato funcional comum das movimentações de estoque.
- Definir o comportamento conceitual das entradas de estoque.
- Definir o comportamento conceitual das saídas de estoque.
- Reforçar que toda movimentação possui tipo, Produto, quantidade positiva e usuário responsável.
- Definir que entradas aumentam o saldo disponível e saídas reduzem o saldo disponível.
- Impedir que uma saída exceda o saldo disponível ou produza saldo negativo.
- Definir o registro das movimentações confirmadas no histórico.
- Preservar a rastreabilidade por Produto, usuário responsável, tipo, quantidade, motivo e dados contextuais aplicáveis.
- Reconhecer Fornecedor como relação contextual de entrada, sem torná-lo requisito universal.
- Definir que operações rejeitadas não confirmam alteração no estoque nem no histórico.
- Relacionar o estado do estoque ao saldo disponível e ao estoque mínimo, sem incorporar dashboard ou relatórios.
- Manter a dependência com autenticação e autorização já consolidadas, sem redefinir a matriz detalhada de permissões.
- Delimitar o contrato da movimentação em relação à implementação futura do Xano, à integração futura do Reflex e às consultas posteriores.

## Scope

### Incluído

- Contrato funcional de movimentações de estoque.
- Entrada de estoque como tipo de movimentação.
- Saída de estoque como tipo de movimentação.
- Relação entre Movimentação, Produto e Estoque.
- Quantidade positiva como condição conceitual de movimentação.
- Atualização conceitual do saldo disponível após movimentação confirmada.
- Impossibilidade de saída acima do saldo disponível e de saldo negativo.
- Identificação do usuário responsável pela operação.
- Registro de tipo, Produto, quantidade, data e hora, motivo e dados contextuais aplicáveis.
- Observação quando aplicável, sem antecipar sua obrigatoriedade.
- Fornecedor quando aplicável à entrada, sem transformá-lo em requisito universal.
- Registro das movimentações confirmadas no histórico.
- Preservação da integridade histórica das movimentações confirmadas.
- Rejeição de operações inválidas sem confirmação de alteração no estoque ou no histórico.
- Relação conceitual entre saldo disponível, estoque mínimo e situação do estoque.
- Dependência funcional com autenticação e autorização já consolidadas.
- Definição dos limites entre contrato de movimentação, implementação backend, integração frontend e consultas futuras.

### Fora do escopo

- Implementação de código.
- Criação de tabelas, schemas físicos, campos físicos, chaves ou estruturas de banco.
- Definição de endpoints ou APIs concretas.
- Alteração no Xano ou implementação de XanoScript.
- Alteração no frontend Reflex, criação de telas ou componentes.
- Dashboard e relatórios gerenciais.
- Autenticação como tema principal, implementação de sessão ou tokens.
- Gestão de usuários e perfis.
- Definição da matriz detalhada de permissões por perfil.
- Criação, alteração ou inativação de categorias, produtos e fornecedores.
- Definição de política definitiva de exclusão de cadastros.
- Integrações externas.
- Vendas, pagamentos, notas fiscais e funcionalidades financeiras.
- Múltiplos depósitos ou filiais.
- Importação em massa.
- Decisões físicas de concorrência, transação, persistência ou implantação antes de revisão específica do grupo.
- Consultas gerenciais e relatórios derivados do estoque ou do histórico, que deverão ser tratados em capabilities posteriores quando necessário.

## Impact

- **Movimentação de Estoque:** passa a possuir um contrato funcional comum para entradas e saídas, com tipo, Produto, quantidade positiva, usuário responsável e rastreabilidade.
- **Entrada:** aumenta conceitualmente o saldo disponível e pode possuir Fornecedor como contexto aplicável, sem exigência universal.
- **Saída:** reduz conceitualmente o saldo disponível e não pode exceder o saldo existente nem gerar saldo negativo.
- **Produto:** continua sendo a referência central da movimentação e deve possuir Categoria válida para operação normal conforme o contrato de cadastros básicos. Produto inativo ou desabilitado não deve ser utilizado normalmente, sem que esta change defina todos os critérios operacionais pendentes.
- **Estoque:** representa o estado atual derivado das movimentações confirmadas e deve permitir relacionar saldo disponível, estoque mínimo e situação do estoque.
- **Histórico:** deve conservar as movimentações confirmadas e seus dados de rastreabilidade. Uma operação rejeitada não deve criar movimentação confirmada nem alterar o estado confirmado.
- **Fornecedor:** permanece contextual às entradas de estoque quando aplicável e não se torna requisito universal de movimentação.
- **Autenticação e autorização:** continuam sendo dependências obrigatórias. O usuário precisa ser autenticado e autorizado conforme a capability consolidada, mas a matriz detalhada de permissões não será redefinida nesta change.
- **Xano:** será responsável futuramente por aplicar as regras de negócio, validar integridade, controlar o estado do estoque e confirmar ou rejeitar a movimentação.
- **Reflex:** deverá futuramente apresentar os estados e coletar as interações, consumindo as decisões do backend sem duplicar regras de integridade ou segurança.
- **Dashboard e relatórios:** poderão consumir o saldo e o histórico em changes futuras, sem participar da confirmação ou do cálculo operacional da movimentação nesta change.

## Dependências

### Dependências com a fundação do domínio

- Movimentação possui exatamente um tipo: entrada ou saída.
- Movimentação está relacionada a um Produto.
- Movimentação possui um usuário responsável.
- A quantidade da movimentação é positiva.
- Entrada aumenta a quantidade disponível.
- Saída reduz a quantidade disponível.
- Saída não pode exceder a quantidade disponível nem gerar saldo negativo.
- A situação do estoque considera o estoque mínimo.
- Operação rejeitada não confirma alteração no estoque nem no histórico.

### Dependências com autenticação e autorização

- Operações de movimentação são operações protegidas.
- O usuário responsável deve estar autenticado e autorizado.
- A decisão final de acesso deve ser aplicada no backend.
- Falhas de autenticação, autorização, validação e regra de negócio devem permanecer distinguíveis.
- Esta change não define permissões específicas por perfil nem cria novos perfis.

### Dependências com cadastros básicos

- A movimentação referencia um Produto existente no domínio.
- Produto possui Categoria válida para operação normal.
- Produto inativo ou desabilitado não deve ser utilizado normalmente, mantendo pendentes os critérios exatos de tratamento.
- A relação Produto–Estoque sustenta a atualização conceitual do saldo.
- A relação Produto–Movimentação sustenta a rastreabilidade histórica.
- Fornecedor pode ser associado à entrada quando o contexto exigir, sem ser obrigatório para toda movimentação.
- A change não recria o ciclo de manutenção dos cadastros nem redefine a política de exclusão definitiva.

### Separação de responsabilidades

- **Contrato da movimentação:** define comportamentos observáveis, invariantes, relações e rejeições.
- **Implementação futura no Xano:** deverá materializar persistência, validações, consistência do saldo e histórico, após decisões técnicas próprias.
- **Integração futura no Reflex:** deverá apresentar e enviar informações conforme os contratos do backend.
- **Consultas futuras:** poderão consultar saldo e histórico operacional em change específica ou em uma decomposição posterior.
- **Dashboard e relatórios:** deverão consumir informações consolidadas sem alterar a regra de movimentação.

## Riscos

- **Divergência entre saldo e histórico:** se a confirmação do saldo e o registro histórico não forem tratados de forma coerente no backend, o estado do estoque poderá deixar de refletir as movimentações confirmadas.
- **Operações concorrentes:** saídas simultâneas podem consumir o mesmo saldo se a implementação futura não definir uma estratégia adequada.
- **Produto inválido ou inativo:** critérios incompletos para Produto e Categoria podem permitir operações incompatíveis com o catálogo.
- **Fornecedor universalizado:** exigir Fornecedor em toda movimentação violaria sua natureza contextual às entradas.
- **Histórico inconsistente:** permitir alteração ou remoção prematura de movimentações confirmadas pode comprometer a rastreabilidade.
- **Regras prematuras:** transformar hipóteses sobre motivo, observação, data, concorrência ou correção em regras definitivas pode congelar decisões ainda não aprovadas.
- **Escopo ampliado:** misturar movimentação com cadastros, autenticação, dashboard, relatórios ou integrações externas pode dificultar a validação da capability.
- **Segurança na interface:** tratar controles visuais do Reflex como autorização suficiente violaria a arquitetura definida.

## Decisões de escopo a serem revisadas pelo grupo

As decisões abaixo permanecem pendentes e não devem ser convertidas em regras definitivas sem revisão explícita:

- tratamento operacional de Produto inativo ou desabilitado;
- efeito de Categoria inativa sobre novas movimentações;
- critérios para considerar uma Categoria válida no momento da movimentação;
- obrigatoriedade do motivo para entrada, saída ou ambas;
- obrigatoriedade ou opcionalidade da observação;
- obrigatoriedade de Fornecedor em tipos específicos de entrada;
- possibilidade de uso de Fornecedor inativo;
- unidade e precisão aceitas para quantidade;
- definição da data e hora pelo sistema;
- imutabilidade das movimentações confirmadas;
- mecanismo de correção, cancelamento ou estorno;
- necessidade de auditoria específica para tentativas rejeitadas;
- garantia de consistência entre atualização do saldo e registro histórico;
- tratamento de operações concorrentes;
- aceitação de saída igual ao saldo disponível;
- cálculo e classificação da situação relacionada ao estoque mínimo;
- comportamento quando o estoque mínimo for zero;
- categorias estruturadas de erro específicas para a movimentação;
- permissões específicas por perfil;
- inclusão da consulta do histórico nesta change ou em change separada;
- decisão técnica sobre transação, persistência, concorrência e implementação no Xano;
- decisão sobre a decomposição entre contrato, implementação backend, integração frontend e consultas operacionais.

Essas pendências devem ser resolvidas pelo grupo antes de serem transformadas em requisitos normativos na Specification ou em decisões de implementação.

## Status

Proposal da change preparada para revisão do grupo, com base no Explore da capability movimentacao-estoque, sem Specification, Design, Tasks, Apply, Archive ou implementação técnica.
