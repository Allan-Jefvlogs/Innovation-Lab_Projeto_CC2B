# Specification: Integração do módulo de Categorias

## ADDED Requirements

### Requirement: Categorias usam dados reais do Xano

A rota `/categorias` MUST exigir a sessão existente e carregar Categorias paginadas de `GET /categories`. A tabela MUST exibir somente ID, nome, status e ação; MUST NOT conter registros, IDs, nomes, status ou quantidades de Produtos mockados. A contagem de Produtos MUST ficar fora desta versão.

#### Scenario: Listagem de Categorias

- **WHEN** usuário autorizado abre `/categorias`
- **THEN** Reflex carrega todas as páginas reais do Xano e apresenta loading, erro ou estado vazio apropriado

#### Scenario: Buscar Categoria

- **WHEN** usuário informa parte do nome
- **THEN** a busca local encontra substrings sem diferenciar caixa ou acentos e não altera o texto exibido

### Requirement: Criar Categoria

O botão `Nova categoria` MUST abrir um modal com nome obrigatório. Reflex MUST trimar e bloquear nome vazio antes do request, evitar submissões simultâneas e chamar `POST /categories` com o token da sessão. O Xano MUST trimar e validar o nome, rejeitar vazio e duplicidade e criar status `ativo`. Em sucesso, a interface MUST fechar o modal, limpar o campo, atualizar a lista e mostrar `Categoria criada com sucesso.`. Duplicidade MUST mostrar `Já existe uma categoria com esse nome.`; erro inesperado MUST mostrar `Não foi possível criar a categoria.`.

#### Scenario: Nome vazio

- **WHEN** usuário tenta salvar um nome vazio ou composto de espaços
- **THEN** o request MUST NOT ser enviado e a interface mostra `Informe o nome da categoria.`

#### Scenario: Nome duplicado

- **WHEN** Xano rejeita a criação por duplicidade
- **THEN** a interface mostra `Já existe uma categoria com esse nome.` e mantém o modal aberto

### Requirement: Alterar status sem perda do vínculo

A última coluna MUST conter switch controlado por status. Ativar MUST chamar `PATCH /categories/by_id/{id}/activate`; inativar MUST chamar `PATCH /categories/by_id/{id}/inactivate`. Reflex MUST atualizar o status visual somente com o estado confirmado pela resposta do Xano. Em erro, o estado anterior MUST permanecer e uma mensagem amigável MUST ser mostrada. A operação MUST alterar status, nunca excluir a Categoria nem alterar Produtos associados.

#### Scenario: Inativar e reativar

- **WHEN** Líder desliga ou liga o switch
- **THEN** o endpoint PATCH correspondente MUST persistir `inativo` ou `ativo` e a lista MUST refletir a resposta confirmada

#### Scenario: Erro de atualização

- **WHEN** a API rejeita ou falha ao mudar status
- **THEN** o switch MUST continuar refletindo o status anterior e a interface mostra erro

#### Scenario: Preservar referência de Produto

- **WHEN** Categoria associada a Produto é inativada
- **THEN** a Categoria e o vínculo permanecem; criação de Produto lista somente Categorias ativas e edição mantém a referência inativa atual

### Requirement: Permissões de Categoria permanecem no backend

Leitura MUST exigir `category.read`; criação MUST exigir `category.create`; ativação MUST exigir `category.update`; inativação MUST exigir `category.inactivate`. A integração MUST preservar os grants existentes e MUST NOT substituir autorização do Xano por controle visual.

#### Scenario: Perfil sem grant de escrita

- **WHEN** Almoxarife ou Auxiliar sem grant de mutação abre a tela
- **THEN** pode consultar conforme `category.read`, não vê controles de escrita e o Xano continua rejeitando chamadas sem grant

### Requirement: Interface de escrita respeita grants independentes

A interface MUST usar os grants efetivos retornados por `/auth/me` em `AuthState.permission_codes`, por meio dos mecanismos de autorização já existentes. Ela MUST NOT inferir permissões de escrita a partir de um ID fixo de perfil. O botão `Nova categoria` MUST aparecer somente com `category.create`, e tanto a abertura quanto o salvamento do formulário MUST conferir novamente esse grant. Para categoria ativa, o switch MUST permitir interação somente com `category.inactivate`; para categoria inativa, somente com `category.update`. O evento de status MUST revalidar o grant correspondente ao status atual, inclusive quando invocado diretamente. A rota `/categorias` MUST permanecer protegida por `category.read`. O Xano continua como autoridade final.

#### Scenario: Acesso à página por `category.read`

- **WHEN** usuário com `category.read` abre `/categorias`
- **THEN** pode visualizar a página independentemente dos grants de escrita; usuário sem `category.read` continua bloqueado pela proteção existente da rota

#### Scenario: Exibição e abertura do cadastro

- **WHEN** usuário não possui `category.create`
- **THEN** o botão `Nova categoria` não aparece e uma chamada direta ao evento de abertura não exibe o formulário

#### Scenario: Revalidação ao salvar cadastro

- **WHEN** usuário sem `category.create` chama diretamente o evento de salvamento ou perde o grant depois de abrir o formulário
- **THEN** o State rejeita o cadastro sem enviar o request ao Xano

#### Scenario: Ação do switch conforme status

- **WHEN** categoria está ativa
- **THEN** o switch só pode ser usado por quem possui `category.inactivate`; quando está inativa, só pode ser usado por quem possui `category.update`

#### Scenario: Revalidação do evento de status

- **WHEN** usuário sem o grant correspondente chama diretamente o evento de status
- **THEN** o State rejeita a operação e preserva o status anterior
