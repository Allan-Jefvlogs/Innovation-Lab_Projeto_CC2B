# Design: Validacao avancada das operacoes de estoque

## Historico e transferencia

A Change `operacao-backend-saida-estoque` registrou a cobertura funcional executada com o
Produto ficticio ID 6 e redefiniu a tarefa 4.4 para refletir somente essa cobertura. O texto
original da tarefa 4.4 e mantido como historico no design daquela Change. Os cenarios
avancados listados aqui nao foram executados nem aprovados; esta Change recebe formalmente
esses itens para acompanhamento.

A Change original continua documentando que a conta Free nao oferece Sandbox ou Data Source
adicional. A mesma limitacao vale para este plano. A Change `seguranca-concorrencia-estoque`
foi cancelada/adiada para esta entrega academica porque a solucao exigiria recursos de plano
pago. Concorrencia e overselling nao sao pre-requisito nem parte do escopo desta Change; a
ausencia de garantia permanece registrada e nenhum teste daqui pode ser usado como prova de
seguranca concorrente. A Change de concorrencia e seu historico sao registro do trabalho
proposto, nao implementacao entregue.

## Decisao de adiamento e estado das evidencias

Por decisao do projeto, esta Change foi adiada e retirada do escopo da entrega academica atual. O plano gratuito do Xano nao oferece Sandbox nem Data Source adicional, e nao existe harness isolado aprovado para os testes avancados. As evidencias runtime funcionais de Entrada e Saida permanecem nos designs das Changes arquivadas `operacao-backend-entrada-estoque` e `operacao-backend-saida-estoque`; elas nao substituem os testes listados abaixo.

Permanecem sem comprovacao: (1) rollback de `POST /entries` depois da primeira escrita; (2) rollback de `POST /exits` depois da primeira escrita; (3) rejeicao de Produto ativo sem linha em `inventory_stock`, para Entrada e Saida; (4) persistencia e retorno de `data_hora` personalizada; (5) comparacao de todos os campos da resposta de cada endpoint com os registros persistidos; e (6) invariantes de saldo e movimentos para todas as falhas, rejeicoes e operacoes confirmadas. Nenhum desses cenarios e declarado aprovado por existir codigo ou contrato documentado.

A protecao contra lost update e overselling em requisicoes simultaneas tambem nao foi comprovada. A Change `seguranca-concorrencia-estoque` foi arquivada sem aplicar suas specs, por depender de recursos pagos do Xano; seu arquivamento nao implementa nem valida protecao concorrente. As 11 tarefas ainda abertas permanecem abertas; com a tarefa 1.1 ja concluida, o estado continua em 1/12.

## Plano de validacao e criterios

| Caso | Pre-requisitos e risco | Evidencia e criterio de aprovacao |
|---|---|---|
| Rollback depois da primeira escrita, em Entrada e Saida | Ambiente isolado ou harness aprovado; Produto e saldo ficticios; mecanismo para provocar falha apos editar `inventory_stock` e antes de adicionar `inventory_movement`. Risco alto se executado no datasource compartilhado; nao executar nele. | Capturar saldo e movimentos antes/depois. Cada chamada deve falhar e deixar saldo identico ao anterior, sem movimento parcial. Se qualquer escrita parcial permanecer, reprovar e interromper os testes. |
| Linha de saldo ausente | Ambiente isolado; Produto existente e ativo sem linha `inventory_stock`. Remover ou preparar essa condicao somente no ambiente descartavel. | `POST /entries` e `POST /exits` devem rejeitar com `STOCK_BALANCE_NOT_FOUND`, sem alterar saldo nem criar movimento. Se o comportamento publicado divergir, registrar o erro real e parar; nao normalizar para a expectativa. |
| `data_hora` personalizada | Ambiente que permita movimento ficticio persistente, autorizacao explicita se compartilhado, valor timestamp conhecido com fuso definido. | Para Entrada e Saida, comparar o instante informado na resposta e no registro persistido, normalizando fuso. Divergencia, valor substituido por `now` ou movimento inesperado reprova o caso. |
| Resposta completa de Entrada e Saida | Chamadas validas apenas em ambiente autorizado e com saldo/produto ficticios; salvar resposta sem credenciais. | Conferir `movement_id`, `product_id`, `tipo`, `quantidade`, `saldo_anterior`, `saldo_atual`, `data_hora`, `supplier_id`, `user_id`, `motivo` e `observacao` contra o movimento e saldo persistidos. Campos ausentes ou divergentes reprovam. |
| Invariantes apos falhas e rejeicoes | Capturar saldo, movimentos e identificadores antes de cada caso; executar cada falha no ambiente permitido. | Operacao rejeitada ou revertida nao deixa alteracao de saldo nem novo movimento. Para operacoes confirmadas, saldo final deve corresponder ao saldo inicial mais Entradas confirmadas menos Saidas confirmadas; cada movimento deve corresponder a uma operacao confirmada. |

## Procedimento seguro

1. Confirmar endpoint e versao publicados, identidade do ambiente e permissao de leitura.
2. Antes de qualquer escrita, obter ambiente isolado/harness aprovado ou autorizacao explicita
   que cubra os registros ficticios e todas as chamadas previstas.
3. Registrar identificadores, saldo e movimentos antes do caso; enviar uma chamada por vez,
   sem repetir uma chamada ambigua antes de reconciliar o estado.
4. Consultar saldo e movimentos depois de cada chamada e guardar status, codigo, resposta e
   comparacao antes/depois sem tokens, senhas ou cabecalhos de autenticacao.
5. Interromper diante de divergencia de contrato, alteracao inesperada, resposta ambigua,
   indisponibilidade de leitura ou qualquer escrita parcial.

Movimentos de auditoria no datasource compartilhado nao devem ser apagados como limpeza.
Falha induzida apos escrita, ausencia deliberada de linha de saldo ou outra preparacao
destrutiva so pode ocorrer em ambiente isolado descartavel ou harness aprovado.
