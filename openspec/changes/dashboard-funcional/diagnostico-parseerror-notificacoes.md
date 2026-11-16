# Diagnóstico temporário do ParseError nas notificações

## Evidências e limites

Alvo informado: workspace 152211, branch v1, datasource live. Nenhuma requisição ao workspace ou publicação foi executada nesta etapa.

O usuário confirmou que o mesmo ParseError permaneceu após publicar a remoção dos campos nativos em eval. Essa hipótese anterior não explica suficientemente a falha. O marco foi corrigido e o erro anterior de lida não reapareceu na execução relatada; isso não identifica qual consulta falhou.

As duas referências restantes a `$db.purchase_request_history.purchase_request_id` estão nos joins com `$db.purchase_request.id`, na lista e no contador. O schema define int referenciando purchase_request. Não há entrada de pedido nem coerção de ID nessas consultas. Objeto, coleção ou null indevido não estão comprovados.

O MCP documenta joins como `$db.tabela.coluna == $db.outra_tabela.id`. Os joins do gráfico, confirmado funcional pelo usuário, seguem esse formato. Isso não comprova estes joins específicos. A exportação nexstock-dashboard-atual-19e4787461234159a4224c738893a9f3 mostra comparações entre colunas, mas é anterior às últimas publicações: ainda não permite excluir reinterpretação posterior pelo importador.

## Inspeção do histórico existente

1. No workspace 152211, selecionar branch v1 e abrir Request History do GET de notificações.
2. Selecionar a execução HTTP400 já ocorrida e abrir Function Stack.
3. Localizar as duas consultas purchase_request_history: a primeira produz a página; a segunda, a contagem.
4. Informar apenas número/nome da etapa com erro e se a lista terminou. Não copiar headers, variáveis, registros ou cURL.
5. Não clicar em Activate Debugger, pois isso reexecuta a requisição. Se a pilha não foi registrada ou foi truncada, não é possível recuperar retroativamente as etapas ausentes.

Fonte: https://docs.xano.com/maintenance-monitoring-and-logging/request-history.md

## Instrumentação local para revisão

O GET local contém dois wrappers try_catch delimitados por comentários BEGIN/END TEMP NOTIFICATIONS DIAG. Na preparação inicial, as consultas foram preservadas integralmente. A revisão posterior abaixo altera somente os nomes dos joins; testes com hashes continuam verificando todo o restante das consultas, normalizando apenas esses dois nomes e whitespace.

| Código fixo | Significado, se emitido |
| --- | --- |
| NOTIFICATIONS_DIAG_LIST_QUERY_FAILED | Falha capturada na consulta da lista. O contador não foi executado. |
| NOTIFICATIONS_DIAG_COUNT_QUERY_FAILED | A lista terminou e a falha foi capturada na consulta do contador. |

Cada catch termina com precondition(false), error_type standard. O diagnóstico passa a retornar HTTP500/ERROR_FATAL com um código de etapa, embora o erro original tenha sido HTTP400. Essa diferença é temporária: não corrige nem reclassifica a regra de negócio. Não retorna sucesso, página vazia ou contador zero em caso de falha. O erro bruto não é registrado nem retornado.

Não há logging, dados pessoais, IDs de pedidos, tokens, payloads, valor do marco, novas funções ou rotas. Autenticação e validação do marco permanecem antes das consultas. Joins, filtros por auth.id e escopo próprio/global, eventos, ordenação, paginação, contador e contrato de sucesso permanecem iguais. Não há consultas adicionais nem escritas.

Se o erro continuar original sem um código diagnóstico, não atribuir a falha a uma consulta: pode ocorrer antes da entrada no try, fora dos wrappers ou em uma versão publicada diferente. Conferir primeiro export atual somente dos scripts. A captura desse ParseError e o escopo das saídas page/unread_total ainda dependem do runtime Xano; sintaxe válida não comprova essas propriedades.

## Revisão posterior: nomes dos joins

Com autorização para corrigir uma inconsistência localizada, os joins das duas consultas passaram de `request` para `purchase_request` e de `read_state` para `purchase_request_notification_read`. As referências já usavam `$db.purchase_request.*` e `$db.purchase_request_notification_read.*`. Agora cada referência corresponde ao nome declarado no join, seguindo o padrão dos GETs funcionais de compras e movimentações e os exemplos oficiais: https://docs.xano.com/xanoscript/function-reference/database-operations#joins

São quatro substituições de nomes no GET. Tabelas, tipos inner/left, condições entre colunas, filtro de recibo por auth.id, autorização próprio/global, marco, eventos, projeção, paginação e contador permanecem iguais. Nenhum outro endpoint foi alterado. Um teste estático verifica que todos os nomes usados em referências `$db` estão declarados na consulta; os hashes anteriores protegem o restante do código das duas consultas.

A divergência de nomes é verificável no código; sua relação causal com o ParseError ainda não foi demonstrada no runtime. O MCP e os exemplos oficiais validam o padrão adotado, mas não executam essas consultas. A última exportação disponível antecede as últimas publicações. Por isso, os identificadores temporários LIST/COUNT continuam presentes. Se a falha persistir, usar a etapa retornada e a definição publicada atual para investigar, sem trocar joins ou filtros por tentativa. Esta revisão não declara o erro resolvido.

## Preview preparado, não executado

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_notifications_get.xs" --no-guids --no-fast --no-writeback --dry-run
```

Após revisão e autorizações separadas de publicação/execução, realizar uma única leitura GET autorizada para identificar o código e parar antes de outra mudança funcional. Não executar PATCH, criar recibos ou alterar o marco.

## Remoção

Depois de localizar a etapa, retirar apenas os wrappers try_catch/catch e comentários BEGIN/END TEMP, preservando as consultas internas. Não restaurar o arquivo inteiro de Git ou backup, pois há outras alterações locais. Rever/remover o teste temporário de hashes junto com a instrumentação e manter os testes permanentes de contrato e autorização.

## Validação local

40 testes direcionados aprovados, incluindo quatro testes da instrumentação: consultas inalteradas, identificadores distintos, parada em erro e ausência de logging/escritas. Os testes não executam o mecanismo Xano. GET válido no MCP. Aceitação do importador, captura dos erros e localização da etapa em runtime permanecem pendentes.
