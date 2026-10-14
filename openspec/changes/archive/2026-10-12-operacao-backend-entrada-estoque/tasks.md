# Tasks: Operação backend de Entrada de Estoque

## 1. Inspeção e contrato

- [x] 1.1 Confirmar que `inventory_stock` já possui saldo decimal e índice único por Produto.
- [x] 1.2 Confirmar que não existe tabela nem endpoint local de movimentação e revisar a specification consolidada.
- [x] 1.3 Confirmar a autorização central, o seed aditivo e as permissões atuais.
- [x] 1.4 Validar na documentação XanoScript operações de tabela, endpoint e transação; confirmar em runtime que `db.direct_query` não é suportado pela instância atual.

## 2. Persistência e autorização

- [x] 2.1 Criar tabela `inventory_movement` com referências, tipo, quantidade, data/hora, ator, Fornecedor opcional, motivo e observação.
- [x] 2.2 Acrescentar `stock.entry` e o grant inicial somente de `stockkeeper` ao seed aditivo.

## 3. Operação de entrada

- [x] 3.1 Criar `POST /entries` autenticado no grupo `Inventory Stock` e validar `stock.entry` dentro da transação.
- [x] 3.2 Validar Produto existente/ativo, quantidade positiva, motivo e Fornecedor opcional existente/ativo.
- [x] 3.3 Resolver timestamp opcional para o `now` do servidor quando omitido.
- [x] 3.4 Atualizar saldo com `db.get` + `db.edit` suportados e criar o movimento na mesma transação; documentar a limitação de lost update concorrente.
- [x] 3.5 Retornar identificadores, contexto e valores de saldo anterior/atual; mapear falhas de edição sem escrita parcial.

## 4. Verificação

- [x] 4.1 Validar todos os XanoScripts adicionados/alterados no Xano Developer MCP.
- [x] 4.2 Executar `openspec validate operacao-backend-entrada-estoque --strict`.
- [x] 4.3 Executar `git diff --check`.
- [x] 4.4 Registrar a cobertura funcional executada: Entrada real de 10,75 KG em `POST /entries` no Produto fictício ID 6, saldo atualizado e movimento confirmado no Histórico; e testes diretos no backend Xano, em `POST /entries` e `POST /exits`, confirmados pelo usuário com os resultados esperados para Produto inexistente/inativo, ausência de autenticação, usuário sem a permissão necessária, quantidade zero/negativa e motivo vazio. As fontes e limites das evidências constam em design.md. Rollback, concorrência, timestamp personalizado, saldo ausente e inspeção completa das respostas ficam fora deste escopo e são acompanhados nas Changes referenciadas.
- [x] 4.5 Revisar o preview isolado de `entries_post.xs` (`Matched: 1 of 153 files`, `UPDATE query entries POST`, sem operação `DELETE`), confirmar no painel Xano que `stock.entry` está no catálogo e concedida a `stockkeeper`, e registrar que tabelas e funções compartilhadas necessárias já estão disponíveis; esta tarefa confirma o escopo do preview, não uma publicação efetiva.

## 5. Fronteira frontend

- [x] 5.1 Manter o Reflex sem chamada transacional e o botão Registrar entrada inalterado nesta change.
