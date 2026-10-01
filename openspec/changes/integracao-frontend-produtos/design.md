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
| Ativar | `PATCH /products/by_id/{product_id}/activate` (endpoint novo local) | `product.update` |

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

## Endpoint local de ativa??o

Como o PATCH gen?rico n?o aceita `status`, a ativa??o usa `PATCH /products/by_id/{product_id}/activate`, no grupo `Inventory Catalog`, com `auth = "user"` e par?metro de rota inteiro `product_id`. O endpoint exige `product.update`, verifica a exist?ncia do produto e grava somente `status: "ativo"`. A interface chama essa rota somente quando o status original ? `inativo` e o status escolhido ? `ativo`. O snapshot local foi validado pelo Xano Developer MCP; conforme confirmado, a rota ainda n?o existe no Xano remoto e retorna 404 at? ser publicada. A publica??o dever? incluir exclusivamente esse arquivo ap?s um dry-run isolado.

## Padr?o reutiliz?vel de seletores relacionais pesquis?veis

A implementação compartilhada está em `Meu_projeto/components/searchable_select.py` e é reutilizada também pela tela de Entrada.

Os campos de relacionamento com op??es din?micas do Xano devem usar um seletor pesquis?vel em vez de um select tradicional quando a lista puder crescer. O seletor mostra o nome amig?vel e mant?m o ID do registro como valor enviado. A pesquisa local usa substring, `casefold` e remo??o de diacr?ticos; ela filtra somente as op??es j? carregadas e n?o altera o r?tulo ou os dados originais.

O padr?o inicial aplica-se a Categoria e Fornecedor padr?o nos formul?rios de Produto. Cada endpoint paginado carrega inicialmente uma p?gina de at? 100 registros. Quando houver mais p?ginas, o seletor oferece `Carregar mais op??es`; n?o carrega a lista ilimitada no formul?rio nem consulta o Xano por tecla. A busca considera as op??es carregadas e o usu?rio pode carregar p?ginas adicionais quando o item n?o aparecer. A sele??o guarda o ID num?rico como texto no State e converte para inteiro no payload.

Em edi??o, uma rela??o existente que n?o apare?a entre as op??es ativas deve ser consultada por ID, preservada como r?tulo amig?vel e marcada como n?o selecion?vel para novas associa??es quando estiver inativa. Ela n?o deve ser removida automaticamente.

Este padr?o dever? ser reutilizado para Produto em movimenta??es, Fornecedor em entradas e demais relacionamentos futuros. Se o volume ou a necessidade de localizar registros em todo o cat?logo justificar busca remota, isso depender? de endpoint com busca/pagina??o apropriada; n?o se deve simular busca global baixando todas as p?ginas sem limite.
