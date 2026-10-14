# Spec Delta: autenticacao-autorizacao

## Purpose

Esta alteração estende a capability consolidada `autenticacao-autorizacao` para cobrir a integração de autenticação entre o frontend Reflex e o backend Xano. Ela formaliza a inclusão do campo `inventory_profile_id` no contrato de resposta do endpoint `GET /auth/me`, a persistência e recuperação de sessão baseada em token no cliente Reflex, o fluxo de logout e a proteção de rotas como mecanismo de experiência do usuário (UX), mantendo a autoridade definitiva de segurança no Xano.

## MODIFIED Requirements

### Requirement: O sistema MUST manter a separação de responsabilidades entre frontend e backend

O sistema MUST manter a separação de responsabilidades entre frontend e backend.

A responsabilidade do frontend é apresentar o estado de autenticação, enviar as informações relevantes, guiar a navegação das páginas de acordo com a sessão e informar o usuário sobre o resultado da operação. A proteção de rotas no frontend MUST ser tratada como comodidade de navegação e experiência de interface.

A responsabilidade do backend é validar identidade, aplicar regras de autorização, avaliar integridade do domínio e decidir se a operação pode ser confirmada.

#### Scenario: Frontend sem autonomia de segurança

- **WHEN** o frontend oculta ou exibe controles de acesso ou protege a navegação de rotas internas
- **THEN** isso MUST ser tratado apenas como experiência de interface
- **AND** a autorização MUST continuar sendo validada no backend para cada requisição protegida

#### Scenario: Backend como autoridade

- **WHEN** uma operação protegida for chamada diretamente ou por qualquer cliente não autorizado
- **THEN** a decisão final MUST ser feita pelo backend conforme as regras de autorização e integridade do sistema

#### Scenario: Proteção de rota no frontend como mecanismo de interface

- **WHEN** um usuário não autenticado tenta acessar diretamente uma página interna do sistema (como `/dashboard` ou `/produtos`)
- **THEN** o frontend Reflex MUST redirecionar a navegação para a tela de login (`/`)
- **AND** esse redirecionamento MUST ser considerado um mecanismo de experiência do usuário, sem substituir a validação mandatória de token e autorização que o backend Xano executa em cada requisição de dados

#### Scenario: Rejeição no backend de requisição sem token válido

- **WHEN** uma requisição direta for enviada a qualquer endpoint protegido do Xano sem cabeçalho `Authorization: Bearer <authToken>` ou com token inválido/expirado
- **THEN** o backend Xano MUST rejeitar a requisição com erro de acesso negado
- **AND** nenhuma informação protegida de cadastro ou estoque MUST ser retornada

---

## ADDED Requirements

### Requirement: O backend MUST fornecer os dados de identidade e perfil do usuário autenticado no endpoint de sessão

O endpoint `GET /auth/me` do grupo `Authentication` MUST incluir no seu payload de resposta o campo `inventory_profile_id` do registro `user` correspondente ao token autenticado (`$auth.id`), além dos dados cadastrais básicos (`id`, `name`, `email`, `role`).

Isso permite que o cliente identifique o perfil de domínio do estoque do usuário autenticado e apresente a interface contextualizada.

#### Scenario: Consulta de sessão com perfil de estoque atribuído

- **WHEN** uma requisição autenticada com token válido for enviada para `GET /auth/me` e o usuário possuir perfil de estoque atribuído
- **THEN** o backend MUST responder com sucesso (HTTP 200)
- **AND** a resposta MUST conter os campos `id`, `name`, `email`, `role` e `inventory_profile_id` com o respectivo identificador numérico do perfil.

#### Scenario: Consulta de sessão sem perfil de estoque atribuído

- **WHEN** uma requisição autenticada com token válido for enviada para `GET /auth/me` e o usuário não possuir perfil de estoque vinculado
- **THEN** o backend MUST responder com sucesso (HTTP 200)
- **AND** o campo `inventory_profile_id` MUST estar presente na resposta com valor nulo (`null`).

---

### Requirement: O frontend Reflex MUST autenticar credenciais de usuário através do endpoint de login

O frontend Reflex MUST coletar e-mail e senha informados pelo usuário na tela de login e submetê-los ao endpoint `POST /auth/login` do Xano.

O sistema MUST fornecer feedback visual claro durante o processamento e distinguir tentativas com credenciais inválidas de falhas gerais de conectividade.

#### Scenario: Autenticação com credenciais válidas

- **WHEN** o usuário submeter e-mail e senha correspondentes a um cadastro válido no Xano
- **THEN** o frontend MUST receber o `authToken` e o `user_id` retornados pelo backend
- **AND** o frontend MUST armazenar o token e redirecionar a navegação para `/dashboard`.

#### Scenario: Tentativa de login com credenciais inválidas

- **WHEN** o usuário submeter um e-mail não cadastrado ou uma senha incorreta
- **THEN** o backend MUST retornar erro de acesso negado
- **AND** o frontend Reflex MUST exibir mensagem amigável de erro informando credenciais inválidas
- **AND** o usuário MUST permanecer na página de login com a possibilidade de tentar novamente.

#### Scenario: Indisponibilidade de conexão com o backend

- **WHEN** o frontend não conseguir estabelecer conexão com o backend Xano durante a submissão do formulário
- **THEN** o frontend Reflex MUST capturar a falha de transporte
- **AND** o frontend MUST exibir mensagem informando a impossibilidade de comunicação com o servidor, sem travar o estado da aplicação.

---

### Requirement: O frontend Reflex MUST gerenciar e persistir o token de autenticação de forma segura no cliente

O frontend Reflex MUST armazenar o `authToken` emitido pelo Xano em armazenamento persistente no navegador (`rx.LocalStorage`) e utilizá-lo para manter a sessão ativa e autorizar as requisições subsequentes.

#### Scenario: Recuperação automática da sessão ao recarregar a página

- **WHEN** o usuário autenticado recarregar a página (F5) ou reabrir o navegador em uma rota interna
- **THEN** o frontend Reflex MUST recuperar o `authToken` previamente persistido no `rx.LocalStorage`
- **AND** o frontend MUST consultar `GET /auth/me` para revalidar a sessão e restaurar os dados do usuário em memória
- **AND** a navegação na página solicitada MUST prosseguir normalmente sem exigir novo login manual.

#### Scenario: Token expirado ou revogado durante a verificação de sessão

- **WHEN** o frontend tentar validar uma sessão cujo `authToken` esteja expirado ou tenha sido invalidado pelo backend
- **THEN** o backend MUST responder com falha de autenticação (HTTP 401 ou 403)
- **AND** o frontend Reflex MUST remover o `authToken` do `rx.LocalStorage`, limpar os dados de sessão em memória e redirecionar o usuário para a tela de login (`/`).

---

### Requirement: O frontend Reflex MUST permitir o encerramento seguro da sessão (logout)

O sistema MUST disponibilizar uma ação de encerramento de sessão (*logout*) acessível em todas as páginas internas da aplicação.

#### Scenario: Execução de logout pelo usuário

- **WHEN** o usuário autenticado acionar a opção "Sair" na barra de navegação
- **THEN** o frontend Reflex MUST limpar o `authToken` armazenado no `rx.LocalStorage`
- **AND** o estado de autenticação em memória MUST ser resetado para não autenticado
- **AND** o usuário MUST ser redirecionado imediatamente para a página de login (`/`).

---

### Requirement: O frontend Reflex MUST restringir rotas operacionais conforme os grants efetivos

Em cada carregamento de rota interna autenticada, `AuthState` MUST verificar o código de permissão requerido pela rota usando `permission_codes` efetivos retornados por `/auth/me`, independentemente do nome ou ID de um perfil operacional. Uma sessão sem o grant necessário MUST ser redirecionada para `/dashboard`; a interface MUST NOT conceder grants nem substituir a autorização do Xano.

As rotas operacionais MUST exigir: `/produtos` e suas consultas `product.read`; `/produtos/novo`, `product.create`; edição de produto, `product.update`; `/categorias`, `category.read`; `/fornecedores`, `supplier.read`; `/estoque`, `stock.read`; `/movimentacoes`, `movement.read`; `/movimentacoes/entradas`, `stock.entry`; `/movimentacoes/saidas`, `stock.exit`; e `/relatorios`, `report.read`. A regra de `/movimentacoes` é distinta do endpoint compartilhado `GET /movements`, que pode aceitar `movement.read` ou `report.read` para atender às duas telas.

`/usuarios` e `/perfis` MUST permanecer exclusivos ao perfil `administrator`, mesmo que outro perfil receba grants operacionais. A identificação de administrador MUST seguir o código de perfil `administrator`; o Xano continua autoridade para as operações administrativas. A rota `/alterar-senha` MUST continuar sujeita ao fluxo de troca obrigatória. `/dashboard` MUST ser acessível como destino seguro a uma sessão autenticada sem perfil/grants utilizáveis; sessão não autenticada MUST ser redirecionada para `/`.

#### Scenario: Auxiliar recebe grant operacional

- **WHEN** uma sessão autenticada de Auxiliar possui `stock.entry` efetivo e acessa `/movimentacoes/entradas`
- **THEN** `AuthState` MUST permitir a rota, independentemente do ID ou nome operacional do perfil
- **AND** o endpoint MUST continuar validando `stock.entry` no Xano.

#### Scenario: Auxiliar não recebe grant operacional

- **WHEN** uma sessão autenticada de Auxiliar não possui `stock.exit` e acessa `/movimentacoes/saidas`
- **THEN** `AuthState` MUST redirecionar para `/dashboard`
- **AND** uma chamada direta ao endpoint MUST continuar sujeita à autorização do Xano.

#### Scenario: Grants de Histórico e Relatórios são independentes

- **WHEN** uma sessão não possui `movement.read`
- **THEN** `/movimentacoes` MUST ser bloqueada, mesmo que o usuário possua outros grants
- **WHEN** uma sessão não possui `report.read`
- **THEN** `/relatorios` MUST ser bloqueada, mesmo que o usuário possua `movement.read`.

#### Scenario: Auxiliar com grants acessa Entradas e Saídas

- **WHEN** a sessão de Auxiliar possui `stock.entry` e `stock.exit` efetivos
- **THEN** as rotas de Entradas e Saídas MUST ser permitidas
- **AND** a autorização definitiva de cada escrita MUST continuar sendo feita pelo Xano.

#### Scenario: Rotas administrativas permanecem exclusivas

- **WHEN** um usuário autenticado sem perfil `administrator` acessa `/usuarios` ou `/perfis`
- **THEN** o frontend MUST redirecionar para `/dashboard`
- **AND** as APIs administrativas MUST recusar o usuário.

#### Scenario: Sessão autenticada sem grants ou perfil operacional

- **WHEN** uma sessão autenticada sem perfil válido ou sem grants operacionais acessa uma rota operacional
- **THEN** o frontend MUST redirecionar para `/dashboard`
- **AND** `/dashboard` MUST carregar sem ciclo de redirecionamento.
