# Design: Integração do módulo de Categorias

## API Xano

Usar o grupo existente `Inventory Catalog` (`api:gestao-estoque-cadastros`). `GET /categories` permanece paginado e retorna todas as Categorias, sem filtro de status. O State percorre páginas com `per_page=100`, eliminando chamadas por item. A busca normaliza caixa e acentos e filtra localmente por substring do nome.

`POST /categories` continua exigindo `category.create`; o input `nome` usa trim, rejeita vazio e verifica duplicidade antes de persistir. A tabela já inicia `status` como `ativo` e tem índice único em `nome`.

`PATCH /categories/by_id/{category_id}/activate` será adicionado com `category.update`. `PATCH /categories/by_id/{category_id}/inactivate` já existe e usa `category.inactivate`. Ambos validam a existência do ID, alteram somente `status` e retornam o registro atualizado.

Não alterar permissões nem grants. Pelo autorizador atual, Líder pode escrever; Almoxarife e Auxiliar preservam leitura conforme seus grants, sem controles de escrita na interface.

## Interface e State

Criar `CategoryState` na página de Categorias. Ele mantém itens, loading, erro, busca, modal, nome, estado de criação, ID em atualização de status e mensagens. O `on_load` exige autenticação e carrega a lista real. Erros não usam dados de fallback.

A tabela tem `ID | Nome | Status | Ativar/Inativar`. Não exibir contagem de Produtos porque o endpoint não fornece contagem agregada e não se fará N+1. O status persistido usa `ativo`/`inativo`; a interface mostra `Ativa`/`Inativa`. O switch permanece controlado pelo status confirmado pelo Xano.

O modal de criação desabilita o botão durante o POST. Em sucesso, fecha, limpa e recarrega os itens. `DUPLICATE_VALUE` e nome vazio recebem mensagens específicas.

## Relação com Produto

Não alterar `ProductsState`: formulários de criação já solicitam Categorias com `status=ativo`; na edição, uma referência atual inativa é carregada como opção desabilitada para preservar o vínculo.

## Validação e publicação

Validar os XanoScripts alterados, compilar Reflex, validar OpenSpec strict e `git diff --check`. Preparar dry-run limitado aos XanoScripts desta change. Não publicar sem revisão explícita do preview.
