# Tasks: Operação backend de Saída de Estoque

## 1. Inspeção e contrato

- [x] 1.1 Confirmar que `inventory_movement` suporta `tipo = saida` e já possui os campos necessários.
- [x] 1.2 Confirmar `inventory_stock` decimal, chave única por Produto, autorização central e grant atual de `stock.entry`.
- [x] 1.3 Revisar contrato conceitual consolidado de Movimentação de Estoque e implementação de Entrada.
- [x] 1.4 Consultar documentação XanoScript de operações, inputs e transações; registrar que `db.direct_query` e serialização/lock não são mecanismos utilizáveis nesta change.

## 2. Permissão de Saída

- [x] 2.1 Adicionar `stock.exit` ao catálogo no seed idempotente.
- [x] 2.2 Adicionar grant inicial `stock.exit` para `stockkeeper`, preservando grants existentes e sem grant inicial para `read_only`.

## 3. Endpoint

- [x] 3.1 Criar `POST /exits` autenticado no grupo `Inventory Stock` e validar `stock.exit` dentro da transação.
- [x] 3.2 Validar Produto existente/ativo, quantidade positiva, motivo, saldo existente e saldo suficiente.
- [x] 3.3 Resolver `data_hora` para timestamp informado ou `now` no backend.
- [x] 3.4 Reduzir `inventory_stock` com `db.get` + `db.edit` e criar `inventory_movement` tipo `saida` dentro da mesma transação.
- [x] 3.5 Retornar saldo anterior/atual e dados do movimento, com `$auth.id` e `supplier_id` nulo.
- [x] 3.6 Mapear `INSUFFICIENT_STOCK`, falhas de saldo, deadlock e erro de atualização.

## 4. Validação e runtime

- [x] 4.1 Validar endpoint e seed pelo Xano Developer MCP.
- [x] 4.2 Executar `openspec validate operacao-backend-saida-estoque --strict`.
- [x] 4.3 Executar `git diff --check`.
- [x] 4.4 Registrar a cobertura funcional executada no Produto fictício ID 6: Entrada de 10,75 KG e Saídas de 1,25, 0,75 e 8,75 KG até saldo zero; uma Entrada e três Saídas no Histórico; rejeições diretas da API para saldo insuficiente (`INSUFFICIENT_STOCK`), quantidade zero/negativa e motivo vazio (`INVALID_INPUT`), Produto inexistente/inativo (`PRODUCT_NOT_FOUND`/`PRODUCT_INACTIVE`), ausência de autenticação (HTTP 401) e ausência de `stock.exit` (`PERMISSION_DENIED`); saldo final zero e quatro movimentos após as rejeições. Evidências e limites registrados em design.md. Os cenários avançados não executados foram transferidos para `validacao-avancada-operacoes-estoque`; concorrência/overselling permanecem em `seguranca-concorrencia-estoque`.
- [x] 4.5 Transferir documentalmente a implementação e os testes de concorrência para seguranca-concorrencia-estoque, mantendo explícito que a proteção não está implementada nem comprovada.
- [x] 4.6 Revisar o preview isolado de `exits_post.xs` (`Matched: 1 of 153 files`, `UPDATE query exits POST`) e confirmar no workspace que `stock.exit` e o grant de `stockkeeper` já existem; não publicar o seed local, que também contém alterações de outras Changes, nem executar push real.

## 5. Fronteiras

- [x] 5.1 Não criar tabela nova de movimentação nem alterar `POST /entries`.
- [x] 5.2 Não alterar frontend Reflex, Saída visual ou integração de Entrada.
- [x] 5.3 Não publicar Xano, fazer commit ou push.
