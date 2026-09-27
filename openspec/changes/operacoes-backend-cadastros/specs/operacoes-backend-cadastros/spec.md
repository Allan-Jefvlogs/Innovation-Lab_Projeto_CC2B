# operacoes-backend-cadastros Specification

## Purpose

Esta capability define o contrato verificável das operações backend no Xano para Categoria, Produto e Fornecedor, além de perfis, permissões por perfil, atribuição de perfil pelo Líder e auditoria das alterações de permissões. O Xano é a autoridade para autenticação, autorização, validação e integridade. A interface Reflex de cadastros e permissões, a movimentação de estoque e os endpoints quick-start de contas e papéis permanecem fora do modelo de autorização desta capability.

## ADDED Requirements

### Requirement: As operações desta capability MUST exigir autenticação no backend

Todos os endpoints de cadastro, consulta ou alteração de permissões e atribuição de perfil definidos nesta capability MUST exigir identidade autenticada. Autenticação MUST ser avaliada antes da autorização e antes de qualquer leitura ou alteração protegida.

#### Scenario: Requisição sem identidade autenticada

- **WHEN** uma requisição chega a qualquer endpoint desta capability sem token válido
- **THEN** o Xano MUST rejeitá-la como falha de autenticação antes de executar a operação
- **AND** nenhum dado protegido MUST ser retornado nem qualquer estado MUST ser alterado

#### Scenario: Identidade autenticada

- **WHEN** uma requisição chega com token válido
- **THEN** o backend MUST identificar o usuário por `$auth.id`
- **AND** MUST continuar avaliando o perfil e a autorização exigida pelo endpoint

### Requirement: O sistema MUST representar os três perfis de domínio separadamente do papel quick-start

O backend MUST representar os perfis de domínio `administrator`, `stockkeeper` e `read_only`, apresentados como Líder, Almoxarife e Auxiliar de almoxarifado, respectivamente. Cada conta atribuída MUST referenciar exatamente um perfil válido por `user.inventory_profile_id`. Contas ainda não atribuídas MAY manter esse campo nulo, mas MUST falhar fechadas em todos os endpoints protegidos do estoque.

O papel quick-start `user.role` (`admin`/`member`) MUST NOT ser convertido automaticamente nem usado como perfil ou autorização para operações do Sistema de Gerenciamento de Estoque.

#### Scenario: Usuário atribuído a perfil válido

- **WHEN** um usuário autenticado possui referência a um dos três perfis de domínio
- **THEN** a autorização MUST usar esse perfil para decidir acesso às funcionalidades do estoque
- **AND** MUST NOT inferir outro perfil a partir de `user.role`

#### Scenario: Usuário sem perfil ou com vínculo inválido

- **WHEN** um usuário autenticado não possui perfil ou sua referência não resolve para perfil válido
- **THEN** os endpoints protegidos do estoque MUST negar a operação com erro de perfil não atribuído ou inválido
- **AND** nenhum grant MUST ser concedido implicitamente

#### Scenario: Papel quick-start não concede privilégio de domínio

- **WHEN** um usuário possui `user.role` igual a `admin` ou `member`, mas não tem perfil de domínio atribuído
- **THEN** esse papel MUST NOT conceder qualquer permissão para os endpoints desta capability

### Requirement: O Líder MUST atribuir perfis sem permitir autoalteração

O signup MUST NOT usar `inventory_profile_id` nem `profile_code` fornecido pelo cliente para atribuir um perfil. O usuário MUST NOT escolher o próprio perfil e uma conta criada por signup MUST permanecer sem perfil até atribuição pelo Líder. No funcionamento normal da aplicação, somente o Líder autenticado pode atribuir a uma conta um dos três perfis de domínio, inclusive a usuários existentes e novos, por operação protegida no backend. A única exceção é o bootstrap inicial, executado por operador confiável do workspace antes de existir Líder e descrito no cenário específico abaixo. A atribuição normal MUST aceitar somente `profile_code` e MUST rejeitar tentativa do Líder de alterar o próprio perfil.

#### Scenario: Líder atribui perfil a outro usuário

- **WHEN** o Líder envia perfil válido para uma conta alvo diferente de si próprio
- **THEN** o backend MUST persistir a referência do perfil alvo
- **AND** MUST retornar a atribuição efetiva

#### Scenario: Usuário tenta escolher perfil no signup

- **WHEN** um cliente de signup inclui ou escolhe `inventory_profile_id` ou `profile_code`
- **THEN** o fluxo de signup MUST criar a conta sem perfil, mantendo `user.inventory_profile_id` nulo independentemente dos valores enviados
- **AND** MUST NOT usar `inventory_profile_id` nem `profile_code` do cliente para atribuir perfil
- **AND** a atribuição MUST permanecer exclusiva do Líder

#### Scenario: Tentativa de autoalteração de perfil

- **WHEN** o Líder solicita atribuir outro perfil à própria conta
- **THEN** o backend MUST rejeitar a operação sem alterar o vínculo

#### Scenario: Bootstrap único do primeiro Líder

- **WHEN** ainda não existe conta com perfil `administrator` e um operador confiável do workspace executa a função interna de bootstrap para usuário existente cuja identidade foi confirmada pelo grupo
- **THEN** o backend MUST atribuir `administrator` ao usuário e registrar o marcador único de bootstrap na mesma transação
- **AND** a função MUST NOT estar exposta por endpoint HTTP ou disponível a usuários autenticados da aplicação
- **AND** qualquer execução posterior MUST ser rejeitada sem atribuir outro perfil
- **AND** depois do bootstrap, somente um Líder autenticado MUST poder atribuir perfis pela operação protegida normal
- **AND** o signup MUST NOT converter `admin/member` nem escolher automaticamente o alvo

#### Scenario: Perfil desconhecido ou ator não Líder

- **WHEN** um não-Líder tenta atribuir perfil ou o Líder envia código de perfil desconhecido
- **THEN** o backend MUST rejeitar a operação sem alterar a conta alvo

### Requirement: O backend MUST persistir perfis e permissões com catálogo controlado

O backend MUST manter catálogo de três perfis, catálogo dos doze códigos de permissão cobertos nesta capability e relação de grants por perfil com unicidade por par perfil-permissão. Grants MUST NOT existir para `administrator`; sua autorização MUST ser integral e implícita, sem grants editáveis que possam restringi-la. `stockkeeper` e `read_only` MAY possuir zero ou mais grants persistidos; a lista vazia `[]` MUST ser válida para ambos.

Os códigos cobertos são `category.read`, `category.create`, `category.update`, `category.inactivate`, `product.read`, `product.create`, `product.update`, `product.inactivate`, `supplier.read`, `supplier.create`, `supplier.update` e `supplier.inactivate`.

#### Scenario: Matriz inicial

- **WHEN** os perfis e permissões iniciais forem provisionados
- **THEN** Líder MUST ter acesso integral às operações do estoque
- **AND** Almoxarife MUST poder consultar Categoria, Produto e Fornecedor e criar, alterar e inativar Produto e Fornecedor
- **AND** Auxiliar de almoxarifado MUST poder consultar Categoria, Produto e Fornecedor
- **AND** as demais operações de Categoria, Produto e Fornecedor MUST ser negadas a Almoxarife e Auxiliar conforme a matriz aprovada

#### Scenario: Líder tenta restringir a si próprio

- **WHEN** uma requisição tenta alterar grants do perfil `administrator` ou restringir o acesso integral do Líder
- **THEN** o backend MUST rejeitar a alteração
- **AND** a autorização do Líder MUST permanecer integral

#### Scenario: Perfil não-Líder sem grants

- **WHEN** o Líder remove todos os grants de Almoxarife ou Auxiliar
- **THEN** o backend MUST persistir a lista vazia
- **AND** o perfil alvo MUST permanecer autenticável, sem permissão implícita para operações de cadastro
- **AND** o Líder MUST poder atribuir grants ao perfil posteriormente

### Requirement: O backend MUST autorizar cada operação com o grant específico

Depois de autenticar a identidade e resolver o perfil atual no banco, cada endpoint MUST verificar a permissão específica necessária antes de retornar dados ou alterar estado. O Líder MUST ter bypass integral para as funcionalidades do Sistema de Gerenciamento de Estoque. Outros perfis MUST possuir o grant persistido correspondente.

#### Scenario: Operação autorizada

- **WHEN** o usuário possui o perfil ou grant exigido pelo endpoint
- **THEN** o backend MUST executar a operação após as validações de entrada e domínio

#### Scenario: Operação sem grant

- **WHEN** o usuário está autenticado, mas não possui o grant exigido
- **THEN** o backend MUST rejeitar a operação como falha de autorização
- **AND** nenhuma alteração MUST ser confirmada

#### Scenario: Grant revogado com token ainda válido

- **WHEN** um grant é removido e o usuário faz uma nova requisição com o mesmo token autenticado
- **THEN** a nova requisição MUST usar os grants persistidos atuais
- **AND** MUST negar a operação se o grant necessário foi removido

### Requirement: O backend MUST expor consulta e substituição controlada de permissões

`GET /permissions` MUST estar disponível somente ao Líder e retornar o catálogo e a matriz efetiva dos três perfis, incluindo a natureza integral e imutável do acesso do Líder e a revisão de cada perfil editável.

`PATCH /permissions/profiles/{profile_code}` MUST estar disponível somente ao Líder e aceitar a lista completa de permissões desejada mais `permission_revision`. Alvos válidos são somente `stockkeeper` e `read_only`. A lista vazia MUST ser válida. Códigos desconhecidos ou duplicados, alvos inválidos, tentativa de editar `administrator` e revisão obsoleta MUST ser rejeitados sem alteração parcial.

#### Scenario: Consulta por Líder

- **WHEN** o Líder solicita `GET /permissions`
- **THEN** o backend MUST retornar o catálogo e os grants efetivos por perfil
- **AND** MUST identificar que o acesso do Líder é integral e não editável

#### Scenario: Consulta ou alteração por não-Líder

- **WHEN** Almoxarife, Auxiliar ou usuário sem perfil chama um endpoint de gerenciamento de permissões
- **THEN** o backend MUST negar a chamada sem revelar ou alterar a matriz

#### Scenario: Substituição válida, inclusive lista vazia

- **WHEN** o Líder envia lista completa válida para `stockkeeper` ou `read_only` com revisão atual
- **THEN** o backend MUST substituir os grants daquele perfil pela lista recebida
- **AND** MUST incrementar `permission_revision` e retornar a matriz persistida e a nova revisão
- **AND** a operação MUST ser atômica

#### Scenario: Entrada inválida ou conflito de revisão

- **WHEN** a lista contém código desconhecido/repetido, o alvo é imutável ou a revisão está obsoleta
- **THEN** o backend MUST rejeitar a chamada com erro distinguível
- **AND** grants, revisão e auditoria MUST permanecer sem alteração

#### Scenario: Duas substituições concorrentes com a mesma revisão

- **WHEN** duas substituições para o mesmo perfil usam simultaneamente a mesma `permission_revision`
- **THEN** no máximo uma MUST confirmar grants, revisão e auditoria
- **AND** a outra MUST ser rejeitada com `PERMISSION_REVISION_CONFLICT` após rollback integral

### Requirement: O sistema MUST auditar alterações de permissões confirmadas

O backend MUST registrar cada alteração de permissões confirmada em tabela dedicada append-only `inventory_permission_audit`. O evento MUST conter ator autenticado, perfil alvo, revisão anterior, nova revisão, permissões adicionadas e permissões removidas. O registro MUST ocorrer na mesma transação da substituição dos grants. Esta capability MUST NOT fornecer endpoint de consulta, edição ou exclusão de eventos de auditoria.

#### Scenario: Alteração confirmada

- **WHEN** uma substituição válida de grants é confirmada
- **THEN** o backend MUST persistir os grants e o evento de auditoria na mesma transação
- **AND** o evento MUST registrar ator, alvo, revisões e diferenças de permissões

#### Scenario: Auditoria falha

- **WHEN** não é possível persistir o evento de auditoria
- **THEN** a transação MUST reverter também a alteração dos grants e da revisão

#### Scenario: Chamada rejeitada

- **WHEN** uma tentativa de alteração é inválida, não autorizada ou conflita com a revisão
- **THEN** nenhum evento de alteração confirmada MUST ser gravado

### Requirement: O backend MUST fornecer operações de Categoria protegidas

O grupo Xano `Inventory Catalog`, com canonical `gestao-estoque-cadastros`, MUST expor, com autenticação e grant correspondente, `GET /categories`, `GET /categories/by_id/{category_id}`, `POST /categories`, `PATCH /categories/by_id/{category_id}` e `PATCH /categories/by_id/{category_id}/inactivate`.

#### Scenario: Criar Categoria

- **WHEN** usuário com `category.create` envia `nome` válido
- **THEN** o backend MUST criar a Categoria com ID estável e status inicial `ativo`
- **AND** MUST retornar o registro criado

#### Scenario: Listar e consultar Categoria

- **WHEN** usuário com `category.read` lista ou consulta Categoria
- **THEN** o backend MUST retornar os registros compatíveis com filtros, status e paginação definidos
- **AND** detalhe de ID inexistente MUST retornar erro `NOT_FOUND`

#### Scenario: Alterar Categoria

- **WHEN** usuário com `category.update` envia PATCH com `nome` permitido
- **THEN** o backend MUST atualizar somente campos permitidos e retornar o estado atualizado
- **AND** MUST rejeitar body vazio ou campos não permitidos

### Requirement: O backend MUST fornecer operações de Produto protegidas

O grupo `Inventory Catalog` MUST expor, com autenticação e grant correspondente, `GET /products`, `GET /products/by_id/{product_id}`, `POST /products`, `PATCH /products/by_id/{product_id}` e `PATCH /products/by_id/{product_id}/inactivate`.

#### Scenario: Criar Produto

- **WHEN** usuário com `product.create` envia `codigo`, `nome`, `categoria_id`, `unidade_medida`, `estoque_minimo` válido e `descricao` opcional
- **THEN** o backend MUST persistir o Produto com status inicial `ativo` e retornar o registro criado
- **AND** MUST NOT aceitar `id`, `status` ou `estoque_atual` enviados pelo cliente

#### Scenario: Consultar Produto

- **WHEN** usuário com `product.read` lista ou consulta Produto
- **THEN** o backend MUST retornar registros com filtros e paginação definidos e incluir a referência `categoria_id`
- **AND** detalhe de ID inexistente MUST retornar `NOT_FOUND`

#### Scenario: Alterar Produto

- **WHEN** usuário com `product.update` envia PATCH com campos mutáveis válidos
- **THEN** o backend MUST alterar somente os campos permitidos e retornar o Produto atualizado
- **AND** MUST rejeitar body vazio, `id`, `status` e outros campos não permitidos

### Requirement: O backend MUST fornecer operações de Fornecedor protegidas

O grupo `Inventory Catalog` MUST expor, com autenticação e grant correspondente, `GET /suppliers`, `GET /suppliers/by_id/{supplier_id}`, `POST /suppliers`, `PATCH /suppliers/by_id/{supplier_id}` e `PATCH /suppliers/by_id/{supplier_id}/inactivate`.

#### Scenario: Criar Fornecedor

- **WHEN** usuário com `supplier.create` envia `nome_razao_social`, `tipo_documento` (`CPF` ou `CNPJ`) e `documento`, com `contato` e `endereco` opcionais
- **THEN** o backend MUST criar Fornecedor com ID estável e status inicial `ativo`
- **AND** MUST retornar o registro criado

#### Scenario: Consultar Fornecedor

- **WHEN** usuário com `supplier.read` lista ou consulta Fornecedor
- **THEN** o backend MUST aplicar os filtros e paginação definidos e retornar os dados persistidos
- **AND** detalhe de ID inexistente MUST retornar `NOT_FOUND`

#### Scenario: Alterar Fornecedor

- **WHEN** usuário com `supplier.update` envia PATCH com campos mutáveis válidos
- **THEN** o backend MUST alterar somente os campos permitidos e retornar o registro atualizado
- **AND** MUST rejeitar body vazio e campos não permitidos

### Requirement: O backend MUST aplicar contratos comuns de consulta e atualização

As listagens MUST aceitar `page` padrão `1`, `per_page` padrão `20` e limite máximo `100`, com ordenação estável por ID ascendente e envelope paginado Xano. Sem filtro de status, listagens MUST incluir registros ativos e inativos. Categoria MUST aceitar filtro `status`; Produto MUST aceitar `status` e `categoria_id`; Fornecedor MUST aceitar `status` e `tipo_documento`.

PATCH de cadastro MUST ser parcial e permitir somente os campos mutáveis definidos no Design: Categoria (`nome`); Produto (`codigo`, `nome`, `descricao`, `categoria_id`, `unidade_medida`, `estoque_minimo`, além do controle `limpar_descricao`); Fornecedor (`nome_razao_social`, `tipo_documento`, `documento`, `contato`, `endereco`, além dos controles `limpar_contato` e `limpar_endereco`). Omissão MUST preservar valor existente. Para os opcionais limpáveis, valor não nulo MUST atualizar; a flag de limpeza correspondente igual a `true`, sem valor correspondente, MUST definir o valor persistido como `null`; flag igual a `false` sem valor correspondente MUST preservar o valor. Envio direto de `null` no campo de valor MUST ser rejeitado como `INVALID_INPUT`. Campo de valor e flag correspondente `true` no mesmo PATCH MUST ser rejeitados como `INVALID_INPUT`. Flags são controles e MUST NOT ser persistidas. PATCH sem alteração efetiva MUST ser rejeitado. `id` e `status` MUST NOT ser alteráveis por PATCH genérico.

#### Scenario: Paginação e filtro

- **WHEN** uma listagem recebe filtros e parâmetros válidos de paginação
- **THEN** o backend MUST retornar somente resultados filtrados na página solicitada e os metadados `itemsReceived`, `curPage`, `nextPage`, `prevPage`, `offset`, `perPage` e `items`
- **AND** MUST rejeitar valores de paginação ou filtro inválidos

#### Scenario: PATCH parcial preserva omissões

- **WHEN** PATCH contém pelo menos um campo permitido e omite outros campos existentes
- **THEN** o backend MUST alterar somente os campos enviados
- **AND** MUST rejeitar campo imutável/desconhecido ou body sem campo mutável

#### Scenario: PATCH preserva campo opcional omitido

- **WHEN** PATCH omite `descricao`, `contato` ou `endereco` e não ativa sua flag de limpeza
- **THEN** o backend MUST preservar o valor persistido correspondente

#### Scenario: PATCH atualiza campo opcional com valor não nulo

- **WHEN** PATCH envia valor não nulo para `descricao`, `contato` ou `endereco` sem ativar a flag correspondente
- **THEN** o backend MUST atualizar somente o campo enviado

#### Scenario: PATCH limpa campo opcional por flag explícita

- **WHEN** PATCH envia `limpar_descricao`, `limpar_contato` ou `limpar_endereco` igual a `true` sem enviar o campo de valor correspondente
- **THEN** o backend MUST definir somente o campo correspondente como `null`
- **AND** MUST NOT persistir as flags de limpeza

#### Scenario: PATCH rejeita null direto e combinação conflitante

- **WHEN** PATCH envia `null` diretamente em campo de valor opcional ou envia campo de valor junto da flag correspondente igual a `true`
- **THEN** o backend MUST rejeitar a requisição com `INVALID_INPUT` sem alterar o registro

#### Scenario: Flag de limpeza falsa não altera campo

- **WHEN** PATCH envia flag de limpeza igual a `false` sem o campo de valor correspondente
- **THEN** o backend MUST preservar o campo persistido
- **AND** se não houver outra alteração efetiva, MUST rejeitar o PATCH como `INVALID_INPUT`

### Requirement: O backend MUST validar a referência Produto–Categoria

Ao criar Produto, `categoria_id` MUST referenciar Categoria existente e ativa. Em PATCH, nova associação ou troca de Categoria MUST exigir Categoria existente e ativa. Alterações de outros campos de Produto já relacionado a Categoria posteriormente inativada MUST preservar o vínculo existente. Inativar Categoria MUST NOT remover nem alterar referências de Produto.

#### Scenario: Nova associação a Categoria inexistente ou inativa

- **WHEN** criação de Produto ou troca de `categoria_id` aponta para Categoria inexistente ou inativa
- **THEN** o backend MUST rejeitar a operação como regra de negócio
- **AND** nenhum Produto MUST ser criado ou alterado parcialmente

#### Scenario: Produto mantém vínculo histórico

- **WHEN** uma Categoria relacionada é inativada
- **THEN** os Produtos existentes MUST manter `categoria_id` e demais referências
- **AND** uma alteração de outro campo do Produto MUST poder preservar a associação sem criar novo vínculo

### Requirement: O backend MUST impor unicidade pelos valores armazenados

O backend MUST respeitar os índices únicos existentes em `category.nome`, `product.codigo` e `supplier.documento`, tanto em criação quanto em alteração. A unicidade MUST comparar valores armazenados e MUST NOT aplicar trim, conversão de caixa, remoção de pontuação, normalização automática ou validação adicional de CPF/CNPJ nesta capability. Checagem prévia MAY melhorar a resposta, mas a constraint persistente MUST continuar protegendo gravações concorrentes.

#### Scenario: Valor duplicado em criação ou alteração

- **WHEN** criação ou alteração tenta persistir valor já usado por outro registro no campo único correspondente
- **THEN** o backend MUST rejeitar a operação com erro distinguível `DUPLICATE_VALUE`
- **AND** o estado existente MUST permanecer íntegro

#### Scenario: Requisições concorrentes

- **WHEN** duas requisições concorrentes tentam gravar o mesmo valor único
- **THEN** no máximo uma MUST ser confirmada
- **AND** a outra MUST retornar conflito de duplicidade

#### Scenario: Variantes textuais

- **WHEN** valores diferem por espaços, caixa ou pontuação
- **THEN** o backend MUST aplicar a igualdade dos valores armazenados e MUST NOT canonizá-los automaticamente

### Requirement: O backend MUST inativar sem excluir ou quebrar referências

Os endpoints dedicados de inativação MUST alterar somente `status` para `inativo`. A operação MUST ser idempotente. Esta capability MUST NOT expor DELETE, excluir fisicamente registros ou remover referências existentes. Reativação fica fora do escopo.

#### Scenario: Inativar cadastro

- **WHEN** um usuário autorizado inativa Categoria, Produto ou Fornecedor
- **THEN** o registro MUST permanecer persistido com mesmo ID e referências e status `inativo`
- **AND** nenhuma exclusão física MUST ocorrer

#### Scenario: Inativar cadastro já inativo

- **WHEN** a operação de inativação é repetida para registro já inativo
- **THEN** o backend MUST retornar o estado inativo sem efeitos colaterais adicionais

### Requirement: Esta capability MUST NOT alterar estoque ou movimentações

Operações de Categoria, Produto, Fornecedor, atribuição de perfil e permissões MUST NOT criar ou alterar saldo de estoque nem criar, alterar ou excluir entradas, saídas ou histórico de movimentações. `estoque_minimo` MUST continuar sendo somente campo configurável de Produto.

#### Scenario: Alteração de cadastro

- **WHEN** qualquer operação desta capability cria, consulta, altera ou inativa cadastro
- **THEN** saldo disponível, estruturas de estoque e histórico de movimentações MUST permanecer inalterados

### Requirement: APIs quick-start MUST permanecer fora da autorização do estoque

O acesso integral do Líder definido nesta capability MUST abranger somente funcionalidades do Sistema de Gerenciamento de Estoque. `members_accounts` e `admin/user_role` MUST permanecer fora do helper/modelo de autorização do estoque e continuar usando o mecanismo legado `admin/member`.

#### Scenario: Acesso às APIs quick-start

- **WHEN** um usuário chama `members_accounts` ou `admin/user_role`
- **THEN** o acesso MUST continuar sujeito ao mecanismo legado `admin/member`
- **AND** o bypass integral do perfil Líder desta capability MUST NOT alterar a autorização dessas rotas

### Requirement: O backend MUST distinguir classes de erro

O contrato de erro MUST permitir distinguir autenticação, perfil ausente/inválido, autorização negada, entrada inválida, regra de negócio, não encontrado, duplicidade, perfil imutável e conflito de revisão. O erro MUST preservar um código estável além de mensagem legível.

#### Scenario: Falha por categoria de erro

- **WHEN** uma operação falha por autenticação, autorização, validação, regra de negócio, ausência de registro, duplicidade ou revisão obsoleta
- **THEN** o backend MUST retornar a categoria/código correspondente
- **AND** MUST NOT depender apenas de texto livre para que o cliente diferencie o resultado

## Acceptance Criteria

- Todas as rotas e permissões correspondem às tabelas do Design; cada endpoint autenticado verifica grant antes de ler ou escrever dados protegidos.
- As 36 combinações da matriz inicial (12 permissões × 3 perfis) produzem resultados esperados e o Líder mantém acesso integral.
- Usuários existentes e novos só recebem perfil por atribuição do Líder; `admin/member` não é convertido; signup não permite escolha; Líder não altera o próprio perfil.
- `GET /permissions` e PATCH de substituição funcionam apenas para Líder; aceitar `[]`, validar revisão e catálogo, atualizar revisão atomicamente e auditar mudanças confirmadas.
- Os ciclos de Categoria, Produto e Fornecedor respeitam contratos de campos, filtros, paginação, erros, unicidade, referência ativa de Categoria, preservação de referências e inativação sem DELETE.
- Testes demonstram que nenhuma operação desta capability altera saldo ou movimentações, e que `members_accounts` e `admin/user_role` conservam o mecanismo legado.
- XanoScript dos arquivos em escopo é validado pelo Xano Developer MCP e workflows são verificados em datasource de teste, sem depender de datasource live.
