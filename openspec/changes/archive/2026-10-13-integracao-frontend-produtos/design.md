# Design: Integração Reflex de Produto

## Contratos Xano existentes

O grupo é `api:gestao-estoque-cadastros`. Todos os endpoints declaram `auth = "user"` e chamam `Inventory/authorize_permission`.

| Operação | Método e rota | Permissão |
|---|---|---|
| Listar | `GET /products` | `product.read` |
| Detalhe | `GET /products/by_id/{product_id}` | `product.read` |
| Criar | `POST /products` | `product.create` |
| Atualizar campos | `PATCH /products/by_id/{product_id}` | `product.update` |
| Inativar | `PATCH /products/by_id/{product_id}/inactivate` | `product.inactivate` |
| Ativar | `PATCH /products/by_id/{product_id}/activate` (publicado no workspace Xano 152211) | `product.update` |

POST exige `codigo`, `nome`, `categoria_id` inteiro, `unidade_medida` e `estoque_minimo` decimal maior ou igual a zero; `descricao` é opcional. Categoria deve existir e estar ativa. O status inicial é `ativo` pelo padrão da tabela. PATCH aceita `codigo`, `nome`, `descricao`, `limpar_descricao`, `categoria_id`, `unidade_medida` e `estoque_minimo`; não aceita `id` nem `status`. Para limpar descrição, usar `limpar_descricao=true`. Reassociação exige Categoria existente e ativa; preservar associação atual é permitido.

O schema Produto contém `id`, `codigo`, `nome`, `descricao?`, `categoria_id` (referência à Categoria), `unidade_medida`, `estoque_minimo` decimal e `status` (`ativo`/`inativo`). Não há quantidade atual no cadastro.

- Na edi??o, `original_product_status` mant?m o valor carregado do Xano e `current_product_status` representa o valor escolhido no formul?rio. O bot?o Ativar/Inativar apenas alterna o valor local; n?o faz requisi??o. Ao salvar, comparar os campos cadastrais com `original_product`, enviar `PATCH /products/by_id/{product_id}` se houver diferen?as e, se o status mudou, chamar o endpoint de transi??o correspondente depois do PATCH cadastral. Redirecionar para `/produtos` somente ap?s sucesso de todas as opera??es.
- Os endpoints de campos e status n?o compartilham uma transa??o. Se os campos forem salvos e o PATCH de status falhar, manter a edi??o e os valores escolhidos, reler o produto por `GET /products/by_id/{product_id}`, atualizar a base original e exibir erro de falha parcial para permitir nova tentativa consistente.

## Fluxo Reflex

- A busca da listagem mantém `search_query` em `ProductsState` e filtra em memória os produtos carregados por substring case-insensitive e sem acentos em código, nome e nome da Categoria; digitar não faz chamadas adicionais ao Xano. Os valores originais exibidos não são normalizados.
- Estender o XanoClient para usar Bearer, query params e JSON, com mensagens distintas para 401, 403, validação, duplicidade, regra de negócio e não encontrado.
- `ProductsState` concentra listagem, opções de Categoria, criação, detalhe, edição e mudança de status.
- A rota de edição usa `/produtos/[product_id]/editar`; o guard atual continua exigindo sessão e permite UX a Líder/Almoxarife. O estado não chama APIs da página se o perfil não passar pelo guard.
- A criação carrega Categorias ativas usando `GET /categories?status=ativo`, valida os campos e envia apenas os campos do contrato.
- Criação e edição usam o mesmo select de unidade de medida, com códigos `UN`, `CX`, `RL`, `PCT`, `PAR`, `KG`, `L` e `MT` e rótulos legíveis; o payload envia somente o código em maiúsculas. Códigos históricos reconhecidos sem diferenciar caixa são normalizados para o código canônico na interface.
- Erros do POST são classificados pelo código explícito retornado pelo Xano, inclusive quando estiver dentro de `message` ou de um envelope aninhado. `DUPLICATE_VALUE` mostra o código enviado; `BUSINESS_RULE_VIOLATION` informa que a Categoria não existe ou está inativa; erros de input orientam revisar obrigatórios e estoque mínimo. Um HTTP 400 isolado nunca é tratado como duplicidade. Códigos desconhecidos usam mensagem genérica e preservam os campos do formulário.
- A edição carrega produto por ID e Categorias ativas. Se o produto tiver vínculo atual com Categoria inativa, a opção atual será preservada sem sugeri-la para nova associação.
- O status escolhido fica pendente no formul?rio at? Salvar altera??es; o bot?o apenas alterna o estado local. Inativar usa `product.inactivate`; ativar usa `product.update`. As chamadas remotas ocorrem somente no salvamento.
- Após criar, voltar para `/produtos`, cujo carregamento busca novamente os dados. Após edição/status, voltar à lista ou manter resposta de sucesso no editor.

## Fornecedor padrão no formulário de Produto

Criação e edição usam o mesmo select alimentado por `GET /suppliers?status=ativo`, paginado, sob `supplier.read`. `Sem fornecedor padrão` não envia ID. Ao editar, uma referência atual inativa é carregada por `GET /suppliers/by_id/{supplier_id}` e mostrada como opção atual desabilitada; o usuário pode preservar o vínculo, limpá-lo explicitamente ou selecionar um Fornecedor ativo.

## Regras reservadas à futura Entrada de estoque

Na futura entrada iniciada por código de barras, Produto preencherá código, nome e Fornecedor padrão como sugestão. O Fornecedor da entrada continuará alterável conforme a regra futura; o Fornecedor padrão não é exclusividade de compra. A futura data/hora será visível e opcional: se informada, o backend usa o valor; se omitida, o backend grava a data/hora efetiva de conclusão da entrada. A interface exibirá: “Se nenhuma data for informada, será utilizada automaticamente a data e hora do registro da entrada.” Esta mudança não implementa tela de entrada.

## Autorização e UX

Os códigos de permissão não são persistidos nem considerados concedidos pelo frontend. O Xano valida cada chamada. A visibilidade local usa o perfil conhecido e a matriz inicial (Líder integral, Almoxarife com operações de Produto, Auxiliar leitura); uma resposta 403 continua possível se o Líder tiver alterado grants, e deve ser exibida amigavelmente. Para sincronizar grants dinâmicos na interface seria necessário um contrato de consulta de permissões disponível ao usuário autenticado, que não existe atualmente para perfis não Líder.

## Limites de dados

A listagem consulta `GET /products`, `GET /categories` sem filtro de `status` e `GET /stock`; as respostas são paginadas (`items` e metadados), com até 100 itens por chamada. Reflex percorre as páginas necessárias de Categorias e Estoque até uma página retornar menos de 100 itens. `GET /categories` exige `category.read` e retorna `id`, `nome` e `status`; `GET /stock` pertence ao grupo `api:estoque`, exige Bearer e `stock.read`, e retorna `product_id`, `codigo`, `nome`, `quantidade_disponivel`, `estoque_minimo` e `situacao_estoque`. O State monta em memória os mapas `categoria_id -> nome` e `product_id -> saldo`, sem chamadas por Produto. Categoria nula é exibida como `Sem categoria`; referência não encontrada como `Categoria não encontrada`. Produto sem item correspondente de estoque exibe `—` e `Saldo não encontrado`, sem assumir zero. Os rótulos de situação vêm dos códigos retornados pelo Xano; `status` permanece exclusivamente cadastral (`ativo`/`inativo`). HTTP 401 redireciona para a tela de login e 403 é apresentado como falta de permissão.

## Endpoint de ativacao: historico e estado confirmado

Como o PATCH gen?rico n?o aceita `status`, a ativa??o usa `PATCH /products/by_id/{product_id}/activate`, no grupo `Inventory Catalog`, com `auth = "user"` e par?metro de rota inteiro `product_id`. O endpoint exige `product.update`, verifica a exist?ncia do produto e grava somente `status: "ativo"`. A interface chama essa rota somente quando o status original ? `inativo` e o status escolhido ? `ativo`.

Historico: na auditoria anterior, a rota foi encontrada no snapshot local, validada pelo Xano Developer MCP e considerada ausente no workspace remoto, com retorno 404 observado naquele momento. Essa conclusao era referente ao estado entao verificado e nao descreve o estado atual.

Confirmacao atual fornecida pelo usuario: o endpoint `PATCH /products/by_id/{product_id}/activate` existe no workspace Xano 152211. No painel, a chamada a `Inventory/authorize_permission` usa `permission_code = "product.update"`. No NexStock, ao selecionar Ativar produto, o status permaneceu apenas no formulario; depois de clicar em Salvar alteracoes, o Produto ficticio ID 6 passou para `ativo`. Isso confirma o fluxo de alteracao local seguido da persistencia em runtime. A publicacao isolada do endpoint esta confirmada e nao requer novo push nesta tarefa.

Esta evidencia tambem cobre parcialmente a tarefa 6.3, especificamente a transicao de ativacao apos salvar. Os demais cenarios de 6.3, assim como as tarefas 6.5 e 6.6, permanecem pendentes.

## Evidência runtime: fornecedor padrão no cadastro

Na revisão do endpoint publicado `POST /products`, foi identificada uma divergência em relação ao contrato local: a versão publicada não declarava o input opcional `fornecedor_padrao_id` e não incluía esse campo no `db.add product`. O XanoScript local declara o input como inteiro opcional, valida que o fornecedor informado exista e esteja ativo e persiste o ID no registro de Produto.

Após a correção no endpoint publicado, o usuário confirmou um teste real pelo NexStock: cadastrou o Produto de código `12345` com o Fornecedor padrão `Termomecanica Sao Paulo S A`; o vínculo foi persistido na tabela `product` sem edição manual no banco. Na tela de Entrada, a leitura do código `12345` recuperou o Produto e preencheu automaticamente esse Fornecedor. Esta evidência foi fornecida pelo usuário e não foi repetida pelo agente nesta etapa.

O teste comprova o caminho de cadastro e leitura usado pela Entrada para esse caso. Alterar o Fornecedor padrão durante a edição e removê-lo por `PATCH /products/by_id/{product_id}` ainda exigem testes separados. As tarefas 6.3 e 6.5 permanecem pendentes até a cobertura restante ser executada; esta evidência parcial não conclui esses conjuntos de testes.

## Padr?o reutiliz?vel de seletores relacionais pesquis?veis

A implementação compartilhada está em `Meu_projeto/components/searchable_select.py` e é reutilizada também pela tela de Entrada.

Os campos de relacionamento com op??es din?micas do Xano devem usar um seletor pesquis?vel em vez de um select tradicional quando a lista puder crescer. O seletor mostra o nome amig?vel e mant?m o ID do registro como valor enviado. A pesquisa local usa substring, `casefold` e remo??o de diacr?ticos; ela filtra somente as op??es j? carregadas e n?o altera o r?tulo ou os dados originais.

O padr?o inicial aplica-se a Categoria e Fornecedor padr?o nos formul?rios de Produto. Cada endpoint paginado carrega inicialmente uma p?gina de at? 100 registros. Quando houver mais p?ginas, o seletor oferece `Carregar mais op??es`; n?o carrega a lista ilimitada no formul?rio nem consulta o Xano por tecla. A busca considera as op??es carregadas e o usu?rio pode carregar p?ginas adicionais quando o item n?o aparecer. A sele??o guarda o ID num?rico como texto no State e converte para inteiro no payload.

Em edi??o, uma rela??o existente que n?o apare?a entre as op??es ativas deve ser consultada por ID, preservada como r?tulo amig?vel e marcada como n?o selecion?vel para novas associa??es quando estiver inativa. Ela n?o deve ser removida automaticamente.

Este padr?o dever? ser reutilizado para Produto em movimenta??es, Fornecedor em entradas e demais relacionamentos futuros. Se o volume ou a necessidade de localizar registros em todo o cat?logo justificar busca remota, isso depender? de endpoint com busca/pagina??o apropriada; n?o se deve simular busca global baixando todas as p?ginas sem limite.

## Revisao de escopo e evidencias da tarefa 6.5

Historico: a redacao anterior da tarefa 6.5 cobria cadastro sem Fornecedor, selecao de Fornecedor ativo, edicao com vinculo atual inativo, limpeza explicita e rejeicao pelo backend de nova associacao invalida. A tarefa foi estreitada para os cenarios que ainda nao possuem evidencia, sem remover o requisito aprovado sobre preservacao de vinculo inativo.

A proposta exclui criar, editar ou inativar Fornecedores nesta Change. O requisito da spec para mostrar e preservar um Fornecedor inativo ja vinculado ao Produto e um comportamento de integridade da edicao; ele nao adiciona uma funcionalidade para inativar Fornecedores. Esse requisito permanece vigente.

Evidencias runtime confirmadas pelo usuario: Produto criado com Fornecedor ativo; troca do Fornecedor padrao, incluindo a mudanca ainda nao salva permanecer apenas no formulario; persistencia da troca no Xano apos salvar; remocao explicita do vinculo; confirmacao de `fornecedor_padrao_id = null` no Xano; e correcao/publicacao isolada do PATCH de Produtos.

Situacao registrada antes das novas evidencias desta revisao: ainda sem evidencia para cadastro de Produto sem Fornecedor padrao, preservacao em runtime de vinculo atual cujo Fornecedor esteja inativo e rejeicao pelo backend de associacao inexistente ou inativa. Essa fotografia anterior foi atualizada pelos resultados listados abaixo.

## Auditoria do escopo ativo/inativo de Fornecedor

A decisao do projeto de nao oferecer gestao de ativacao/inativacao de Fornecedores nesta etapa e compativel com a proposta desta Change e com a spec vigente `integracao-fornecedores`, que exclui status e acoes de ciclo de vida da pagina `/fornecedores`. Isso nao remove o estado do dominio nem as regras de integridade de Produtos.

A auditoria estatica confirmou `supplier.status` como enum opcional `ativo`/`inativo`, padrao `ativo`, em `xano/table/supplier.xs`. O endpoint `PATCH /suppliers/by_id/{supplier_id}/inactivate` aplica `status: "inativo"` sob `supplier.inactivate`. `GET /suppliers` filtra por status. `POST /products` exige que uma referencia nova exista e esteja ativa; `PATCH /products/by_id/{product_id}` exige Fornecedor existente e ativo para nova associacao, mas permite preservar a referencia atual inativa quando ela nao e trocada. Essas verificacoes sao leitura de codigo, nao novos testes runtime.

Ha conflito direto com remover os cenarios de Fornecedor inativo da tarefa/spec de Produto: `openspec/specs/fundacao-tecnica-cadastros/spec.md` requer estado ativo/inativo e ciclo funcional futuro de inativacao; `openspec/specs/cadastros-basicos/spec.md` inclui inativacao no ciclo minimo; `openspec/changes/operacoes-backend-cadastros/specs/operacoes-backend-cadastros/spec.md` exige preservar referencias e rejeitar novas associacoes inativas; e esta Change exige mostrar e preservar um vinculo atual inativo na edicao. Esses contratos nao exigem controles de status na interface `/fornecedores`, mas impedem retirar o comportamento de preservacao sem uma decisao de produto e revisao das specs proprietarias.

Evidencias runtime adicionais confirmadas pelo usuario nesta revisao: criacao de Produto sem Fornecedor com persistencia nula; rejeicao de Fornecedor inexistente; alem da criacao com Fornecedor ativo, troca persistida e remocao explicita com `fornecedor_padrao_id = null` ja registradas. Portanto, esses casos foram removidos do conjunto ainda pendente da tarefa 6.5.

Na revisao anterior, esses dois testes ainda permaneciam pendentes. A confirmacao registrada abaixo atualiza aquele estado, sem substituir as evidencias historicas. Nenhuma gestao de status de Fornecedor foi adicionada.

## Confirmacao final dos testes de Fornecedor inativo

O usuario confirmou que realizou com sucesso, no NexStock, os dois testes restantes: (1) edicao de Produto preservando o vinculo existente com um Fornecedor inativo; e (2) rejeicao de uma nova associacao a Fornecedor inativo. O registro limita-se a essa confirmacao; nao foram fornecidos nem adicionados logs, codigos HTTP ou outros detalhes de resposta.

Somados aos testes de cadastro com Fornecedor ativo, cadastro sem Fornecedor, troca persistida, limpeza explicita para `null` e rejeicao de Fornecedor inexistente registrados anteriormente, os criterios da tarefa 6.5 estao cobertos. A tarefa foi marcada como concluida em `tasks.md`.

## Evidencias finais da tarefa 6.6

### Confirmacoes manuais no NexStock

O usuario confirmou em runtime: busca parcial por codigo e nome; busca sem diferenciar maiusculas/minusculas e acentos; selecao de Categoria pelo nome com persistencia do ID; selecao de Fornecedor pelo nome com persistencia do ID; e preservacao do vinculo existente com Fornecedor inativo. Essas confirmacoes sao testes manuais no NexStock, nao resultados dos testes automatizados abaixo.

### Testes automatizados isolados

O arquivo `tests/test_products_relationship_loading.py` usa `unittest`, respostas simuladas e mocks do cliente Xano; nao faz chamadas reais nem grava dados no Xano. Foram aprovados:

- `test_categories_load_next_page_without_duplicate_ids`: carrega 100 Categorias simuladas, solicita a pagina 2, agrega IDs sem duplicatas e preserva os IDs das novas opcoes.
- `test_suppliers_load_next_page_without_duplicate_ids`: repete a verificacao para Fornecedores, desconsiderando a opcao local `Sem fornecedor padrao` na contagem.
- `test_inactive_category_link_remains_visible_and_is_not_resubmitted`: simula um Produto associado a Categoria inativa; a edicao mostra o rotulo atual, mantem o ID no State, marca a opcao indisponivel, nao permite seleciona-la como nova associacao, e um PATCH simulado de outro campo omite `categoria_id`. Um formulario novo recebe somente as Categorias ativas.

Execucao: `.venv\\Scripts\\python.exe -m unittest discover -s tests -v` — 3 testes passaram. A paginacao e o vinculo com Categoria inativa foram validados com dados simulados; isso nao comprova comportamento runtime no Xano. Nenhuma Categoria ou Fornecedor foi criado ou alterado no ambiente remoto. A confirmacao manual de preservacao de Fornecedor inativo permanece separada e nao foi repetida.

Com as confirmacoes manuais dos criterios de busca e selecao/ID, a evidencia manual anterior de Fornecedor inativo e os tres testes automatizados isolados para paginacao e Categoria inativa, os criterios definidos para a tarefa 6.6 estao cobertos. Esta evidencia conclui a tarefa sem afirmar teste runtime remoto para paginas acima de 100 ou para Categoria inativa.

## Evidencias finais da tarefa 6.3

Texto original da tarefa: "Testar manualmente criação, leitura de produtos/categorias/estoque, paginação de saldos, saldo ausente, situações retornadas, atualização, duplicidade, categoria inativa, ativação/inativação e permissões com perfis diferentes."

### Confirmacoes manuais informadas pelo usuario

O usuario confirmou testes realizados no Reflex e no Xano para criação e consulta de Produtos, edição, código duplicado, ativação e inativação, e autorização por perfis, incluindo resposta `PERMISSION_DENIED` para uma operação não autorizada. As evidências manuais anteriores desta Change também registram seleção de Categoria pelo nome e persistência de seu ID. Essas são confirmações do usuário; não foram repetidas nesta auditoria pelo agente.

### Testes automatizados isolados com mocks

O arquivo `tests/test_products_relationship_loading.py` simula respostas do cliente Xano e não faz chamadas reais nem grava dados. Para a 6.3, foram aprovados:

- `test_product_without_stock_row_shows_missing_balance`: Produto sem linha correspondente em `GET /stock` é apresentado com quantidade `—` e situação `Saldo não encontrado`.
- `test_stock_pagination_aggregates_pages_and_maps_situations`: resposta inicial de 100 saldos leva à consulta da página seguinte; os resultados das páginas são associados aos Produtos e as situações `sem_estoque`, `abaixo_minimo` e `normal` são apresentadas como `Sem estoque`, `Abaixo do mínimo` e `Normal`. O teste também verifica o fallback de saldo ausente para outro Produto.
- Reutilizado de 6.6: `test_inactive_category_link_remains_visible_and_is_not_resubmitted` simula um Produto ligado a Categoria inativa, verifica que o vínculo permanece visível no State e que o PATCH simulado de outro campo omite `categoria_id`; a Categoria inativa fica desabilitada no seletor e ausente de um formulário novo.

Execução final: `.venv\\Scripts\\python.exe -m unittest discover -s tests -v` — 5 testes passaram na suíte. Os casos de estoque ausente, paginação/situações e Categoria inativa são testes automatizados com dados e respostas simulados. Eles não são evidência de runtime no Xano. O usuário informou que existem somente quatro Categorias, todas ativas, portanto não foi realizada nem alegada inativação de Categoria real.

Com as confirmações manuais indicadas e os testes automatizados isolados dos cenários restantes, a cobertura definida para a tarefa 6.3 está atendida. Esta conclusão não converte resultados simulados em testes runtime; cada tipo de evidência permanece identificado separadamente.
