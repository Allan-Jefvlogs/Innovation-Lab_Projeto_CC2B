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

### Requirement: O frontend Reflex MUST restringir a navegação interna conforme o perfil de estoque

Em cada carregamento de uma rota interna autenticada, o frontend MUST consultar centralmente a rota atual e o `inventory_profile_id` carregado em `AuthState`. O perfil `1` (Líder) pode navegar para todas as páginas internas. O perfil `2` (Almoxarife) pode acessar `/dashboard`, `/produtos`, `/produtos/novo`, `/categorias`, `/fornecedores`, `/estoque`, `/movimentacoes`, `/movimentacoes/entradas`, `/movimentacoes/saidas` e `/relatorios`. O perfil `3` (Auxiliar de almoxarifado) pode acessar `/dashboard`, `/produtos`, `/categorias`, `/fornecedores`, `/estoque`, `/movimentacoes` e `/relatorios`.

Uma rota interna não permitida MUST redirecionar a sessão autenticada para `/dashboard`. `/dashboard` MUST continuar acessível como destino de retorno para uma sessão autenticada sem perfil atribuído ou com identificador de perfil não reconhecido. Uma sessão sem autenticação MUST continuar sendo redirecionada para `/`. Essa proteção é exclusivamente uma regra de navegação/UX; operações e dados continuam sujeitos à autorização do backend Xano.

#### Scenario: Líder navega para qualquer página interna

- **WHEN** um usuário autenticado com `inventory_profile_id == 1` acessar diretamente qualquer rota interna registrada
- **THEN** o frontend MUST permitir a navegação sem redirecionamento por perfil.

#### Scenario: Almoxarife acessa rotas permitidas e tem rotas administrativas bloqueadas

- **WHEN** um usuário autenticado com `inventory_profile_id == 2` acessar uma rota permitida para Almoxarife
- **THEN** o frontend MUST manter a navegação na rota solicitada
- **WHEN** esse usuário acessar `/usuarios` ou `/perfis`
- **THEN** o frontend MUST redirecionar a navegação para `/dashboard`.

#### Scenario: Auxiliar acessa consultas e não acessa operações de movimentação

- **WHEN** um usuário autenticado com `inventory_profile_id == 3` acessar `/dashboard`, `/produtos`, `/categorias`, `/fornecedores`, `/estoque`, `/movimentacoes` ou `/relatorios`
- **THEN** o frontend MUST manter a navegação na rota solicitada
- **WHEN** esse usuário acessar `/usuarios`, `/perfis`, `/produtos/novo`, `/movimentacoes/entradas` ou `/movimentacoes/saidas`
- **THEN** o frontend MUST redirecionar a navegação para `/dashboard`.

#### Scenario: Sessão autenticada sem perfil válido usa o dashboard como destino seguro

- **WHEN** uma sessão autenticada sem `inventory_profile_id` atribuído ou com identificador desconhecido acessar uma rota interna diferente de `/dashboard`
- **THEN** o frontend MUST redirecionar a navegação para `/dashboard`
- **AND** o frontend MUST permitir que `/dashboard` seja carregado sem criar um ciclo de redirecionamento.
