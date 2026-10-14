# Proposal: Operação backend de Saída de Estoque

## Problema

O NexStock possui saldo oficial em `inventory_stock` e registro comum de movimentos em `inventory_movement`, mas ainda não oferece uma operação backend para retirar estoque com autorização, validação de disponibilidade e rastreabilidade atômica.

## Objetivo

Adicionar uma operação autenticada de Saída que reduza o saldo oficial e registre um movimento `saida` na mesma transação, sem permitir que a validação individual da operação aceite quantidade acima do saldo lido.

## Escopo

- Criar `POST /exits` no grupo existente `Inventory Stock` (`api:estoque`).
- Adicionar a permissão `stock.exit` ao catálogo por meio do seed idempotente e conceder o grant inicial ao perfil `stockkeeper`.
- Usar o bypass integral implícito de `administrator` e não conceder grant inicial a `read_only`.
- Validar autenticação, permissão, Produto ativo, quantidade positiva, saldo existente e disponibilidade suficiente.
- Usar `data_hora` informada ou `now` do backend, registrar `user_id` de `$auth.id` e gravar `supplier_id` nulo.
- Atualizar `inventory_stock` e inserir `inventory_movement` dentro de `db.transaction`.
- Documentar a limitação conhecida de concorrência do padrão `db.get` + `db.edit`.

## Fora do escopo

- Criar uma nova tabela de movimentação.
- Integrar ou alterar o frontend Reflex.
- Alterar a operação `POST /entries`.
- Criar histórico, cancelamento ou exclusão de movimentos.
- Publicar artefatos no Xano remoto, realizar commit ou push.

## Dependências

Depende das tabelas existentes `product`, `inventory_stock`, `inventory_movement`, do grupo `Inventory Stock`, da autenticação Xano e da função `Inventory/authorize_permission`. Os saldos precisam estar inicializados para os Produtos que podem receber Saídas.

## Reorganização de escopo

Esta Change trata da implementação funcional individual de POST /exits: autorização,
validações, atualização do saldo e registro da movimentação na mesma transação. A
implementação existente usa db.get + db.edit dentro de db.transaction, mas não possui
garantia comprovada contra lost update ou overselling entre requisições concorrentes.

A investigação, implementação e validação de uma proteção concorrente para as operações
de Entrada e Saída foi transferida para a Change seguranca-concorrencia-estoque. Esta
transferência não significa que a proteção foi implementada ou testada. Até a conclusão
da nova Change, a limitação concorrente da versão atual permanece explícita.
