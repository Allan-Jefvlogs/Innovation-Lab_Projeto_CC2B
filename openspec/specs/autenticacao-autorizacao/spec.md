# autenticacao-autorizacao Specification

## Purpose
Esta capability estabelece o contrato comportamental de autenticação e autorização do Sistema de Gerenciamento de Estoque. Ela define identidade do usuário, associação com perfis, necessidade de autorização para operações protegidas e as regras mínimas de resposta e rastreabilidade que devem ser respeitadas por todas as outras changes.

A finalidade desta specification é garantir que o Reflex continue atuando como camada de apresentação e interação, enquanto o Xano permanece responsável por autenticação, autorização, integridade e regras de negócio.

## Requirements

### Requirement: O sistema MUST identificar o usuário antes de permitir acesso a operações protegidas

Toda operação protegida que envolve acesso a dados ou execução de ações relevantes para o sistema MUST exigir identificação de um usuário autenticado.

#### Scenario: Usuário não autenticado

- **WHEN** uma operação protegida é solicitada por uma identidade inexistente ou ausente
- **THEN** o sistema MUST rejeitar a operação como não autenticada
- **AND** nenhuma ação de alteração de estado, persistência ou execução de processo relevante MUST ser confirmada

#### Scenario: Usuário autenticado

- **WHEN** uma operação protegida é solicitada por um usuário com identidade válida
- **THEN** o sistema MUST continuar a avaliação de autorização antes de concluir a operação

### Requirement: O sistema MUST reconhecer os perfis iniciais definidos pelo projeto

O sistema MUST reconhecer os perfis iniciais definidos no projeto:

- Administrador;
- Estoquista;
- Usuário de consulta.

A associação entre usuário e perfil MUST ser tratada como parte do contrato de acesso do sistema.

#### Scenario: Perfil associado ao usuário

- **WHEN** um usuário é criado ou atualizado no sistema
- **THEN** o perfil associado MUST ser identificável e consistente com o contrato de acesso do sistema
- **AND** a autorização desse usuário MUST ser avaliada com base no perfil associado

#### Scenario: Perfil não informado

- **WHEN** um usuário não possuir perfil válido associado
- **THEN** o sistema MUST impedir o acesso a operações protegidas
- **AND** a tentativa MUST ser rejeitada com uma resposta de acesso inválido ou não autorizado, conforme o contrato de erro definido nesta capability

### Requirement: O sistema MUST separar claramente autenticação de autorização

Autenticação e autorização são responsabilidades distintas e MUST ser tratadas separadamente no contrato do sistema.

A autenticação MUST decidir se a identidade do usuário é válida. A autorização MUST decidir se o usuário autenticado pode executar uma operação específica.

#### Scenario: Usuário autenticado sem permissão

- **WHEN** um usuário autenticado tenta executar uma operação para a qual não possui autorização
- **THEN** o sistema MUST rejeitar a operação como não autorizada
- **AND** o frontend MUST receber uma resposta reconhecível como falha de autorização
- **AND** a funcionalidade MUST permanecer protegida mesmo que o cliente oculte a ação visualmente

#### Scenario: Usuário não autenticado

- **WHEN** um usuário tenta executar uma operação protegida sem identidade válida
- **THEN** a operação MUST ser rejeitada antes de qualquer avaliação de permissão específica

### Requirement: O sistema MUST proteger as operações relevantes conforme o perfil e as permissões

As operações que alteram dados, consultam informações protegidas, gerenciam acessos ou realizam movimentações de estoque MUST estar protegidas por avaliação de autorização no backend.

O escopo desta capability MUST considerar como operações protegidas, no mínimo:

- gerenciamento de usuários e perfis;
- cadastro e manutenção de registros de domínio relevantes;
- operações de entrada e saída de estoque;
- consulta do histórico de movimentações;
- consulta de estoque e situação de produtos;
- consulta e geração de informações gerenciais e relatórios.

#### Scenario: Operação de estoque por usuário sem permissão

- **WHEN** um usuário autenticado sem permissão adequada tenta registrar entrada ou saída de estoque
- **THEN** o sistema MUST rejeitar a operação como não autorizada
- **AND** nenhuma alteração de estoque ou registro de movimentação MUST ser confirmada

#### Scenario: Operação de consulta por usuário sem permissão

- **WHEN** um usuário autenticado sem permissão adequada tenta consultar dados protegidos
- **THEN** o sistema MUST rejeitar a consulta como não autorizada
- **AND** o resultado não deve depender da ocultação visual de controles no frontend

### Requirement: O sistema MUST preservar a identidade do usuário responsável pelas movimentações

Toda entrada ou saída de estoque MUST registrar a identidade do usuário autenticado e autorizado que executou a operação.

#### Scenario: Registro de movimentação

- **WHEN** uma entrada ou saída de estoque for registrada
- **THEN** o sistema MUST associar a identidade do usuário responsável à movimentação
- **AND** essa informação MUST permanecer rastreável no histórico da operação

#### Scenario: Movimentação sem responsável

- **WHEN** uma operação de estoque não identifica um usuário válido e autorizado
- **THEN** a operação MUST ser rejeitada
- **AND** nenhuma alteração de estoque ou movimentação confirmada MUST permanecer registrada

### Requirement: O sistema MUST distinguir respostas de autenticação, autorização, validação e regra de negócio

As respostas do backend MUST permitir distinguir falhas de autenticação, falhas de autorização, erros de validação e erros de regra de negócio.

Isso permite que o frontend apresente feedback sem reproduzir a lógica interna do backend.

#### Scenario: Falha de autenticação

- **WHEN** o cliente não possui identidade válida para uma operação protegida
- **THEN** o backend MUST responder com um erro de autenticação reconhecível

#### Scenario: Falha de autorização

- **WHEN** o cliente possui identidade válida, mas não possui a autorização necessária
- **THEN** o backend MUST responder com um erro de autorização reconhecível

#### Scenario: Falha de validação ou regra de negócio

- **WHEN** a operação não atende às regras de integridade ou validação do sistema
- **THEN** o backend MUST responder com uma categoria específica de erro
- **AND** o frontend MUST poder exibir o erro de forma consistente sem inferir regras internas a partir de texto livre

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
