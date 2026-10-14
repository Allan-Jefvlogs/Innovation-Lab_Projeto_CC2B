# integracao-frontend-produtos Specification

## Purpose
TBD - created by archiving change integracao-frontend-produtos. Update Purpose after archive.

## Requirements

### Requirement: Selecionar Fornecedor padrão opcional no Produto

Os formulários de criação e edição MUST exibir o mesmo select de Fornecedor padrão, sem texto livre, carregado de `GET /suppliers` com filtro de ativos e paginação. O select MUST permitir `Sem fornecedor padrão` e enviar o ID numérico, nunca o nome. Ao editar, uma referência atual inativa MUST permanecer visível como opção atual desabilitada, sem ser removida automaticamente; o usuário poderá mantê-la, limpá-la ou selecionar um Fornecedor ativo. A autorização e validação definitiva MUST permanecer no Xano.

#### Scenario: Carregar opções de Fornecedor
- **WHEN** usuário autorizado abre criação ou edição de Produto
- **THEN** Reflex carrega Fornecedores ativos paginados e permite selecionar nenhum ou um Fornecedor ativo

#### Scenario: Preservar vínculo atual inativo
- **WHEN** Produto existente aponta para Fornecedor inativo
- **THEN** edição carrega e mostra o vínculo atual sem quebrar, sem permitir nova seleção desse Fornecedor e sem limpá-lo automaticamente

#### Scenario: Enviar ou limpar Fornecedor padrão
- **WHEN** usuário seleciona Fornecedor ativo, mantém a seleção sem alteração ou escolhe `Sem fornecedor padrão`
- **THEN** Reflex envia o ID numérico, omite campo inalterado ou envia `limpar_fornecedor_padrao=true`, respectivamente

### Requirement: Busca local na listagem de Produtos

Quando os Produtos estiverem carregados, o campo de busca MUST filtrar em memória por substring case-insensitive e accent-insensitive nos campos `codigo`, `nome` e nome da Categoria. A normalização para comparação MUST remover acentos sem alterar os valores exibidos. A busca MUST atualizar conforme o usuário digita e MUST NOT fazer chamadas adicionais ao Xano por tecla. Com a busca vazia, a listagem MUST mostrar todos os Produtos carregados. Se não houver Produtos no Xano, Reflex MUST mostrar `Nenhum produto cadastrado.`; se houver Produtos, mas nenhum corresponder à busca, MUST mostrar `Nenhum produto encontrado.`.

#### Scenario: Filtrar sem diferenciar caixa ou acentos
- **WHEN** usuário digita um trecho em qualquer combinação de maiúsculas/minúsculas e sem acentos
- **THEN** a tabela mostra os Produtos cujo código, nome ou nome da Categoria contém o trecho após normalização, sem alterar os valores exibidos nem fazer uma nova chamada HTTP

#### Scenario: Busca vazia ou sem correspondência
- **WHEN** a busca está vazia ou não corresponde a nenhum Produto
- **THEN** a listagem mostra todos os Produtos ou `Nenhum produto encontrado.`, respectivamente; uma resposta realmente vazia do Xano continua mostrando `Nenhum produto cadastrado.`

### Requirement: Unidade de medida selecionada de catálogo padronizado

Os formulários de criação e edição MUST oferecer o mesmo select, sem texto livre, com os códigos `UN`, `CX`, `RL`, `PCT`, `PAR`, `KG`, `L` e `MT`, apresentados com seus nomes amigáveis. O valor enviado ao Xano MUST ser somente o código permitido em maiúsculas. Na edição, unidades históricas correspondentes a um código permitido sem diferenciar caixa MUST ser normalizadas para a opção canônica; unidade desconhecida MUST NOT ser enviada como valor permitido sem seleção explícita de uma opção válida.

#### Scenario: Selecionar unidade na criação e edição
- **WHEN** usuário escolhe uma unidade em qualquer formulário
- **THEN** a interface mostra o rótulo e o Xano recebe somente o código maiúsculo correspondente

#### Scenario: Carregar código histórico em minúsculas
- **WHEN** um Produto existente contém um código permitido em minúsculas, como `un`
- **THEN** o formulário seleciona `UN`, não falha ao carregar e salva o código canônico em maiúsculas quando houver atualização

### Requirement: Leitura de Produtos do Xano

O Reflex MUST carregar a listagem e o detalhe de Produto pelo Xano usando o token Bearer da sessão. O Xano MUST exigir `product.read`. A interface MUST exibir loading e erro sem substituir falhas por dados mockados. A listagem MUST usar o ID Xano para ações e respeitar o envelope paginado.

#### Scenario: Listagem carregada
- **WHEN** usuário autenticado abre `/produtos`
- **THEN** Reflex consulta `GET /products` com Bearer e mostra os itens reais retornados

#### Scenario: Nome da Categoria na listagem
- **WHEN** Produtos s?o carregados para `/produtos`
- **THEN** Reflex consulta as p?ginas necess?rias de `GET /categories` sem filtro de status, associa os registros por `categoria_id` e mostra o nome real inclusive para Categorias inativas, sem fazer chamadas por Produto

#### Scenario: Refer?ncia de Categoria ausente ou inv?lida
- **WHEN** um Produto n?o possui `categoria_id` ou o ID n?o corresponde aos itens retornados
- **THEN** a linha mostra `Sem categoria` ou `Categoria n?o encontrada`, respectivamente, sem interromper a listagem

#### Scenario: Leitura recusada
- **WHEN** Xano responde que a sessão ou permissão não autoriza leitura
- **THEN** a interface mostra erro amigável e não apresenta dados mockados como fallback

### Requirement: A listagem deve exibir saldo e situação oficiais do Xano

Ao carregar `/produtos`, Reflex MUST consultar as páginas de `GET /stock` com o Bearer atual e associar os itens pelo `product_id`, sem chamadas individuais por Produto. O Xano MUST autorizar a leitura com `stock.read`. A coluna `Qtd.` MUST mostrar `quantidade_disponivel`; `Situação do estoque` MUST mapear `sem_estoque`, `abaixo_minimo` e `normal` para rótulos amigáveis. `Status` MUST continuar exibindo somente o status cadastral `ativo`/`inativo`. Reflex MUST NOT calcular saldo nem situação.

#### Scenario: Saldo e situação carregados
- **WHEN** o Produto possui item correspondente em `GET /stock`
- **THEN** a listagem mostra quantidade e situação retornadas pelo Xano, associadas pelo `product_id`

#### Scenario: Paginação do saldo
- **WHEN** uma página de `GET /stock` retorna 100 itens
- **THEN** Reflex carrega a próxima página e continua até obter uma página com menos de 100 itens

#### Scenario: Saldo ausente
- **WHEN** um Produto não possui item correspondente em `GET /stock`
- **THEN** a quantidade aparece como `—` e a situação como `Saldo não encontrado`, sem assumir zero e sem interromper a listagem

#### Scenario: Permissão de consulta recusada
- **WHEN** `GET /stock` retorna HTTP 403
- **THEN** a listagem mostra mensagem amigável de falta de permissão sem dados substitutos

#### Scenario: Sessão inválida na consulta de saldo
- **WHEN** `GET /stock` retorna HTTP 401
- **THEN** a sessão é tratada como inválida e o usuário é encaminhado para login

### Requirement: Criação de Produto

O Reflex MUST enviar `POST /products` com `codigo`, `nome`, `categoria_id`, `unidade_medida`, `estoque_minimo` e `descricao` somente quando preenchida. A criação MUST validar os campos obrigatórios e MUST NOT permitir múltiplos envios enquanto estiver em andamento. O backend MUST exigir `product.create`, Categoria existente e ativa e unicidade de `codigo`.

#### Scenario: Criação válida
- **WHEN** usuário autorizado envia os campos obrigatórios válidos
- **THEN** o produto é persistido pelo Xano e a interface retorna à listagem atualizada

#### Scenario: Erro de validação, duplicidade ou autorização
- **WHEN** Xano rejeita a criação
- **THEN** a interface mostra mensagem amigável e mantém o formulário sem exibir sucesso

#### Scenario: Erros específicos de criação
- **WHEN** Xano retorna `DUPLICATE_VALUE`, `BUSINESS_RULE_VIOLATION` ou um erro de input para `POST /products`
- **THEN** Reflex informa respectivamente que o código enviado já existe, que a Categoria não existe ou está inativa, ou que os campos/estoque mínimo devem ser revisados; um HTTP 400 sem código reconhecido usa mensagem genérica e nunca é classificado automaticamente como duplicidade

### Requirement: Atualização de Produto

O Reflex MUST carregar `/produtos/{id}/editar` pelo ID real e consultar `GET /products/by_id/{product_id}`. A edição MUST enviar somente campos aceitos por `PATCH /products/by_id/{product_id}`; status e ID MUST NOT ser enviados nesse PATCH. O backend MUST exigir `product.update` e validar unicidade e nova associação de Categoria.

#### Scenario: Editar Produto existente
- **WHEN** usuário autorizado altera campos permitidos
- **THEN** Reflex envia PATCH ao Xano e, somente após sucesso, redireciona para `/produtos`, que busca novamente a lista real

#### Scenario: Falha ao editar Produto
- **WHEN** Xano ou a conexão rejeita o PATCH
- **THEN** Reflex permanece no formulário de edição, preserva os campos e mostra o erro

#### Scenario: ID inexistente ou atualização recusada
- **WHEN** Xano responde `NOT_FOUND`, `PERMISSION_DENIED`, `DUPLICATE_VALUE`, `INVALID_INPUT` ou regra de negócio
- **THEN** Reflex exibe feedback adequado e não informa sucesso

### Requirement: Ativação e Inativação lógica

Produto MUST permanecer persistido e MUST usar `status` `ativo` ou `inativo`; exclusão física MUST NOT ser oferecida. O formulário MUST manter `original_product_status` separado do status escolhido atualmente. Clicar em Ativar/Inativar MUST alterar somente o estado local e MUST NOT chamar o Xano. Ao clicar em Salvar alterações, Reflex MUST enviar o PATCH cadastral quando houver diferenças e chamar `PATCH /products/by_id/{product_id}/inactivate` ou `PATCH /products/by_id/{product_id}/activate` somente quando o status escolhido diferir do original. A inativação exige `product.inactivate`; a ativação exige `product.update`. Reflex MUST redirecionar para `/produtos` somente depois que todas as operações necessárias retornarem sucesso.

#### Scenario: Alterar status sem salvar
- **WHEN** usuário alterna Ativar/Inativar no formulário
- **THEN** o status exibido e o rótulo do botão mudam, sem qualquer chamada ao Xano

#### Scenario: Salvar somente alteração de status
- **WHEN** usuário salva um status diferente do original
- **THEN** Reflex chama somente o endpoint correspondente à transição e redireciona para `/produtos` após sucesso

#### Scenario: Salvar campos e status juntos
- **WHEN** usuário altera campos cadastrais e status e clica em Salvar alterações
- **THEN** Reflex envia o PATCH cadastral e depois o PATCH de status necessário; redireciona somente após ambos terem sucesso

#### Scenario: Falha após salvar campos cadastrais
- **WHEN** o PATCH cadastral retorna sucesso, mas o PATCH de status falha
- **THEN** Reflex permanece na edição, informa a falha parcial, recarrega o produto do Xano para atualizar a base original e mantém os campos e status escolhido no formulário

#### Scenario: Falha sem alteração parcial
- **WHEN** qualquer operação necessária falha antes de uma atualização anterior ter sucesso
- **THEN** Reflex permanece na edição, preserva os valores e mostra o erro sem redirecionar

### Requirement: Proteção de rotas e ações

As rotas de criação e edição MUST reutilizar autenticação e o guard de rota existente, usando os grants efetivos retornados por `/auth/me` independentemente do perfil operacional. `product.create` MUST controlar a rota/ação de criação e `product.update` MUST controlar a rota/ação de edição. O Auxiliar pode executar essas ações quando o grant correspondente tiver sido explicitamente configurado; sem o grant, a ação MUST ficar indisponível e o acesso direto MUST redirecionar para `/dashboard`. Toda escrita MUST continuar autorizada pelo Xano; o perfil e o guard do frontend MUST NOT substituir essa validação.

#### Scenario: Acesso direto à edição sem product.update
- **WHEN** um usuário sem `product.update`, inclusive Auxiliar, tenta abrir rota de edição pela URL
- **THEN** o guard redireciona para `/dashboard`

#### Scenario: Auxiliar com product.update
- **WHEN** o usuário Auxiliar possui `product.update` efetivo
- **THEN** a ação Editar e a rota de edição MUST estar disponíveis
- **AND** o Xano MUST continuar validando `product.update` ao salvar.

#### Scenario: Chamada sem grant de escrita
- **WHEN** usuário consegue acionar uma ação mas não possui grant atual
- **THEN** Xano rejeita a operação e Reflex apresenta o erro sem alterar dados

### Requirement: Seletores pesquis?veis de relacionamentos din?micos

Os formul?rios de Produto MUST oferecer seletores pesquis?veis para Categoria e Fornecedor padr?o, mostrando r?tulos amig?veis e guardando/enviando o ID real do registro. Ao abrir ou focar o campo, o seletor MUST mostrar as op??es carregadas; digitar MUST filtrar localmente por substring sem diferenciar caixa ou acentos. A pesquisa MUST NOT fazer chamadas HTTP por tecla. Para endpoints paginados, a interface MUST carregar inicialmente no m?ximo uma p?gina de at? 100 op??es e MUST permitir solicitar explicitamente a pr?xima p?gina quando houver mais resultados, sem baixar o cat?logo inteiro automaticamente. A valida??o e autoriza??o definitivas permanecem no Xano.

O mesmo padr?o reutiliz?vel MUST orientar futuros seletores de Produto em movimenta??es, Fornecedor em entradas e outros relacionamentos. A edi??o MUST manter vis?vel uma refer?ncia atual inativa obtida por ID, sem permitir nova associa??o a ela nem remov?-la automaticamente.

#### Scenario: Pesquisar e selecionar Categoria
- **WHEN** usu?rio abre o campo de Categoria e digita parte do nome, inclusive sem acentos ou com caixa diferente
- **THEN** a lista carregada ? filtrada localmente, a sele??o exibe o nome da Categoria e o formul?rio guarda/envia o ID real

#### Scenario: Pesquisar e selecionar Fornecedor padr?o
- **WHEN** usu?rio abre o campo de Fornecedor padr?o e digita parte do nome, inclusive sem acentos ou com caixa diferente
- **THEN** a lista carregada ? filtrada localmente, a sele??o exibe o nome do Fornecedor e o formul?rio guarda/envia o ID real ou a op??o `Sem fornecedor padr?o`

#### Scenario: Cat?logo com mais de uma p?gina
- **WHEN** a p?gina atual de op??es n?o inclui o relacionamento desejado e h? mais op??es no endpoint
- **THEN** usu?rio pode carregar a pr?xima p?gina explicitamente; o seletor n?o carrega todas as p?ginas automaticamente nem consulta por tecla

#### Scenario: Preservar relacionamento inativo durante edi??o
- **WHEN** Produto possui Categoria ou Fornecedor atualmente inativo
- **THEN** o formul?rio mostra o r?tulo obtido por ID e preserva o v?nculo sem oferecer o item inativo como nova sele??o
