# Design

## Context

A proposal aprovada reúne duas entregas backend no Xano: o ciclo operacional de Categoria, Produto e Fornecedor e o gerenciamento das permissões de Almoxarife e Auxiliar de almoxarifado pelo Líder. As estruturas locais de cadastro já existem em `xano/table/category.xs`, `product.xs` e `supplier.xs`; não há endpoints correspondentes no snapshot. A autenticação usa `xano/table/user.xs` e os endpoints quick-start de login e contas.

As specifications consolidadas exigem autenticação, autorização backend, validação de Categoria para Produto, preservação de referências e distinção entre falhas de autenticação, autorização, validação e regra de negócio. A movimentação de estoque é uma capability separada. Este Design define APIs e estruturas adicionais de perfil/permissão, mas não cria implementação ou sincroniza o workspace.

O Xano Developer MCP foi consultado nesta etapa. A documentação XanoScript 2.7.1 descreve grupos e verbos HTTP, autenticação `auth = "user"`, operações de banco, transações e testes unitários/workflow. Embora a documentação inclua a propriedade de isolamento serializável, o parser MCP desta sessão rejeitou essa sintaxe; o design atualizado usa um índice único de auditoria por perfil/revisão anterior como guarda concorrente dentro da transação. Nenhum teste de execução foi possível nesta sessão.

## Goals / Non-Goals

### Goals

- Expor endpoints protegidos para criar, listar, consultar por ID, alterar e inativar os três cadastros.
- Aplicar a matriz inicial por perfil no backend e possibilitar que o Líder altere os grants dos outros dois perfis.
- Separar o usuário autenticado, o perfil de domínio e o papel quick-start `admin`/`member`.
- Atualizar imediatamente a autorização após a alteração de permissões, sem depender de estado de autorização guardado no token.
- Preservar unicidade, relacionamento Produto–Categoria e histórico, sem exclusão física nem operação de estoque.
- Definir contratos de entrada, saída, paginação e erros utilizáveis por uma integração Reflex futura.

### Non-Goals

- Implementar autenticação ou substituir o mecanismo de token Xano existente.
- Implementar a interface de gerenciamento de permissões ou telas de cadastro em Reflex.
- Implementar gestão geral de usuários ou interface de gestão de contas; a atribuição de perfil pelo Líder limita-se ao endpoint descrito nesta change.
- Alterar saldo, criar estoque, registrar movimentações ou consultar histórico operacional.
- Implementar reativação ou exclusão física dos cadastros.
- Criar permissões ou endpoints de estoque, relatórios, dashboard ou outras capabilities.

## Architecture

O Xano autentica o token e disponibiliza `$auth.id`. Cada endpoint deste Design declara `auth = "user"`; a autorização de domínio é executada depois da autenticação e antes de qualquer leitura ou escrita do cadastro.

Uma função reutilizável `Inventory/authorize_permission` recebe o código de permissão necessário, busca o perfil atualmente relacionado a `$auth.id` e aplica uma destas regras:

1. Usuário sem perfil ou com vínculo inválido: rejeitar com `PROFILE_UNASSIGNED` ou `PROFILE_INVALID`.
2. Perfil `administrator` (Administrador, apresentado como Líder): permitir a operação sem consultar grants editáveis.
3. Outro perfil: exigir grant persistido para o código exato da operação; caso contrário, rejeitar com `PERMISSION_DENIED`.

Cada endpoint de cadastro chama essa função com o código próprio, por exemplo `product.update` ou `category.read`. Os endpoints de consulta de permissões e de alteração da matriz exigem `administrator` explicitamente. O endpoint de alteração também restringe o perfil alvo a `stockkeeper` ou `read_only`.

Essa função será a regra central reutilizável para endpoints futuros que adotarem a mesma matriz. Os endpoints quick-start `members_accounts` e `admin/user_role` ficam explicitamente fora do sistema de autorização do estoque e continuam usando `admin/member`; o acesso integral do Líder aplica-se somente às funcionalidades do Sistema de Gerenciamento de Estoque.

## Modelo de dados

### Perfil

Criar `xano/table/inventory_profile.xs` com:

- `id`: chave primária gerada pelo Xano;
- `code`: código estável e único;
- `display_name`: nome apresentado ao usuário;
- `permission_revision`: inteiro iniciado em `1`, incrementado a cada substituição, usado para detectar alterações concorrentes da matriz.

Semear exatamente estes perfis:

| `code` | Conceito | `display_name` |
| --- | --- | --- |
| `administrator` | Administrador | Líder |
| `stockkeeper` | Estoquista | Almoxarife |
| `read_only` | Usuário de consulta | Auxiliar de almoxarifado |

O código `administrator` é protegido pela função central; não existe endpoint que permita editar o código ou permissões desse perfil.

### Catálogo de permissões

Criar `xano/table/inventory_permission.xs` como catálogo estável, não editável pelas APIs desta capability. Cada registro possui `id`, `code` único, recurso e ação. Semear os doze códigos:

- `category.read`, `category.create`, `category.update`, `category.inactivate`;
- `product.read`, `product.create`, `product.update`, `product.inactivate`;
- `supplier.read`, `supplier.create`, `supplier.update`, `supplier.inactivate`.

O catálogo não representa apenas os grants atuais: define quais permissões podem ser atribuídas. Novas capabilities deverão adicionar seus códigos e especificar seus grants iniciais em changes próprias.

### Grants por perfil

Criar `xano/table/inventory_profile_permission.xs` com `id`, `profile_id` e `permission_id`, ambos referências obrigatórias, e índice único composto (`profile_id`, `permission_id`). A ausência de uma linha significa que o perfil não possui aquele grant.

Persistir grants somente para `stockkeeper` e `read_only`. O acesso do Administrador/Líder será implícito pelo código imutável `administrator`; não será representado por uma lista mutável de grants. Isso evita que dados de permissão, chamadas incorretas ou concorrência possam retirar o acesso integral do Líder.

Semear os grants iniciais conforme a matriz aprovada:

| Permissão | `administrator` / Líder | `stockkeeper` / Almoxarife | `read_only` / Auxiliar |
| --- | --- | --- | --- |
| `category.read` | Integral | Sim | Sim |
| `category.create` | Integral | Não | Não |
| `category.update` | Integral | Não | Não |
| `category.inactivate` | Integral | Não | Não |
| `product.read` | Integral | Sim | Sim |
| `product.create` | Integral | Sim | Não |
| `product.update` | Integral | Sim | Não |
| `product.inactivate` | Integral | Sim | Não |
| `supplier.read` | Integral | Sim | Sim |
| `supplier.create` | Integral | Sim | Não |
| `supplier.update` | Integral | Sim | Não |
| `supplier.inactivate` | Integral | Sim | Não |

“Integral” para o Líder significa que a verificação central sempre permite qualquer código de permissão definido no sistema, inclusive códigos adicionados por capabilities futuras que usem o mesmo helper.

### Vínculo do usuário autenticado

Adicionar `inventory_profile_id` à tabela de autenticação `user`, como referência a `inventory_profile`. O campo aceita nulo para contas ainda não atribuídas; toda conta habilitada a usar funcionalidades do estoque deve possuir exatamente um perfil válido.

O snapshot atual contém `user.role` opcional com valores quick-start `admin` e `member`. Esse campo permanece inalterado para compatibilidade com endpoints quick-start que estejam fora desta change. Ele não é lido pela função de autorização de cadastros, não é convertido automaticamente em perfil e não autoriza operações de estoque/cadastro.

Como podem existir linhas de usuário antes do novo vínculo, o Apply deve ser faseado: criar os perfis; adicionar a referência nullable; o Líder atribui manualmente um perfil a cada usuário existente que deva acessar o estoque. Não converter `admin` ou `member` automaticamente: esses papéis quick-start não distinguem os três perfis de domínio. Usuários sem perfil permanecem sem acesso aos endpoints protegidos até que o Líder faça a atribuição.

Novos usuários não podem enviar nem escolher `inventory_profile_id` no signup. O vínculo começa sem atribuição; somente o Líder pode defini-lo usando `PATCH /users/by_id/{user_id}/profile`, validando o alvo e um dos três códigos de perfil. A rota não permite ao Líder alterar o próprio perfil. Até receberem perfil, novos usuários autenticam-se, mas falham fechados nas operações do estoque.

#### Bootstrap inicial do primeiro Líder

Como nenhum usuário é Líder no estado inicial e `user.role` não pode ser convertido, o primeiro vínculo `administrator` será feito por um operador confiável do workspace diretamente pelo executor interno de funções do Xano, após confirmar fora do sistema a identidade aprovada pelo grupo. O operador executa uma única vez `Inventory/bootstrap_first_leader` para um usuário existente e ainda sem perfil. A função não é endpoint HTTP, não é chamada pelos endpoints públicos e não aceita token de usuário comum.

A função exige que os perfis já tenham sido provisionados, verifica que não há um `administrator` atribuído nem marcador de bootstrap, e atribui o perfil e grava o marcador `first_leader` na mesma transação. O marcador tem código único; invocações concorrentes não podem confirmar duas atribuições. Esta exceção controlada existe somente para criar o primeiro Líder. Depois do primeiro sucesso, toda nova chamada falha antes de atribuir perfil; daí em diante, somente um Líder autenticado pode atribuir perfis pela operação protegida normal, e o Líder não pode alterar o próprio perfil. A operação não lê nem converte `admin/member`. Perda posterior de todos os Líderes requer intervenção operacional controlada do proprietário do workspace, não reabertura deste bootstrap.

Este é o único passo de provisionamento fora do endpoint de atribuição pelo Líder; ele exige acesso administrativo ao workspace e não cria uma rota permanente de autoelevação para contas da aplicação.

O login atual emite token com `extras = {}` e retorna `user_id`; a função de autorização resolve o perfil pelo usuário autenticado no banco. A implementação não precisa copiar perfil ou permissões para o token.

### Auditoria da alteração de permissões

Manter auditoria append-only para toda alteração de permissões confirmada. Criar `xano/table/inventory_permission_audit.xs` com:

- ID e timestamp do evento;
- ID do usuário autenticado que realizou a alteração;
- perfil alvo;
- revisão anterior e revisão nova;
- listas de códigos adicionados e removidos.

Adicionar índice único composto (`target_profile_id`, `revision_before`). Além de preservar uma trilha de auditoria, esse índice garante que somente uma alteração possa confirmar uma mesma revisão anterior. O conflito é reconhecido depois do rollback consultando esse par, sem depender de sintaxe de isolamento que o parser MCP rejeita.

O registro de auditoria é escrito na mesma transação que atualiza os grants. Falha ao registrar a auditoria reverte também a alteração de permissões. Não há endpoint nesta capability para consultar, editar ou apagar eventos de auditoria.

Não reutilizar automaticamente `event_log`: o arquivo local é marcado como quick-start e associa evento a `account_id`, sem contrato de imutabilidade ou semântica de auditoria de permissões.

## Endpoints e grupos Xano

Usar um grupo Xano `Inventory Catalog`, com pasta `xano/api/inventory_catalog/` e canonical proposto `gestao-estoque-cadastros`. A documentação do Xano exige grupo para cada endpoint e canonical único na instância inteira; como não houve consulta de configuração remota nesta etapa, verificar colisão do canonical antes de futura sincronização.

Todos os endpoints abaixo exigem `auth = "user"`. Os nomes usam rotas inglesas coerentes com os identificadores Xano e com os nomes das tabelas; o Reflex apresentará rótulos em português.

### Categoria

| Verbo | Rota | Permissão |
| --- | --- | --- |
| `GET` | `/categories` | `category.read` |
| `GET` | `/categories/by_id/{category_id}` | `category.read` |
| `POST` | `/categories` | `category.create` |
| `PATCH` | `/categories/by_id/{category_id}` | `category.update` |
| `PATCH` | `/categories/by_id/{category_id}/inactivate` | `category.inactivate` |

### Produto

| Verbo | Rota | Permissão |
| --- | --- | --- |
| `GET` | `/products` | `product.read` |
| `GET` | `/products/by_id/{product_id}` | `product.read` |
| `POST` | `/products` | `product.create` |
| `PATCH` | `/products/by_id/{product_id}` | `product.update` |
| `PATCH` | `/products/by_id/{product_id}/inactivate` | `product.inactivate` |

### Fornecedor

| Verbo | Rota | Permissão |
| --- | --- | --- |
| `GET` | `/suppliers` | `supplier.read` |
| `GET` | `/suppliers/by_id/{supplier_id}` | `supplier.read` |
| `POST` | `/suppliers` | `supplier.create` |
| `PATCH` | `/suppliers/by_id/{supplier_id}` | `supplier.update` |
| `PATCH` | `/suppliers/by_id/{supplier_id}/inactivate` | `supplier.inactivate` |

### Gerenciamento de permissões

| Verbo | Rota | Acesso |
| --- | --- | --- |
| `GET` | `/permissions` | Somente `administrator` |
| `PATCH` | `/permissions/profiles/{profile_code}` | Somente `administrator`; alvo deve ser `stockkeeper` ou `read_only` |
| `PATCH` | `/users/by_id/{user_id}/profile` | Somente `administrator`; atribui um dos três perfis, exceto ao próprio ator |

Os paths com `by_id` usam prefixo estático para evitar ambiguidades de roteamento. Os arquivos seguem a convenção documentada `{nome}_{verbo}.xs`, em minúsculas, e ficam sob a pasta do grupo. Exemplo: `categories_by_id_get.xs` define `GET /categories/by_id/{category_id}`.

## Contratos de entrada e saída

### Criação

Os nomes de campos correspondem às tabelas Xano; o cliente não pode enviar `id` nem `status`. O status inicial `ativo` vem do default das tabelas existentes.

| Entidade | Campos obrigatórios | Campos opcionais |
| --- | --- | --- |
| Categoria | `nome` | — |
| Produto | `codigo`, `nome`, `categoria_id`, `unidade_medida`, `estoque_minimo` (decimal `>= 0`) | `descricao` |
| Fornecedor | `nome_razao_social`, `tipo_documento` (`CPF` ou `CNPJ`), `documento` | `contato`, `endereco` |

`POST` responde com o registro criado, incluindo `id`, estado e `categoria_id` quando aplicável. Produto retorna a referência `categoria_id`; não duplica nem transforma `estoque_atual` em campo do cadastro.

### Alteração parcial

`PATCH` aceita apenas campos mutáveis de cada entidade:

- Categoria: `nome`.
- Produto: `codigo`, `nome`, `descricao`, `categoria_id`, `unidade_medida`, `estoque_minimo`.
- Fornecedor: `nome_razao_social`, `tipo_documento`, `documento`, `contato`, `endereco`.

`id` e `status` não são alteráveis por `PATCH` genérico. Omissão de campo preserva o valor existente. Para limpar campos opcionais, Produto aceita `limpar_descricao` e Fornecedor aceita `limpar_contato` e `limpar_endereco`; quando a flag correspondente é `true`, o valor persistido passa a `null`. O campo de valor informado com valor não nulo atualiza normalmente. Campos de valor são opcionais não anuláveis no schema de entrada, de modo que envio direto de `null` seja rejeitado como erro de entrada. Enviar o campo de valor junto com sua flag de limpeza `true` é conflito e retorna `INVALID_INPUT`. Flag `false` sem valor não altera o campo. Corpo sem alteração efetiva, inclusive somente flags falsas, continua rejeitado com `INVALID_INPUT`. Flags de limpeza são controles do PATCH e nunca são persistidas. A resposta contém o registro atualizado.

### Inativação

O endpoint de inativação não aceita campos de cadastro. Altera somente `status` para `inativo` e retorna o registro atualizado. Repetir a chamada sobre registro já inativo é idempotente e retorna esse estado. Esta capability não implementa reativação.

### Detalhe e listagem

O detalhe retorna os campos persistidos do cadastro e responde `NOT_FOUND` quando o ID não existir. As listagens aceitam:

- Categoria: `status` opcional (`ativo` ou `inativo`).
- Produto: `status` e `categoria_id` opcionais.
- Fornecedor: `status` e `tipo_documento` opcionais.

Sem filtro de `status`, retornam registros ativos e inativos; assim, a inativação não oculta nem apaga informação histórica. As consultas são paginadas com `page` padrão `1`, `per_page` padrão `20`, limite máximo `100`, ordenação estável por `id` ascendente e metadados de paginação do `db.query` Xano. Os filtros sobre colunas sem índice adicional são funcionais para o catálogo previsto; volume futuro que exija índices adicionais deve ser medido antes de alterar schemas.

Resposta da listagem usa o envelope paginado Xano: `itemsReceived`, `curPage`, `nextPage`, `prevPage`, `offset`, `perPage` e `items`. Cada item tem os mesmos campos principais que o endpoint de detalhe.

### Consulta e alteração de permissões

`GET /permissions` retorna o catálogo permitido nesta capability e a matriz efetiva dos três perfis. Para o Líder, retorna todas as permissões atuais com indicação de que o acesso é integral e imutável. Para Almoxarife e Auxiliar, retorna apenas os grants persistidos e o `permission_revision` correspondente.

`PATCH /users/by_id/{user_id}/profile` recebe somente `profile_code`, um dos códigos `administrator`, `stockkeeper` ou `read_only`. Apenas o Líder pode atribuir; o endpoint rejeita alteração do próprio vínculo, IDs/campos de perfil fornecidos pelo cliente e código desconhecido. Signup não aceita escolha do perfil. Usuários ainda sem atribuição continuam bloqueados dos endpoints do estoque.

`PATCH /permissions/profiles/{profile_code}` recebe a lista completa desejada e a revisão retornada pelo GET:

```json
{
  "permission_revision": 4,
  "permissions": ["product.read", "supplier.read"]
}
```

A lista vazia é válida e remove todos os grants editáveis do perfil alvo. IDs, nomes de perfil, grants do Líder e códigos de permissão fora do catálogo não são aceitos no corpo. Códigos desconhecidos, repetidos ou alvo `administrator` são erros de entrada/autorização, sem alteração parcial. A resposta retorna a matriz persistida e a nova revisão.

A substituição é feita em `db.transaction`: validar ator, alvo, revisão e catálogo; calcular grants adicionados/removidos; substituir linhas de `inventory_profile_permission`; atualizar a revisão; gravar auditoria. O índice único de `inventory_permission_audit` sobre (`target_profile_id`, `revision_before`) funciona como compare-and-set persistente: somente uma transação pode confirmar cada revisão anterior. Uma violação desse índice reverte toda a transação; fora da transação, o handler consulta o par alvo/revisão e traduz sua existência em `PERMISSION_REVISION_CONFLICT`. Assim a proteção usa recursos XanoScript validados, sem `isolation = "serializable"`, rejeitado pelo parser MCP desta sessão. Revisões obsoletas também são rejeitadas pela comparação dentro da transação.

## Autorização, erros e tokens

- A autenticação é exigida pela declaração do endpoint (`auth = "user"`). Token ausente ou inválido é rejeitado antes do stack.
- `$auth.id` é a identidade confiável; perfil é carregado da tabela `user` e validado contra `inventory_profile` em cada chamada.
- Toda operação de cadastro executa a checagem da permissão específica antes de buscar dados ou alterar estado.
- A permissão é lida do estado persistido a cada chamada; tokens não contêm grants. Logo, adicionar/remover permissões passa a valer na próxima chamada usando o mesmo token autenticado.
- O helper trata `administrator` como acesso integral; grants persistidos não podem restringir o Líder.
- O perfil sem grants permanece autenticado, mas não pode executar operações de cadastro; não existe grant implícito.

As respostas devem preservar códigos de erro estáveis além do texto de mensagem. Códigos planejados incluem `AUTHENTICATION_REQUIRED`, `PROFILE_UNASSIGNED`, `PROFILE_INVALID`, `PERMISSION_DENIED`, `INVALID_INPUT`, `BUSINESS_RULE_VIOLATION`, `NOT_FOUND`, `DUPLICATE_VALUE`, `IMMUTABLE_PROFILE` e `PERMISSION_REVISION_CONFLICT`. O Xano documenta os tipos nativos `accessdenied`, `inputerror` e `notfound`; o mapeamento final entre código estável e envelope/status Xano será exercitado nos workflow tests para manter distinguíveis autenticação, autorização, validação, conflito e regra de negócio.

## Validação de Categoria, unicidade e integridade

### Produto–Categoria

- Na criação de Produto, buscar `category_id`; Categoria inexistente ou inativa rejeita a operação com `BUSINESS_RULE_VIOLATION`.
- No PATCH, carregar o Produto atual. Se `categoria_id` estiver presente e diferente do vínculo atual, exigir Categoria existente e ativa. Atualizar outros campos de Produto já relacionado a Categoria posteriormente inativada não rompe o vínculo nem exige reassociação.
- Inativar Categoria não altera ou remove produtos associados. Consultas continuam mostrando a referência e status da Categoria.
- A referência `product.categoria_id` continua protegida pelo vínculo físico declarado na tabela Xano.

### Unicidade

As constraints existentes são a autoridade final: `category.nome`, `product.codigo` e `supplier.documento` possuem índice único. Create e update consultam duplicidade antes da escrita para devolver erro identificável; a constraint continua obrigatória para proteger contra duas requisições concorrentes. Em update, comparar contra outros IDs, não contra o próprio registro. Se a escrita falhar, o catch consulta o valor e, em update, exclui o ID atual; somente se outro registro realmente persistir com esse valor retorna `DUPLICATE_VALUE`. Sem conflito confirmado, a falha original é relançada sem tradução. Isso cobre a corrida pre-check/write sem depender de nome interno variável do índice. O caso concorrente ainda requer workflow test em datasource isolado.

#### Campos opcionais limpáveis em PATCH

O XanoScript validado pelo MCP não distingue campo ausente de campo nullable enviado como `null`. Para manter o conjunto de valores textuais válido sem sentinelas, os campos de valor são declarados opcionais não anuláveis (`text campo?`); assim, omissão é aceita e `null` é rejeitado pela validação de input antes do stack. A limpeza é expressa por flags separadas: `limpar_descricao`, `limpar_contato` e `limpar_endereco`. Flag `true` sem valor correspondente escreve `null`; flag `false` sozinha preserva o valor. Campo de valor junto da flag `true` é rejeitado como conflito. Se não houver alteração efetiva, o PATCH é rejeitado. As flags não são persistidas. O código de erro de entrada para o nulo direto depende da validação de schema do Xano; o workflow test deve confirmar o envelope observado e sua correspondência a `INVALID_INPUT`.

Esta change não acrescenta unicidade por combinação, validação de checksum de CPF/CNPJ, trim, conversão de maiúsculas/minúsculas ou remoção de pontuação. Conforme decisão aprovada, a unicidade baseia-se no valor armazenado e nos índices atuais; variantes com espaços, caixa ou pontuação podem ser valores distintos.

### Inativação e referências

Não criar endpoints `DELETE` nem usar `db.del`, `db.bulk.delete` ou `db.truncate` para as três tabelas de domínio. A inativação altera somente o campo `status`. A identidade de Categoria, Produto e Fornecedor e relações existentes permanecem intactas. Fornecedor continua sem relação universal com Produto.

## Fronteira com estoque e frontend

Os endpoints deste Design escrevem apenas `category`, `product`, `supplier`, as novas tabelas de perfis/permissões, `user.inventory_profile_id` e `inventory_permission_audit`. Nenhum endpoint lê-modifica saldo, cria linha de estoque, grava entrada/saída, cria histórico de movimentação ou altera estoque mínimo fora do PATCH de cadastro. `estoque_minimo` continua sendo um atributo configurável de Produto, não uma quantidade disponível.

Reflex futuramente chamará essas APIs, apresentará perfis como Líder, Almoxarife e Auxiliar de almoxarifado e poderá ocultar ações indisponíveis para melhorar a experiência. O frontend não decide autorização e não escreve grants diretamente. O escopo desta change não inclui páginas, componentes, estado Reflex ou apresentação visual da matriz.

## Estratégia de auditoria e segurança

Registrar apenas alterações de permissão confirmadas; chamadas negadas ou inválidas não geram evento de alteração. Evento e grants são atômicos. O registro identifica ator e alvo e descreve a diferença de permissões para permitir reconstrução da sequência. Não registrar tokens, senhas ou dados de cadastro de usuário.

A tabela dedicada e a gravação transacional das alterações confirmadas estão aprovadas. Não será criado endpoint de consulta de auditoria nesta change; a política operacional de retenção deverá respeitar as regras aplicáveis ao projeto e Xano.

## Estratégia de validação XanoScript

1. Validar pelo Xano Developer MCP cada novo `.xs` individualmente: schemas de perfil/permissão/auditoria, API group, endpoints e funções compartilhadas.
2. Incluir validação do endpoint de listagem paginada, PATCH parcial, relacionamento `category_id`, checagem de grants e transação de substituição de grants.
3. Corrigir erros reportados pelo MCP e repetir a validação somente nos arquivos em escopo.
4. Executar validação de workflow no Xano contra datasource de teste. Não usar datasource live para testes destrutivos ou de dados de produção.
5. Preservar o erro preexistente documentado em `xano/workspace/meu_espaco.xs`; não corrigir nem usar esse arquivo como motivo para ampliar a change. O validator deve ser apontado aos arquivos desta capability.
6. Antes de qualquer sincronização em etapa autorizada, comparar snapshot e workspace, validar o canonical único do API group e revisar o dry-run. Isso não faz parte deste Design/Review.

Na exploração, MCP 2.7.1 validou sintaticamente um `query` autenticado representativo, schemas de tabela com FK/índice composto e uma função de substituição em transação com exclusão de grants e inserção iterativa. Isso demonstra viabilidade dos blocos escolhidos, sem validar um conjunto final de endpoints que ainda não foi implementado.

## Estratégia de testes backend

Usar Xano unit tests para funções reutilizáveis e workflow tests para chamadas de endpoint, com datasource de teste isolado. Cobrir no mínimo:

- Perfil inexistente, vínculo ausente ou perfil inválido: acesso negado; papel quick-start `admin`/`member` não concede permissão de cadastro.
- Atribuição de perfil existente e novo somente por Líder; signup não aceita `inventory_profile_id`; tentativa de alterar o próprio perfil é recusada; usuário sem perfil fica sem acesso ao estoque.
- Todas as 36 combinações da matriz inicial (12 permissões × 3 perfis), incluindo o bypass integral do Líder.
- Bootstrap do primeiro Líder, execução simultânea, rejeição após conclusão e ausência de rota pública de bootstrap.
- Leitura e atualização da matriz somente pelo Líder; recusa de edição do perfil Líder, perfil desconhecido, permissão desconhecida, código duplicado e revisão obsoleta.
- Substituição de grants com lista completa, incluindo `permissions: []`; confirmação de que o perfil vazio não tem acesso implícito e pode receber grants novamente.
- Falha no meio da substituição ou da auditoria reverte a transação, sem matriz parcial.
- Usuário sem autenticação; usuário autenticado sem permissão; erro de validação; erro de regra de negócio; ID inexistente; respostas com categorias/códigos distinguíveis.
- Create, list, detail, PATCH e inativação para Categoria, Produto e Fornecedor com perfil permitido e negado.
- Campos obrigatórios, enums, decimal mínimo, atualização parcial, rejeição de body sem campos alteráveis e impossibilidade de alterar ID/status via PATCH genérico.
- Duplicidade de `nome`, `codigo` e `documento` em create e update; duas requisições concorrentes não podem superar o índice único.
- Para PATCH, testar omissão (preservação), valor não nulo (atualização), flag de limpeza `true` (limpeza para null), nulo direto (rejeição como `INVALID_INPUT`), campo mais flag verdadeira (conflito), flag falsa sem campo (preservação) e PATCH sem alteração efetiva (rejeição).
- Produto com Categoria inexistente/inativa rejeitado; alteração de categoria para ativa aceita; associação já existente preservada quando a Categoria é inativada; edição de outro campo sem reassociação permanece possível.
- Inativação mantém IDs, status e referências; nenhuma rota `DELETE` existe; chamadas repetidas de inativação são idempotentes.
- Após alteração de grant, a chamada seguinte com o mesmo token usa a permissão atualizada; token expirado/ inválido continua sendo responsabilidade da autenticação.
- Nenhum cenário de cadastro altera quantidade disponível, tabelas de estoque ou histórico de movimentações.
- Auditoria contém ator, alvo, grants adicionados/removidos e revisões para cada mudança confirmada, sem evento para tentativa rejeitada.

## Riscos / Trade-offs

- **Atribuição manual de perfil:** o Líder atribui perfis a usuários existentes e novos por endpoint protegido; usuário sem perfil permanece sem acesso ao estoque até a atribuição. O papel quick-start não é usado para inferir perfil.
- **Bootstrap inicial:** operador confiável do workspace escolhe e atribui o primeiro Líder uma única vez por função interna não exposta por HTTP. O marcador único fecha o bootstrap após sucesso; perda posterior de todos os Líderes exige intervenção administrativa explícita, sem reabilitar o caminho de bootstrap da aplicação.
- **Leitura de permissões em toda chamada:** exige consultas ao Xano, mas torna mudanças efetivas imediatamente e elimina estado de autorização obsoleto em tokens.
- **Lista completa no PATCH de grants:** deixa remoção total e reposição idempotente, mas exige revisão de versão para evitar sobrescrita de edição concorrente.
- **Índices existentes e normalização:** por decisão aprovada, igualdade é avaliada pelos valores armazenados sem canonicalização; variantes com espaços, caixa ou pontuação podem representar valores diferentes.
- **Auditoria dedicada:** adiciona uma tabela append-only e torna a alteração de grants dependente do sucesso do registro na mesma transação.
- **Campos opcionais limpáveis em PATCH:** inputs de valor opcionais não anuláveis permitem rejeitar `null` direto sem sentinelas; flags booleanas explícitas implementam limpeza. A resposta exata da validação de schema para `null` direto ainda precisa ser confirmada em workflow test contra `INVALID_INPUT`.
- **Limite das APIs quick-start:** o Líder não recebe acesso integral a `members_accounts` nem `admin/user_role`; essas rotas continuam no mecanismo legado `admin/member`, fora da autorização do estoque.

## Decisões aprovadas pelo grupo

- O perfil dos usuários existentes será atribuído manualmente pelo Líder; não haverá conversão automática de `admin`/`member`.
- Para novos usuários, somente o Líder pode atribuir um dos três perfis. O usuário não escolhe o perfil no signup; até a atribuição, permanece sem acesso às funcionalidades do estoque.
- A auditoria dedicada `inventory_permission_audit` registra cada alteração confirmada com ator, perfil alvo, revisão anterior e nova, permissões adicionadas e removidas. A gravação ocorre na mesma transação dos grants e não haverá endpoint de consulta nesta change.
- Unicidade será baseada nos valores armazenados, sem trim, conversão de caixa, remoção de pontuação ou validação adicional de CPF/CNPJ.
- O acesso integral do Líder vale somente para as funcionalidades do Sistema de Gerenciamento de Estoque. `members_accounts` e `admin/user_role` ficam fora deste modelo e mantêm a autorização legada `admin/member`.
- Permanecem aprovadas a matriz inicial, a edição de grants de Almoxarife e Auxiliar pelo Líder, a possibilidade de remover todos os grants desses perfis e a proteção das permissões do Líder.

As cinco decisões atualizadas acima não são pendências de aprovação. A política operacional de retenção da auditoria deve respeitar as regras aplicáveis ao projeto e ao Xano.
