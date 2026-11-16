# Publicação seletiva futura — notificações e gráfico

Implementação local; nenhum comando abaixo foi executado nesta etapa. Alvo pretendido: workspace 152211, branch v1. Antes de publicar, exportar versões atuais sem records/env e comparar com os arquivos locais, preservando alterações remotas recentes.

## Ordem de revisão por dry-run

1. `table/purchase_request_notification_read.xs`: somente se a tabela ainda não existir; se existir, preservar campos/índices publicados e confirmar UNIQUE user_id/history_id.
2. `function/inventory/purchase_request_notification_all_access.xs`: dependência já usada por compras; comparar e não republicar se já estiver equivalente. Não executar provisionamento ou alterar grants.
3. GET de notificações: projeção dos metadados, dados.status_novo sanitizado e escopo próprio/global.
4. PATCH de leitura: recibo individual; identidade vem de auth.id. Concorrência/rollback não comprovados por testes locais.
5. GET do gráfico: aceita period=7d/30d/12m, mantendo compatibilidade de entrada com 7d por padrão. O frontend novo precisa desta versão para os períodos adicionais.

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "table/purchase_request_notification_read.xs" --no-guids --no-fast --no-writeback --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "function/inventory/purchase_request_notification_all_access.xs" --no-guids --no-fast --no-writeback --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_notifications_get.xs" --no-guids --no-fast --no-writeback --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_notifications_by_id_read_patch.xs" --no-guids --no-fast --no-writeback --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/movements_dashboard_get.xs" --no-guids --no-fast --no-writeback --dry-run
```

Não incluir senha, compras, entradas/saídas, Auditoria ou e-mail neste lote. Não usar sync/delete/records/env/force. Se a CLI falhar com ENOMEM, interromper; não inferir estado remoto.

## Configuração e ativação após autorização separada

- Definir no Xano NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT como timestamp de ativação aprovado, em formato aceito pelo Xano. Conferir sua comparação com data_evento (timestamp em milissegundos no contrato). Sem marco, a central falha fechada. Não retroagir o marco nem criar eventos artificiais.
- Confirmar runtime nativo do gráfico, avanço mensal e todos os metadados. Validar contagem de operações (não soma de quantidades), intervalo semiaberto, timezone São Paulo, zeros reais e cinco recentes globais. Avaliar tempo de leitura para 12 meses no Free; não executar teste de carga.
- Conferir, com contas autorizadas, leitor próprio, read+manage global, administrador, sem read, sessão expirada e 429. Validar recibo de leitura somente com autorização de escrita separada.
- Só após publicação/configuração e validações autorizadas, iniciar o Reflex com NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED=true e NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED=true no ambiente local. Reiniciar o processo porque flags são lidas no import. Nenhum .env foi alterado nesta etapa; senha permanece bloqueada.
- Carga fria autorizada: até cinco GETs de dados (produtos, estoque, resumo de compras, gráfico+recentes, notificações), além da sessão. Cada troca de período faz no máximo um GET adicional, dispensado com cache válido. Sem polling ou retry automático.

## Critérios ainda pendentes

Preview/importação reais, avaliação Xano do stream e avanço mensal, isolamento em runtime, confirmação do marco, colisão concorrente de recibos, validação visual autenticada em desktop/móvel e desempenho de 12 meses. Compilação, oráculos de calendário e mocks não comprovam essas propriedades.

## Revisão após relato de publicação

O usuário informou publicação da tabela e dos três endpoints. Antes de atualizar novamente, obter export posterior à publicação para preservar eventuais alterações remotas; a revisão anterior de 172 documentos não continha esses objetos. A correção local atual altera somente os três endpoints (não exige republicar tabela/helper): gráfico com parse de 00:00:00 explícito; GET/PATCH de notificações com validação estrita e normalização do marco. Os comandos de dry-run individuais acima continuam aplicáveis a esses três arquivos. Nenhum deles foi executado nesta correção.

O marco deve ser o instante já aprovado de ativação, em Unix milliseconds (13 dígitos positivos). Não gerar um marco novo automaticamente para tentar corrigir o erro, pois isso mudaria quais eventos são visíveis. Conferir nome exato, workspace 152211 e valor salvo em Settings → Environment Variables → Manage; não compartilhar valores nem usar util.get_env para listar configurações no debugger. O nome da variável é de workspace, não uma flag local do Reflex. Ausência real ou escopo/configuração incorretos continuam bloqueando, mesmo com o código corrigido.

## Diagn?stico remanescente ? 2026-11-12

O usu?rio confirmou funcionamento visual do gr?fico nos tr?s per?odos. O painel de recentes vazio n?o tem causa remota comprovada: a consulta local n?o filtra per?odo, ordena por data_hora/id desc, usa joins left e p?gina 1 de cinco registros. O frontend conserva objetos mesmo fora do per?odo; anteriormente descartava silenciosamente itens n?o objetos, passando agora a rejeit?-los. Diagn?stico adicional registra apenas metadados se recentes.items vier vazio enquanto a s?rie possuir opera??es. N?o cria outra consulta e n?o substitui os dados vazios por movimentos inventados.

O resumo publicado no export nexstock-dashboard-atual-19e4787461234159a4224c738893a9f3 preserva solicitacoes_abertas, autoriza??o e escopo. O reflex.log local tem modifica??o em 11/11/2026 16:35 e registra ConnectError nesse GET, sem c?digo HTTP. N?o comprova o problema atual. Acrescentado log sanitizado de campo ausente/tipo inv?lido, preservando valida??o estrita e cache com aviso. N?o alterar resumo/Compras por hip?tese.

A documenta??o do MCP confirma $env.NOME para vari?veis customizadas; $env.$NOME ? reservado para vari?veis de sistema. MISSING indica reprova??o na guarda de presen?a antes de trim/convers?o. O export dispon?vel cont?m a vers?o anterior, com != null; n?o comprova a vers?o atualmente servida ap?s as ?ltimas publica??es. N?o trocar sintaxe ou marco sem evid?ncia.

Procedimento somente de leitura, com sess?o autorizada:
1. Em Settings ? Environment Variables ? Manage do workspace 152211, conferir nome exato NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT e valor j? salvo, sem editar, copiar ao chat ou listar outras vari?veis. O formato esperado pelo c?digo corrigido ? Unix milliseconds em 13 d?gitos.
2. Conferir no c?digo publicado GET/PATCH se existem activation_raw, !== null e os erros EMPTY/INVALID/CONVERSION_FAILED; nome da branch v1 e contexto live. N?o executar PATCH. N?o usar debugger para inspecionar $env inteiro.
3. Pelo hist?rico do GET autorizado, conferir apenas tipos e contagens de serie, recentes, recentes.items, quantidade de recent_page.items e formato da resposta. Se recent_page tiver registros e resposta n?o tiver, revisar a proje??o; se a consulta j? vier vazia, revisar seu output/paging publicado. N?o presumir que totals:false ? a causa.
4. Obter a linha sanitizada atual de GET /purchase_requests/summary (status, tipo de exce??o/origem/c?digo). Se houver erro HTTP200 de contrato, o novo log identifica solicitacoes_abertas sem valor/payload. Se houver ConnectError, corrigir conectividade; se 429, aguardar cooldown sem retries autom?ticos.

Valida??o local: 85 testes direcionados com mocks/estrutura/calend?rio; Reflex compile --dry e OpenSpec strict aprovados; quatro contratos XS v?lidos no MCP. Sem chamadas remotas, runtime, PATCH, altera??o de configura??o, publica??o ou comprova??o visual da densidade dos r?tulos. Nenhum endpoint alterado nesta etapa; n?o h? novo push indicado sem as evid?ncias acima.

## Evid?ncia adicional de recentes ? 2026-11-12

O usu?rio inspecionou Request History e confirmou GET /movements/dashboard HTTP 200 com recentes.items=[null,null,null,null,null], curPage=1, perPage=5 e serie com sete pontos v?lidos. Isso comprova retorno inv?lido no backend e explica o descarte anterior no frontend; n?o ? aus?ncia de movimenta??es. O resumo de compras continua sem log atual.

Corre??o local concentrada na proje??o: substituir o map de objetos inline na resposta por foreach ($recent_page.items) com array.push em recent_items, igual ao padr?o existente no endpoint /movements. A consulta, joins left, ordena??o, pagina??o, datas e toda a s?rie permanecem intactos. N?o acrescentar output que omita campos nem fazer GET adicional. O mecanismo exato de avalia??o/serializa??o do map no runtime n?o foi reproduzido localmente; se a resposta continuar inv?lida ap?s publica??o autorizada, inspecionar somente o tipo/contagem e presen?a dos campos p?blicos de recent_page.items antes da transforma??o.

Preparar revis?o e somente depois preview seletivo de api/inventory_stock/movements_dashboard_get.xs. N?o h? motivo comprovado para republicar o resumo de compras nesta etapa. Validar depois que recentes.items cont?m objetos e n?o null, no m?ximo cinco, e que trocar per?odo n?o restringe as recentes. Nenhum preview ou push foi executado.

## Corre??o exclusiva do GET de notifica??es ? campo lida

O usu?rio confirmou que corrigiu o nome da vari?vel no painel e que o runtime passou a rejeitar `$db.purchase_request_notification_read.id != null|as("lida")`. O erro identifica a express?o calculada em eval como incompat?vel na execu??o observada, n?o uma falha do marco ou de autoriza??o.

O GET local projeta agora `read_receipt_id: $db.purchase_request_notification_read.id`, incluindo `items.read_receipt_id` no output da consulta. O join left continua condicionado a history_id do evento E user_id de auth.id. Sem recibo desse usu?rio, o ID ? null. Depois da consulta, foreach/array.push constr?i o mesmo objeto p?blico com `lida: ($notification.read_receipt_id !== null)`. O ID auxiliar n?o ? devolvido. A troca da proje??o final inline por stack expl?cito evita repetir o padr?o que j? produziu elementos null nas recentes, sem alterar descri??es ou demais campos.

A segunda consulta (unread_total), os dois filtros de escopo/eventos/marco, a pagina??o, autoriza??o e ordena??o permanecem inalterados. N?o h? consultas por item nem novas escritas, tabelas, vari?veis ou altera??o do marco. PATCH de leitura e ?reas de compras/recebimento/gr?fico n?o foram editados.

Preview preparado, n?o executado:

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_notifications_get.xs" --no-guids --no-fast --no-writeback --dry-run
```

Ap?s revis?o/publica??o autorizadas, verificar com leitura autorizada que HTTP 200 retorna items como objetos, lida como booleano, itens sem recibo pr?prio false e com recibo pr?prio true, mantendo itemsTotal/curPage/perPage/unreadTotal. Usar recibos existentes; n?o marcar eventos como lidos nesta etapa. Aceita??o do importador e comportamento do join/booleano no servidor continuam pendentes. Testes de estrutura/mocks e valida??o MCP n?o comprovam runtime.

## ParseError posterior na refer?ncia ao pedido

O usu?rio informou HTTP 400 ParseError: Invalid value for param:"purchase_request_history.purchase_request_id" ap?s publicar a corre??o de lida. O erro n?o identifica sozinho qual das duas consultas falhou. No c?digo revisado, h? duas refer?ncias entre colunas nos joins request e uma refer?ncia adicional em eval que redefine purchase_request_id com o pr?prio campo da tabela-base. O schema confirma int com refer?ncia a purchase_request; n?o h? passagem expl?cita de objeto ou cole??o nesse par?metro no c?digo local.

A hip?tese principal ? avalia??o da proje??o redundante em eval; ainda n?o foi comprovada em runtime. Corre??o local: remover evals dos campos nativos do hist?rico, selecionar items.id/purchase_request_id/evento/data_evento diretamente e renomear id para history_id somente ao montar o objeto p?blico. O ?nico eval restante ? read_receipt_id, proveniente da tabela relacionada. O GET de detalhes j? consulta o hist?rico usando seus campos nativos. N?o converter ou substituir IDs, n?o remover joins nem filtros para contornar o erro.

Os joins request/read_state, os filtros de autoriza??o pr?prio/global, eventos e marco, ordena??o, pagina??o e consulta unread_total n?o foram modificados. Se Request History apontar falha na segunda consulta, a hip?tese de eval n?o explica essa etapa e a corre??o n?o pode ser apresentada como suficiente: ser? necess?rio conferir a defini??o efetivamente publicada do join e sua serializa??o. Solicitar apenas nome/posi??o da etapa que falhou, nunca payload de pedidos ou credenciais.

Valida??o local: 36 testes direcionados aprovados, GET v?lido no MCP. Compila??o Reflex/OpenSpec e checagem de whitespace tamb?m fazem parte da revis?o; nenhum runtime remoto foi executado. Permanece pendente confirma??o da etapa da falha e, ap?s revis?o/publica??o autorizadas, HTTP200, metadados, IDs inteiros, lida booleana e isolamento usando leituras autorizadas. O comando seletivo continua exclusivamente o GET de notifica??es, sem execut?-lo nesta etapa.
