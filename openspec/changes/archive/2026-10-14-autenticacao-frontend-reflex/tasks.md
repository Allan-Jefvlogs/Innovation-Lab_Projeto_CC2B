# Tasks: Autenticação no Frontend Reflex

## 1. Ajuste no Backend Xano (`auth/me`)

- [x] 1.1 Atualizar `xano/api/authentication/auth/me_GET.xs` adicionando o campo `"inventory_profile_id"` ao array `output` da consulta do usuário.
- [x] 1.2 Validar a sintaxe do arquivo `me_GET.xs` através do Xano Developer MCP (`xano_validate_xanoscript`).

## 2. Preparação e Configuração de Ambiente

- [x] 2.1 Criar o arquivo de exemplo de ambiente `.env.example` documentando a variável `XANO_API_BASE_URL`.
- [x] 2.2 Confirmar a disponibilidade da biblioteca `httpx` no ambiente virtual (`requirements.txt`).
- [x] 2.3 Criar a estrutura dos diretórios de suporte `Meu_projeto/services` e `Meu_projeto/state`.

## 3. Implementar Serviço de Comunicação com Xano

- [x] 3.1 Criar `Meu_projeto/services/xano_client.py` com leitura resiliente de `XANO_API_BASE_URL`.
- [x] 3.2 Implementar método assíncrono `login(email, password)` consumindo o endpoint `POST auth/login` do Xano.
- [x] 3.3 Implementar método assíncrono `get_current_user(token)` consumindo o endpoint `GET auth/me` com cabeçalho Bearer, retornando `id`, `name`, `email`, `role` e `inventory_profile_id`.
- [x] 3.4 Implementar tratamento de exceções de transporte (`httpx.RequestError`), timeouts e mapeamento dos envelopes de erro (401/403).

## 4. Implementar Gerenciamento de Estado de Autenticação

- [x] 4.1 Criar `Meu_projeto/state/auth.py` definindo a classe `AuthState(rx.State)`.
- [x] 4.2 Declarar variável reativa persistente `auth_token: str = rx.LocalStorage(name="auth_token")`.
- [x] 4.3 Declarar variáveis de sessão do usuário: `user_id`, `user_name`, `user_email`, `inventory_profile_id`, `profile_display_name`, `is_authenticated`, `is_loading` e `error_message`.
- [x] 4.4 Implementar event handler `submit_login` com validação de campos, chamada ao serviço, tratamento de loading e redirecionamento para `/dashboard`.
- [x] 4.5 Implementar event handler `load_user_profile` com mapeamento dos perfis conceituais baseado em `inventory_profile_id` (`Líder`, `Almoxarife`, `Auxiliar de almoxarifado`, `Sem perfil atribuído`).
- [x] 4.6 Implementar event handler `logout` que limpa o token no `rx.LocalStorage`, reseta os dados do usuário e redireciona para `/`.
- [x] 4.7 Implementar hook `require_auth` para verificação de sessão nas rotas protegidas com redirecionamento de usuários não autenticados.
- [x] 4.8 Implementar hook `check_already_logged_in` na tela de login para redirecionar usuários com sessão ativa diretamente para o dashboard.

## 5. Atualizar a Interface da Página de Login

- [x] 5.1 Atualizar `Meu_projeto/pages/login.py` substituindo o estado mock pelo `AuthState`.
- [x] 5.2 Conectar os campos de entrada de e-mail e senha e o botão "Entrar" ao manipulador `AuthState.login`.
- [x] 5.3 Adicionar indicador de carregamento reativo no botão "Entrar" (`loading=AuthState.is_loading`).
- [x] 5.4 Implementar banner/alerta visual condicional para exibição amigável de `AuthState.error_message`.
- [x] 5.5 Configurar hook `on_load=AuthState.check_already_logged_in` na página de login.

## 6. Integrar Autenticação ao Layout Global e Rotas

- [x] 6.1 Atualizar `Meu_projeto/components/layout.py` substituindo o texto fixo `"Admin • Usuário mock"` pelos dados dinâmicos `AuthState.user_name` e `AuthState.profile_display_name`.
- [x] 6.2 Conectar o botão/link "Sair" da barra lateral ao manipulador `AuthState.logout`.
- [x] 6.3 Configurar o hook `on_load=AuthState.require_auth` nas páginas do sistema em `Meu_projeto/Meu_projeto.py` (`dashboard`, `produtos`, `categorias`, etc.).
- [x] 6.4 Estender o guard central `AuthState.require_auth` para validar a rota atual pelo `inventory_profile_id`, preservar o redirecionamento de sessão não autenticada para `/` e encaminhar rotas não permitidas para `/dashboard`.

## 7. Validação e Testes Funcionais

- [x] 7.1 Testar autenticação bem-sucedida com credenciais válidas e verificar redirecionamento automático para `/dashboard`.
- [x] 7.2 Testar autenticação com e-mail inexistente ou senha incorreta e confirmar exibição da mensagem de erro sem navegação.
- [x] 7.3 Testar tentativa de acesso direto via URL a uma rota protegida (ex.: `/dashboard` ou `/produtos`) sem token e confirmar redirecionamento para `/`.
- [x] 7.4 Testar recarregamento de página (F5) em rota protegida e verificar manutenção da sessão via `rx.LocalStorage` e exibição correta do nome e perfil do usuário.
- [x] 7.5 Testar execução do logout na sidebar e confirmar limpeza do token no armazenamento local e retorno à tela de login.
- [x] 7.6 Testar comportamento visual em caso de simulação de indisponibilidade do backend Xano.
- [x] 7.7 Executar `git status` e `git diff` para revisar a conformidade de todas as alterações com os objetivos da change.
- [x] 7.8 Testar como Líder o acesso direto a todas as rotas internas.
- [x] 7.9 Testar como Almoxarife as rotas permitidas, o acesso a `/produtos/novo` e o redirecionamento de `/usuarios` e `/perfis` para `/dashboard`.
- [x] 7.10 Testar como Auxiliar a autorização operacional por grants: `product.create`, `product.update`, `stock.entry` e `stock.exit` devem permitir suas respectivas rotas/ações quando concedidos e bloquear o acesso direto quando ausentes. Confirmar também que `/usuarios` e `/perfis` permanecem exclusivos ao Líder (`administrator`), independentemente de grants operacionais.
- [x] 7.11 Testar a autorização independente de Histórico e Relatórios: `movement.read` permite `/movimentacoes` e sua ausência bloqueia a rota; `report.read` permite `/relatorios` e sua ausência bloqueia a rota. Confirmar ainda que sessão autenticada sem perfil/grants operacionais pode permanecer em `/dashboard`, sem ciclo, e que sessão não autenticada continua redirecionada para `/`.
