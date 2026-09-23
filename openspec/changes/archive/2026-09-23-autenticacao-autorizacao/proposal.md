# Change: Autenticação e Autorização

## Why

A fundação do domínio do Sistema de Gerenciamento de Estoque já foi consolidada e arquivada, definindo os conceitos centrais de usuário, perfil, categoria, produto, fornecedor, estoque e movimentação de estoque.

O projeto ainda precisa estabelecer de forma explícita como os usuários são identificados, como a autenticação é validada, como os perfis se relacionam com permissões e como as operações protegidas são autorizadas.

Sem esse contrato, o frontend Reflex e o backend Xano podem evoluir com premissas divergentes sobre identidade e acesso, aumentando o risco de comportamento inconsistente, falhas de segurança e retrabalho nas próximas capabilities.

Esta change estabelece o contrato de autenticação e autorização do sistema, preservando a arquitetura definida no projeto: Reflex como camada de apresentação e interação, e Xano como autoridade responsável pela autenticação, autorização, integridade e regras de negócio.

## What Changes

- Definir o contrato de identidade e autenticação dos usuários.
- Definir os perfis iniciais já reconhecidos pelo projeto:
  - Administrador;
  - Estoquista;
  - Usuário de consulta.
- Definir o conceito de permissão e sua relação com os perfis.
- Estabelecer quais tipos de operações exigem autenticação e quais exigem autorização adicional.
- Estabelecer que as decisões de autorização devem ser aplicadas no backend Xano.
- Definir como o frontend Reflex deve consumir o estado de autenticação e as respostas de autorização, sem utilizar a interface como mecanismo de segurança.
- Definir o contrato de respostas para falhas de autenticação e autorização.
- Preservar a associação entre a identidade do usuário e as operações críticas de estoque.
- Estabelecer a relação entre esta change e a fundação de domínio já consolidada.

## Scope

### Incluído

- Contrato conceitual de autenticação.
- Contrato conceitual de autorização.
- Perfis iniciais do sistema.
- Relação entre perfil e permissão.
- Identificação das operações protegidas.
- Responsabilidades do Xano e do Reflex.
- Categorias de erro de autenticação e autorização.
- Relação entre identidade do usuário e rastreabilidade das movimentações.

### Fora do escopo

- Implementação de código.
- Criação de tabelas ou endpoints.
- Implementação de telas ou componentes.
- Escolha definitiva do método de autenticação.
- Escolha definitiva do formato de sessão ou token.
- Definição de uma matriz detalhada e definitiva de permissões para todas as funcionalidades.
- MFA, SSO, OAuth, integrações externas ou mecanismos avançados de segurança.
- Regras de negócio de estoque que não sejam relacionadas à autorização.

## Impact

- **Xano:** será a autoridade para autenticação, autorização e validação das decisões de acesso.
- **Reflex:** será responsável pela apresentação, navegação e feedback relacionados ao estado de autenticação e autorização, sem substituir as validações do backend.
- **Usuários e perfis:** passam a possuir um contrato explícito de identidade e acesso.
- **Estoque e movimentações:** continuam utilizando a identidade do usuário responsável para garantir rastreabilidade e passam a considerar a autorização das operações.
- **Próximas changes:** cadastros, estoque, dashboard e relatórios poderão utilizar o contrato de autenticação e autorização definido nesta change.

## Riscos

- **Segurança por interface:** tratar a ocultação de controles no Reflex como mecanismo de segurança.
- **Conflito de responsabilidade:** permitir que o frontend decida autorização ou que o backend não valide a operação.
- **Definição incompleta de permissões:** criar regras implícitas que produzam comportamentos diferentes entre capabilities.
- **Decisão prematura de tecnologia:** definir método de autenticação ou formato de sessão antes da revisão do grupo.
- **Escopo excessivo:** misturar autenticação, autorização, gestão completa de usuários e implementação de funcionalidades nesta mesma change.