# integracao-usuarios Specification

## Purpose
Esta capability define o gerenciamento de usuários no NexStock, incluindo associação a perfis, autenticação e autorização, senhas temporárias com troca obrigatória, ativação e inativação, e bloqueio de contas inativas. A inativação preserva os registros históricos e as movimentações associados ao usuário.

## Requirements

### Requirement: Status de usuário sem exclusão

O sistema MUST persistir `is_active` na tabela `user`, com padrão ativo. A listagem administrativa MUST mostrar Ativo ou Inativo. Somente o Líder MUST poder inativar ou reativar um usuário por ação separada, com confirmação. A ação MUST alterar apenas o status, preservando histórico, movimentações, senha, perfil e `must_change_password`.

#### Scenario: Inativar e reativar
- **WHEN** o Líder confirma a inativação ou reativação de outro usuário
- **THEN** o backend atualiza apenas `is_active` e a listagem reflete o estado persistido

### Requirement: Bloqueio da conta inativa

O login MUST recusar conta inativa após verificar as credenciais. `/auth/me` MUST recusar token de conta inativa, fazendo o frontend limpar a sessão e voltar ao Login. A autorização central MUST recusar chamadas protegidas de conta inativa. A troca inicial de senha também MUST recusar conta inativa.

#### Scenario: Token anterior à inativação
- **WHEN** um usuário inativado tenta restaurar a sessão ou chamar API de estoque com token antigo
- **THEN** o acesso é recusado e o frontend elimina o token

#### Scenario: Reativação com troca pendente
- **WHEN** o Líder reativa uma conta com `must_change_password=true`
- **THEN** a flag permanece e o próximo login conduz a `/alterar-senha`

### Requirement: Proteção do Líder

O backend MUST recusar a autoinativação do Líder. Antes de inativar outro Líder, MUST verificar que permanece pelo menos um Líder ativo. O frontend MUST ocultar a ação de inativação do próprio Líder.

#### Scenario: Autoinativação
- **WHEN** o Líder tenta inativar sua própria conta
- **THEN** o backend recusa a operação com erro específico

### Requirement: Administração de usuários

O sistema MUST permitir somente ao Líder listar, buscar, criar e editar usuários com paginação backend. A criação MUST exigir nome, e-mail único, perfil real, senha inicial e confirmação. A listagem e a edição MUST NOT retornar senha nem hash.

#### Scenario: Criar usuário
- **WHEN** o Líder envia um cadastro válido
- **THEN** o Xano grava a senha no campo nativo `user.password`, associa o perfil e marca `must_change_password=true`

#### Scenario: Editar dados cadastrais
- **WHEN** o Líder edita nome, e-mail ou perfil
- **THEN** o PATCH comum atualiza apenas esses campos e preserva a senha

### Requirement: Reset administrativo separado

O Líder MUST poder substituir a senha por uma nova senha temporária somente por ação explícita de reset. O endpoint MUST exigir autorização `administrator`, validar confirmação, gravar a senha nativa e marcar `must_change_password=true`. MUST NOT devolver a senha ou o hash.

#### Scenario: Resetar senha
- **WHEN** o Líder confirma o reset de um usuário
- **THEN** a senha anterior é substituída e a troca obrigatória fica pendente

### Requirement: Troca obrigatória pelo próprio usuário

O usuário autenticado com `must_change_password=true` MUST ser encaminhado para `/alterar-senha`. As APIs de estoque que usam a autorização central MUST negar acesso até a troca. O endpoint de troca MUST usar `$auth.id`, MUST NOT aceitar ID arbitrário e MUST marcar a flag como falsa após gravar a senha definitiva.

#### Scenario: Primeiro login
- **WHEN** um usuário com senha temporária entra e `/auth/me` retorna a flag verdadeira
- **THEN** ele é levado a `/alterar-senha` e não acessa as demais rotas protegidas

#### Scenario: Troca concluída
- **WHEN** o usuário informa nova senha válida e confirmação igual
- **THEN** o Xano grava a senha e limpa a flag; o frontend encerra a sessão, volta ao Login e informa o sucesso

### Requirement: Proteção e visibilidade

Os controles de olho MUST alternar apenas a visibilidade das senhas digitadas no cadastro, reset e troca obrigatória. Senhas MUST NOT ser consultadas, persistidas no State ou registradas em logs. A edição cadastral MUST NOT mostrar campos de senha.

#### Scenario: Abrir edição
- **WHEN** o Líder abre o formulário de edição
- **THEN** aparecem somente nome, e-mail, perfil e a ação separada de reset

### Requirement: Perfil administrativo protegido

O Líder MUST NOT alterar o próprio perfil pelo PATCH cadastral. Os perfis disponíveis MUST vir dos registros reais de `inventory_profile` já expostos por `GET /permissions`.

#### Scenario: Rebaixamento próprio
- **WHEN** o Líder tenta alterar seu próprio perfil
- **THEN** o Xano recusa a operação

### Requirement: Comparação segura do status de atividade

Comparações de `is_active` MUST usar semântica estrita para bloquear o booleano `false`. `null` MUST continuar compatível como ativo para registros legados. A regra MUST valer em login, restauração de sessão, autorização central, troca de senha e login/alteração de senha por link de redefinição.

#### Scenario: Conta inativa em qualquer fluxo autenticado
- **WHEN** `is_active=false` e o usuário tenta login, `/auth/me`, consultar uma API protegida ou usar fluxo de senha autenticado
- **THEN** o backend recusa a operação com `USER_INACTIVE` antes de conceder dados ou alterar a senha

#### Scenario: Conta legada sem status
- **WHEN** `is_active=null`
- **THEN** o backend mantém a compatibilidade de conta ativa
