# Design

## Context

A fundação do domínio do Sistema de Gerenciamento de Estoque já foi consolidada e arquivada. Essa base define os conceitos principais do sistema e as regras de rastreabilidade e integridade para estoque e movimentações. A presente change acrescenta o contrato de acesso que organiza como usuários, perfis e permissões governam o uso dessas capacidades.

A arquitetura do projeto define o Reflex como frontend exclusivo e o Xano como backend responsável por lógica de negócio, persistência e regras de autorização. A change de autenticação e autorização deve respeitar essa divisão, sem criar um comportamento de segurança dependente apenas da interface.

## Goals / Non-Goals

### Goals

- Definir um contrato claro de identidade e acesso para o sistema.
- Reforçar que o backend é a autoridade de autenticação e autorização.
- Registrar os perfis iniciais do projeto como ponto de partida do contrato de acesso.
- Definir as operações protegidas e seus requisitos mínimos de autorização.
- Preservar a rastreabilidade do usuário responsável nas movimentações.
- Estabelecer um contrato de resposta que permita distinguir autenticação, autorização, validação e regra de negócio.

### Non-Goals

- Criar tabelas, schemas físicos ou modelos de banco.
- Definir endpoints ou APIs concretas.
- Implementar código para autenticação, tokens, sessões ou autorização.
- Definir uma matriz final e detalhada de permissões para todas as funcionalidades.
- Criar componentes, telas ou fluxos específicos do frontend.
- Introduzir novos perfis sem necessidade comprovada e revisão do grupo.

## Decisions

### Xano será a autoridade de autenticação e autorização

Toda decisão sobre identidade do usuário, validação de acesso e autorização de operações protegidas deve ser tomada no backend Xano. O Reflex poderá receber o estado autenticado e apresentar feedback ao usuário, mas não deve ser usado como barreira de segurança.

**Alternativa considerada:** aplicar apenas controles visuais no frontend. Essa alternativa foi rejeitada porque não protege o sistema contra chamadas diretas ou bypass por cliente não autorizado.

### Autenticação e autorização serão tratadas como contrato de acesso

A change deve descrever comportamento, responsabilidades e regras de acesso sem fixar uma implementação final de autenticação, sessão ou token. Essa abordagem preserva a flexibilidade de decisão técnica para a etapa de implementação que vier a seguir.

**Alternativa considerada:** definir uma tecnologia e um formato de sessão/token nesta change. Essa alternativa foi rejeitada porque o contexto do projeto ainda não estabeleceu a decisão final, e a mudança precisa manter-se no nível de contrato e governança.

### Perfis são o ponto de partida para a autorização

Os perfis já previstos no projeto — Administrador, Estoquista e Usuário de consulta — devem servir de base para a avaliação de acessos. O contrato desta change deve reconhecer esses perfis e exigir que toda operação protegida seja avaliada conforme a identidade do usuário e seu perfil associado.

**Alternativa considerada:** criar novos perfis antes de revisar a necessidade. Essa alternativa foi rejeitada porque os perfis anteriores já foram definidos como base inicial e a mudança deve ser incremental e coerente com o domínio já consolidado.

### Autenticação e autorização devem ser separadas conceitualmente

Autenticação responde à pergunta: “quem é este usuário?” Autorização responde à pergunta: “este usuário pode executar esta ação?”. Essa separação deve ser explicitamente refletida nos requisitos e no comportamento do sistema.

**Alternativa considerada:** tratar autorização como consequência automática da autenticação. Essa alternativa foi rejeitada porque permite que qualquer usuário autenticado tenha acesso indevido a ações sensíveis ou de gestão.

### O frontend deve consumir contratos de erro sem reproduzir lógica interna

As falhas de autenticação, autorização, validação e regra de negócio devem ser distinguíveis para que o frontend apresente mensagens adequadas sem inferir regras internas do sistema a partir de texto livre. Isso preserva separação de responsabilidades e reduz acoplamento entre interface e backend.

**Alternativa considerada:** depender exclusivamente de respostas textuais genéricas. Essa alternativa foi rejeitada porque torna a interface frágil e não verificável.

## Risks / Trade-offs

- **[Risco]** A interface Reflex pode ser interpretada como mecanismo de segurança. **Mitigação:** a design documenta que a autenticação e autorização são decisões do backend, e que a interface é apenas uma camada de apresentação.

- **[Risco]** A ausência de uma matriz final de permissões pode causar ambiguidades iniciais. **Mitigação:** a change define o contrato de acesso e os perfis iniciais, deixando a matriz detalhada para revisão posterior conforme o grupo definir os requisitos.

- **[Risco]** A falta de clareza na distinção entre autenticação e autorização pode gerar inconsistências entre capabilities. **Mitigação:** a spec separa os requisitos e os cenários de autenticação e autorização, reforçando que a validação do usuário e a liberação da ação são etapas diferentes.

- **[Risco]** A sincronização entre domínio e acesso pode falhar se a identidade do usuário não for preservada em movimentações. **Mitigação:** o documento de design reforça que o usuário responsável deve estar associado às operações de estoque e ao histórico correspondente.

- **[Trade-off]** Adiar a escolha de tecnologia e sessão/token reduz decisões prematuras, mas exige que a implementação futura reavalie o contrato antes da execução. **Mitigação:** a design explicitamente marca essas decisões como pendentes e fora do escopo desta change.

## Architecture Boundaries

- **Reflex:** interação com o usuário, apresentação de estados autenticados e respostas de erro, e navegação sensível ao estado de autenticação.

- **Xano:** validação da identidade, avaliação de perfis e permissões, proteção das operações sensíveis e garantia de integridade e rastreabilidade.

- **OpenSpec:** mantém o contrato de acesso e o relacionamento entre a fundação de domínio e as capacidades do sistema.

A change não deve criar estruturas de implementação físico-tecnológicas; seu papel é orientar as próximas mudanças com um contrato de acesso verificável e coerente com a arquitetura existente.