# Proposal: Autenticação no Frontend Reflex

## Why

Atualmente, o frontend do Sistema de Gerenciamento de Estoque implementado em Reflex possui uma tela de login puramente prototipada e estática em `Meu_projeto/pages/login.py`. O botão "Entrar" apenas redireciona para `/dashboard` através de um link estático, o cabeçalho do sistema em `Meu_projeto/components/layout.py` exibe o texto fixo `"Admin • Usuário mock"` e todas as páginas internas podem ser acessadas sem qualquer autenticação.

Por outro lado, o backend Xano já possui os endpoints de autenticação e identificação de usuário no grupo `Authentication` (`POST auth/login` e `GET auth/me`), e a autorização de domínio do estoque já foi estruturada na capability `operacoes-backend-cadastros` com verificação de perfil (`inventory_profile_id`) e grants da tabela `inventory_profile_permission`. Contudo, o endpoint existente `GET auth/me` limita sua projeção de saída a campos legados do quick-start (`id`, `created_at`, `name`, `email`, `account_id`, `role`), não fornecendo atualmente o `inventory_profile_id`.

Sem a integração real entre o Reflex e o Xano:
1. O sistema não autentica credenciais reais, violando o requisito central da capability consolidada `autenticacao-autorizacao`.
2. As operações de estoque e cadastros não conseguem identificar o usuário responsável, impedindo o cumprimento da regra de rastreabilidade.
3. Não há controle de sessão, persistência de identidade ou proteção de rotas no frontend.
4. O frontend não consegue identificar o perfil de estoque do usuário autenticado para apresentar a interface de forma contextualizada.

Esta change propõe implementar a integração real de autenticação no frontend Reflex consumindo os endpoints existentes do Xano, estabelecendo o gerenciamento seguro de sessão via token, a identificação dinâmica do usuário e seu perfil de estoque, a proteção de navegação nas rotas autenticadas, o tratamento adequado de falhas de autenticação e um ajuste pontual e estritamente delimitado no backend Xano para incluir `inventory_profile_id` no payload de retorno do `GET auth/me`.

## What Changes

- Atualizar de forma cirúrgica e pontual o endpoint `GET auth/me` no backend Xano (`xano/api/authentication/auth/me_GET.xs`) para incluir o campo `inventory_profile_id` na lista de campos retornados (`output`).
- Substituir o formulário mock de `Meu_projeto/pages/login.py` por um fluxo de autenticação real integrado ao Xano via `POST auth/login`.
- Implementar gerenciamento global de autenticação em Reflex (`AuthState`), armazenando com segurança o `authToken` retornado através de `rx.LocalStorage`.
- Recuperar os dados da identidade e perfil do usuário autenticado chamando `GET auth/me` com o cabeçalho `Authorization: Bearer <authToken>`.
- Mapear o perfil de estoque do usuário (`inventory_profile_id` / códigos `administrator`, `stockkeeper`, `read_only`) para seus nomes de exibição amigáveis (Líder, Almoxarife, Auxiliar de almoxarifado).
- Exibir a identidade e perfil reais do usuário autenticado no cabeçalho do layout em substituição ao texto mock fixo.
- Implementar o fluxo de encerramento de sessão (logout), limpando o token persistido e os dados em memória, e redirecionando para a tela de login.
- Implementar mecanismo de proteção de rotas nas páginas protegidas, redirecionando usuários não autenticados para `/`.
- Tratar cenários de erro de forma clara e amigável: credenciais inválidas, falha de conectividade com a API e expiração de sessão.
- Parametrizar a URL base da API do Xano via variável de ambiente (`XANO_API_BASE_URL`), evitando URLs fixas no código-fonte.

## Scope

### Incluído

- **Ajuste Pontual no Backend Xano:**
  - Inclusão do campo `"inventory_profile_id"` na cláusula `output` da consulta de usuário em `xano/api/authentication/auth/me_GET.xs`, viabilizando o consumo do perfil pelo frontend.
- **Fluxo de Login no Reflex:**
  - Envio seguro de e-mail e senha via requisição HTTP assíncrona ao endpoint `POST auth/login` do Xano.
  - Indicador visual de carregamento (*loading*) durante a autenticação.
  - Tratamento e exibição de feedback visual para credenciais inválidas (`Invalid Credentials` / 401/403) e erros de rede.
- **Gerenciamento de Token e Sessão:**
  - Armazenamento persistente do `authToken` no navegador utilizando `rx.LocalStorage`.
  - Recuperação automática da sessão ao recarregar a página ou reabrir o navegador.
  - Consumo do endpoint `GET auth/me` para carregar nome, e-mail, papel e `inventory_profile_id` do usuário autenticado.
- **Identificação do Perfil:**
  - Associação e exibição do perfil de estoque correspondente na interface (`Líder`, `Almoxarife`, `Auxiliar de almoxarifado`).
  - Tratamento visual para usuários sem perfil atribuído (`"Sem perfil atribuído"`).
- **Navegação e Proteção de Rotas:**
  - Guarda de navegação (*route protection*) nas páginas internas (`/dashboard`, `/produtos`, `/categorias`, `/fornecedores`, `/estoque`, `/movimentacoes`, `/usuarios`, `/perfis`, `/relatorios`).
  - Redirecionamento automático de usuários não autenticados para `/`.
  - Redirecionamento de usuário já logado que acesse a página de login `/` diretamente para `/dashboard`.
- **Fluxo de Logout:**
  - Ação de logout no menu/sidebar que limpa o armazenamento local, invalida o estado em memória e redireciona o usuário para a página de login.
- **Configuração:**
  - Configuração da URL base do Xano através de variável de ambiente (`XANO_API_BASE_URL`).

### Fora do escopo

- Criação ou alteração de tabelas no banco de dados Xano.
- Criação de novos endpoints no Xano (a única alteração de backend é estritamente a projeção de saída do `auth/me` existente).
- Criação de telas de cadastro de usuário (*signup*) ou recuperação de senha no Reflex.
- Implementação de autenticação via redes sociais, SSO, OAuth ou autenticação multifator (MFA).
- Telas de edição de perfil ou gerenciamento visual da matriz de permissões.
- Integração dos formulários de domínio (cadastro de produtos, categorias, fornecedores ou estoque) com suas respectivas APIs do Xano (serão integrados em changes específicas de cada módulo).

## Decisões aprovadas e diretrizes de projeto

1. **Separação de Responsabilidades:** O backend Xano é a única autoridade para validação de credenciais, emissão de tokens e autorização de operações. O frontend Reflex atua exclusivamente como camada de apresentação, persistência de sessão do cliente e experiência do usuário.
2. **Proteção no Frontend como UX:** A proteção de páginas no Reflex serve para guiar o usuário e evitar que interfaces vazias sejam exibidas; a segurança real das operações e dos dados continua garantida pelo cabeçalho `Authorization: Bearer <authToken>` exigido pelo Xano em cada requisição protegida.
3. **Persistência de Sessão:** O token de autenticação será persistido utilizando `rx.LocalStorage`, permitindo que a sessão do usuário permaneça ativa entre recarregamentos de página (F5) até que expire ou que o logout seja acionado.
4. **Contrato do Endpoint `auth/me`:** O endpoint `GET /auth/me` existente é expandido exclusivamente para retornar o campo `inventory_profile_id`, garantindo que o frontend identifique o perfil de domínio sem necessidade de consultas adicionais ou novas tabelas.
5. **Resoluções de Erro Distinguíveis:** Falhas de credenciais (401/403 no login) devem exibir `"E-mail ou senha inválidos."`; falhas de comunicação com o backend devem exibir mensagem orientando nova tentativa; expiração de token em rotas protegidas deve deslogar o usuário e redirecioná-lo para a tela de login.
6. **Configuração via Ambiente:** A URL da API do Xano não deve ser codificada de forma estática no código-fonte Python, devendo ser lida de variável de ambiente (`XANO_API_BASE_URL` ou arquivo `.env`).

## Dependências

### Dependências funcionais
- `openspec/specs/autenticacao-autorizacao/spec.md`: especificação consolidada de requisitos de autenticação e autorização do sistema.
- `docs/project-overview.md` e `docs/domain-model.md`: definições dos perfis conceituais e regras de negócio.
- `openspec/changes/operacoes-backend-cadastros`: define os códigos de perfil e o relacionamento do usuário com o perfil de estoque (`inventory_profile_id`).

### Dependências técnicas
- Backend Xano disponível com o grupo `Authentication` funcional (`POST auth/login` e `GET auth/me`).
- Biblioteca `httpx` (já instalada no ambiente conforme `requirements.txt`) para execução de chamadas HTTP assíncronas entre o backend Reflex e a API do Xano.
- Componente `rx.LocalStorage` do Reflex para armazenamento reativo do token no navegador.

## Impact

- **Backend Xano:** ajuste pequeno e seguro em `auth/me_GET.xs` para adicionar `inventory_profile_id` ao payload de resposta.
- **Frontend Reflex:** deixa de ser uma casca estática com navegação mockada e passa a operar com autenticação e identificação de usuário reais.
- **Página de Login (`login.py`):** passa a conter estado assíncrono real, feedback de erro e validação de credenciais.
- **Layout Global (`layout.py`):** reflete a identidade e o perfil dinâmicos do usuário conectado e oferece mecanismo funcional de logout.
- **Páginas Protegidas:** passam a ser acessíveis somente por sessões ativas e identificadas.
- **Próximas Capabilities:** telas de cadastro (categorias, produtos, fornecedores) e movimentações de estoque poderão reutilizar diretamente o estado de autenticação (`AuthState.auth_token` e `AuthState.user`) para disparar requisições autorizadas e rastreáveis.

## Riscos e Mitigações

- **Risco: Falha de conexão ou Xano indisponível.**
  *Mitigação:* Captura de exceções de rede (`httpx.RequestError`, timeouts) no cliente HTTP e exibição de alerta claro de falha de conexão na interface, sem travar o aplicativo.
- **Risco: Token expirado ou revogado durante o uso do sistema.**
  *Mitigação:* Interceptação de respostas 401/403 nas consultas de sessão (`GET auth/me`) com limpeza automática do `LocalStorage` e redirecionamento gracioso para `/`.
- **Risco: Usuário sem perfil de estoque atribuído (`PROFILE_UNASSIGNED`).**
  *Mitigação:* Se o usuário autenticado não possuir `inventory_profile_id`, a interface deve indicar o status `"Sem perfil atribuído"` e orientar contato com o Administrador/Líder, sem quebrar o carregamento da página.
- **Risco: Exposição de segredos ou URLs de ambiente.**
  *Mitigação:* Utilização de `os.getenv("XANO_API_BASE_URL")` com documentação clara no `.env.example` e garantia de que tokens e credenciais não sejam registrados em arquivos de log.

## Critérios para considerar a autenticação concluída

1. O endpoint `GET /auth/me` no Xano retorna `inventory_profile_id` no payload JSON.
2. O usuário consegue submeter e-mail e senha válidos e é redirecionado para `/dashboard`.
3. Tentativas com credenciais incorretas exibem mensagem amigável de erro e mantêm o usuário na página de login.
4. O token JWT é armazenado em `rx.LocalStorage` e reutilizado para recuperar os dados do usuário via `GET auth/me`.
5. Ao recarregar a página (F5) em uma rota protegida, a sessão é mantida sem exigir novo login.
6. O cabeçalho da aplicação exibe o nome e o perfil do usuário logado (Líder, Almoxarife ou Auxiliar).
7. Usuários não autenticados que tentam acessar `/dashboard` ou outras rotas internas são redirecionados para `/`.
8. O botão "Sair" remove o token, reseta o estado e redireciona para a página de login.
9. A URL da API do Xano é configurada exclusivamente via variável de ambiente.
