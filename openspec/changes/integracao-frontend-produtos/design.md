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

- Estender o XanoClient para usar Bearer, query params e JSON, com mensagens distintas para 401, 403, validação, duplicidade, regra de negócio e não encontrado.
- `ProductsState` concentra listagem, opções de Categoria, criação, detalhe, edição e mudança de status.
- A rota de edição usa `/produtos/[product_id]/editar`; o guard atual continua exigindo sessão e permite UX a Líder/Almoxarife. O estado não chama APIs da página se o perfil não passar pelo guard.
- A criação carrega Categorias ativas usando `GET /categories?status=ativo`, valida os campos e envia apenas os campos do contrato.
- Erros do POST são classificados pelo código explícito retornado pelo Xano, inclusive quando estiver dentro de `message` ou de um envelope aninhado. `DUPLICATE_VALUE` mostra o código enviado; `BUSINESS_RULE_VIOLATION` informa que a Categoria não existe ou está inativa; erros de input orientam revisar obrigatórios e estoque mínimo. Um HTTP 400 isolado nunca é tratado como duplicidade. Códigos desconhecidos usam mensagem genérica e preservam os campos do formulário.
- A edição carrega produto por ID e Categorias ativas. Se o produto tiver vínculo atual com Categoria inativa, a opção atual será preservada sem sugeri-la para nova associação.
- O status escolhido fica pendente no formul?rio at? Salvar altera??es; o bot?o apenas alterna o estado local. Inativar usa `product.inactivate`; ativar usa `product.update`. As chamadas remotas ocorrem somente no salvamento.
- Após criar, voltar para `/produtos`, cujo carregamento busca novamente os dados. Após edição/status, voltar à lista ou manter resposta de sucesso no editor.

## Autorização e UX

Os códigos de permissão não são persistidos nem considerados concedidos pelo frontend. O Xano valida cada chamada. A visibilidade local usa o perfil conhecido e a matriz inicial (Líder integral, Almoxarife com operações de Produto, Auxiliar leitura); uma resposta 403 continua possível se o Líder tiver alterado grants, e deve ser exibida amigavelmente. Para sincronizar grants dinâmicos na interface seria necessário um contrato de consulta de permissões disponível ao usuário autenticado, que não existe atualmente para perfis não Líder.

## Limites de dados

A listagem usa a resposta paginada Xano (`items` e metadados), solicitando até 100 itens por chamada. A resposta não inclui nome da Categoria nem saldo atual: mostrar `categoria_id` e placeholder de quantidade, sem inventar valores. A Categoria legível é exibida na seleção de criação/edição a partir da API de Categorias.

## Endpoint local de ativa??o

Como o PATCH gen?rico n?o aceita `status`, a ativa??o usa `PATCH /products/by_id/{product_id}/activate`, no grupo `Inventory Catalog`, com `auth = "user"` e par?metro de rota inteiro `product_id`. O endpoint exige `product.update`, verifica a exist?ncia do produto e grava somente `status: "ativo"`. A interface chama essa rota somente quando o status original ? `inativo` e o status escolhido ? `ativo`. O snapshot local foi validado pelo Xano Developer MCP; conforme confirmado, a rota ainda n?o existe no Xano remoto e retorna 404 at? ser publicada. A publica??o dever? incluir exclusivamente esse arquivo ap?s um dry-run isolado.
