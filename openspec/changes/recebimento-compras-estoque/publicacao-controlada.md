# Plano e histórico de publicação controlada

## Preparação somente de leitura

Confirmar workspace 152211, branch v1 e datasource. Preservar export atual dos seis objetos abaixo fora do lote/Git, sem records/env ou credenciais. Comparar conteúdo integral e GUIDs, pois o worktree possui outras changes. Não sobrescrever trabalho de colegas. Conferir product/user/supplier, purchase_request_history, autorizador e helper de escopo, sem executar provisionamento.

### Estado da revisão em 12/11/2026

A tentativa anterior na CLI instalada (1.3.4) falhou com uv_os_get_passwd returned ENOMEM. Posteriormente, o usuário concluiu a exportação pelo PowerShell. A revisão atual usa os 172 documentos XanoScript presentes em `C:\Users\Allan\AppData\Local\Temp\nexstock-recebimento-v1-7edd9c89ce704481988c1ceb312dbc09`. O backup_xano_antes_compras não foi usado como versão atual. Não foi feito novo pull, dry-run, publicação ou acesso a registros nesta revisão. O export é evidência das definições exportadas, não de rollback, migração ou comportamento em runtime.

### Resultado da comparação semântica com o export atual

Todos os seis objetos já existem no export. Os caminhos abaixo são relativos à raiz desse export; o lote futuro deve atualizar os objetos existentes, nunca criar duplicatas.

| Objeto | Caminho no export | Diferenças e decisão |
| --- | --- | --- |
| purchase_request | `table/purchase_request.xs` | Após reconciliação local, preserva filters=trim e visibility="internal" de email_destinatario, quantidade_recebida sem default explícito e todos os índices. A única adição funcional ao schema é unidade_medida_solicitada nullable. |
| inventory_movement | `table/inventory_movement.xs` | Preserva campos, referências e índices existentes. Adiciona purchase_request_id nullable referindo purchase_request, chave_recebimento nullable, unidade_medida nullable, índice do vínculo e UNIQUE da chave. A definição é aditiva; importação, defaults e múltiplos NULL ainda precisam de conferência. |
| POST /purchase_requests | `api/inventory_stock/purchase_requests_POST.xs` | Preserva criação, autorização, idempotência com destinatário, histórico, transação e intenções de e-mail. Adiciona snapshot da unidade no db.add e inicializa quantidade_recebida com 0. As três preconditions agora seguem a forma remota, sem error_type explícito. |
| GET /purchase_requests | `api/inventory_stock/purchase_requests_GET.xs` | Mantém read, helper próprio/global, filtros, ordenação, totals=true e itemsTotal/curPage/perPage. Adiciona unidade ao output e usa a mesma forma de join do export. |
| GET /purchase_requests/by_id/{request_id} | `api/inventory_stock/purchase_requests/by_id/request_id_GET.xs` | Mantém autorização e isolamento antes de ler produto/histórico, paginação e metadados do histórico. Adiciona unidade em solicitacao. Reorganização e wrappers de expressão exportados não indicam perda dos campos anteriores. |
| POST /entries | `api/inventory_stock/entries_POST.xs` | Preserva entradas avulsas e validações iniciais. Se db.edit retornar null, impede as escritas seguintes e retorna STOCK_BALANCE_NOT_FOUND após a transação. Exceções do banco propagam sem catch interno: os códigos específicos anteriores de deadlock e falha de saldo não são garantidos. Vínculo, movimento, pedido e histórico estão na mesma transação. |

#### Bloqueios e diferenças que não devem ser sobrescritas

- A reconciliação local restaurou em purchase_request o trim e a visibilidade interna já publicados de email_destinatario e removeu o default adicional de quantidade_recebida. O POST continua gravando 0 explicitamente em pedidos novos; registros antigos não são alterados pelo código local.
- Todos os índices anteriores das duas tabelas estão presentes no local. Não há declaração de exclusão/recriação, mas isso não garante o plano efetivo de migração: o preview deve confirmar atualização aditiva do mesmo objeto.
- Em entries, o retorno null de db.edit desvia todas as escritas subsequentes e produz STOCK_BALANCE_NOT_FOUND. Exceções de banco não são capturadas dentro da transação e devem propagá-la como falha; isso não comprova rollback em runtime. Os erros específicos STOCK_CONCURRENCY_CONFLICT e STOCK_UPDATE_FAILED do remoto não são garantidos na versão local. A compatibilidade das mensagens para consumidores avulsos e a hipótese de retorno null sem alteração devem ser validadas em teste controlado.
- As declarações explícitas de standard no POST e inner no GET foram removidas para preservar a forma remota. Não se afirma equivalência dos defaults anteriores sem teste real.
- No export estão presentes authorize_permission, purchase_request_notification_all_access, purchase_request_history, purchase_request_email_delivery e os helpers de e-mail utilizados pelo POST. Não há dependência nova de dispatcher executado por este lote.
- O fluxo de recebimento usa operações nativas, sem Direct Database Query. A declaração nullable/UNIQUE é compatível com a proposta, mas múltiplos NULL, integridade referencial efetiva e rollback não foram testados no banco live. Pedidos antigos sem unidade permanecem sem inferência automática e não podem receber vínculo até confirmação autorizada.

**Decisão registrada naquela revisão:** os seis arquivos poderiam ser inspecionados pelos dry-runs abaixo, um por vez, conferindo identidade dos objetos, ausência de remoções e dependências. A diferença nos códigos de falha de entries deveria ser aceita antes de publicar. Naquele momento, não havia dry-run ou publicação nessa revisão. Os relatos posteriores do usuário estão separados ao final deste documento e não alteram retroativamente essa constatação histórica.

A inspeção somente de leitura do código instalado da CLI confirma directory/workspace/branch no pull, env=false e records=false por padrão; no push confirma include/directory/dry-run/no-guids. Isso confirma a sintaxe preparada, não a conexão ou autenticação remota.

No PowerShell externo em que a CLI funcionar, executar a partir da raiz do projeto, criando destino novo fora dele:

```powershell
$exportRecebimento = Join-Path $env:TEMP ("nexstock-recebimento-v1-" + [guid]::NewGuid().ToString("N"))
xano.cmd workspace pull --workspace 152211 --branch v1 --directory "$exportRecebimento"
```

Não acrescentar env, records, draft, sync-state ou verbose. O pull faz leitura remota e grava somente o export no destino escolhido. Não sobrescrever xano nem o backup anterior. Conferir o sucesso antes de usar os arquivos e não compartilhar configurações/segredos.

Localizar os documentos exportados e identificar declarações, não apenas nomes de arquivos. Comparar os seis objetos por tabela ou combinação api_group/rota/verbo; confirmar GUID/ID e alterações de colegas. Export pode usar nomes como entries_POST.xs, purchase_requests_GET.xs e purchase_requests/by_id/request_id_GET.xs. Não classificar ausência apenas por divergência de caminho.

A comparação com Git isoladamente não detectava as propriedades remotas de email_destinatario e a diferença de default de quantidade_recebida, agora reconciliadas. Nenhuma tabela ou endpoint novo é esperado neste lote; se preview anunciar criação/recriação de objeto que já existe ou remoção de campo/índice, interromper. Os GUIDs constam do export; os arquivos locais não os contêm, por isso conferir a correspondência por tabela ou api_group/rota/verbo no preview, sem presumir identidade apenas pelo nome do arquivo.

## Ordem e previews seletivos

Conferir o suporte da CLI antes de executar, parar em ENOMEM e não repetir tentativas ou ampliar o lote. Cada preview deve mostrar apenas um objeto:

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "table/purchase_request.xs" --no-guids --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "table/inventory_movement.xs" --no-guids --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_post.xs" --no-guids --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_get.xs" --no-guids --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_by_id_get.xs" --no-guids --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/entries_post.xs" --no-guids --dry-run
```

Não usar sync/delete/records/env/force. Não publicar PATCH de status/cancelamento, dispatcher ou Auditoria neste lote. Nova autorização é obrigatória para publicar.

## Migração aditiva e ativação

1. Conferir e adicionar unidade_medida_solicitada nullable na compra, sem preencher pedidos antigos.
2. Conferir e adicionar vínculo nullable purchase_request_id, chave_recebimento nullable UNIQUE e unidade_medida nullable na movimentação. Confirmar referências e múltiplos NULL antes de ativar, sem default 0 ou string vazia. Não remover índices anteriores.
3. Publicar seletivamente POST de compras (delta desta etapa: um campo de snapshot no db.add), GETs e POST /entries, nessa ordem. Comparar as versões remotas para preservar e-mail e outras mudanças já publicadas.
4. **Plano histórico anterior aos relatos de publicação:** manter `NEXSTOCK_PURCHASE_RECEIPTS_ENABLED=false` até APIs/schema validados. O código local atual tem padrão `true`; portanto, para manter a proteção operacional enquanto a verificação remota independente estiver incompleta, definir explicitamente `false` no ambiente do processo. Nenhum `.env` foi alterado nesta implementação.

Sem novo endpoint de estoque. O payload avulso anterior é preservado; a resposta do POST é aditiva. Não há endpoint para confirmar unidade histórica nesta entrega: pedidos antigos NULL exigem conferência e procedimento autorizado separado ou entrada avulsa.

## Testes funcionais futuros, com autorização separada

- Usar conta/produto/pedido fictícios identificados, sem dispatcher ou e-mails. Confirmar unidade e estado aguardando_recebimento.
- Criar uma nova solicitação fictícia de 10 unidades para produto fictício ativo e com estoque insuficiente, usando conta autorizada. Conferir unidade preservada e avançar sequencialmente até aguardando_recebimento; não inferir unidade de um pedido antigo.
- Registrar entrada vinculada de 4 unidades: recebido=4, restante=6, status=recebimento_parcial, active_product_id preservado, saldo inicial S acrescido de 4 e um evento recebimento_registrado associado ao movimento.
- Registrar segunda entrada vinculada de 6 unidades, com outra chave: recebido=10, status=concluida, active_product_id=null, saldo S+10 e segundo evento/movimento. Não selecionar os estados automáticos manualmente.
- Repetir mesma chave/payload: mesmo movimento, sem novo saldo/recebido/histórico. Resposta de repetição tem saldos null, sem fabricar valores da resposta anterior.
- Conferir excesso, unidade/produto incompatível, legado NULL, falta de grants, status terminal e mesma chave com payload diferente: nenhuma nova gravação.
- Registrar entrada avulsa de 1 unidade no produto de teste e conferir que compra e histórico de compras não mudam; saldo passa a S+11. Para prova mais forte de não inferência, essa entrada pode ser feita entre os recebimentos de 4 e 6: recebido continua 4/status parcial até a segunda entrada vinculada, com saldo final também S+11. Pedido parcial continua visível em /compras mesmo que produto saia de /reposicao.
- Ler saldo, movimento, pedido e histórico após cada operação. Confirmar HTTP reais em vez de presumir 409/422. Não declarar rollback comprovado sem falha dentro da transação e leituras finais correspondentes. Uso sequencial, sem garantias avançadas de concorrência.

## Interrupção e recuperação

Em falha de preview/migração/teste, parar e manter flag desligada. Não apagar campos, índices ou dados automaticamente. Restaurar um contrato anterior somente após comparação e revisão de compatibilidade, preservando schema aditivo e dados.

Não restaurar o endpoint antigo de Entrada enquanto houver recebimentos em andamento ou tentativas ambíguas: ele pode ignorar campos novos e registrar entrada avulsa sem idempotência. A flag não deve ser habilitada contra essa versão. Resposta HTTP 200 sem contrato de recebimento confirmado bloqueia também a recuperação por POST, exigindo conferência por leitura antes de reenviar; não basta o cliente rejeitar a resposta após uma possível gravação.

Timeout após possível commit exige reconciliação da chave/movimento/pedido. No mesmo State, Recuperar recebimento reutiliza chave e payload. A tentativa não tem persistência durável independente: se State expirar ou servidor reiniciar, conferir por leitura antes de registrar outra entrada equivalente. Não criar nova chave automaticamente e não afirmar exatamente uma execução comprovada em runtime.

## Atualização histórica — relatos posteriores do usuário

Os registros abaixo são relatos fornecidos pelo usuário nesta conversa do projeto. Não foram executados nem verificados independentemente pelo Codex; não há saídas brutas, capturas do painel ou logs anexados a este documento. As datas dessas ações não foram informadas. Eles complementam o retrato de preparação de 12/11/2026 acima, sem transformar aquela revisão em evidência de publicação ou runtime.

O usuário confirmou manualmente que inspecionou as definições das tabelas `purchase_request` e `inventory_movement` no workspace **152211**, branch **v1**, datasource **live**. Também informou anteriormente que os campos de recebimento e os índices de consulta/UNIQUE estavam visíveis no painel. Como as capturas ou um export das definições não foram anexados, este registro comprova somente que houve essa confirmação informada; não permite revisar cada propriedade remota nem afirmar que a visão permanece atual.

### Seis previews seletivos

O usuário informou que concluiu os seis dry-runs e observou:

| Objeto | Resultado informado |
| --- | --- |
| `purchase_request` | UPDATE + 1 ADD_FIELD |
| `inventory_movement` | UPDATE + 3 ADD_FIELD |
| POST `/purchase_requests` | UPDATE |
| GET `/purchase_requests` | UPDATE |
| GET `/purchase_requests/by_id/{request_id}` | UPDATE |
| POST `/entries` | UPDATE |

Segundo o mesmo relato, nenhum preview indicou exclusão ou criação de tabelas. O resumo não documenta os detalhes completos dos previews, GUIDs, referências não resolvidas ou todos os critérios de revisão; portanto, não comprova por si só a identidade integral dos objetos nem a aplicação das alterações.

### Publicação e testes funcionais relatados

O usuário informou posteriormente que os seis documentos foram publicados e que os índices de `purchase_request_id` e UNIQUE de `chave_recebimento` apareciam no painel Xano. Essa confirmação é visual e informada pelo usuário; não há export remoto posterior anexado para comparação nesta change. A existência visual do índice não comprova que ele aceite múltiplos valores NULL.

O usuário relatou dois resultados de recebimento real para a solicitação #12 do produto Caderno, com quantidade solicitada de 30 CX: primeiro, recebimento vinculado parcial de 2 CX, com status parcial e 28 CX restantes; depois, confirmação de que o teste de conclusão também funcionou. A data e os detalhes da segunda quantidade recebida não foram registrados. Esses relatos demonstram somente os cenários descritos pelo usuário; não equivalem à matriz de testes com registros fictícios, não comprovam casos de falha/rollback, idempotência sob concorrência, isolamento de autorização ou comportamento de múltiplos NULL e não devem ser generalizados para esses casos.

## Pendências e limite de tentativas

### Tarefa 4 — metadados e índice

1. **Consulta automatizada anterior:** a Xano CLI falhou com `uv_os_get_passwd returned ENOMEM`. A leitura não foi repetida nesta etapa para respeitar a limitação já observada.
2. **Inspeção manual relatada:** o usuário confirmou que examinou as duas tabelas e viu os campos/índices esperados. Sem capturas ou export, não foi possível comparar todas as propriedades. A inspeção visual do índice UNIQUE não demonstra que o banco aceite vários `NULL`.

Após essas duas tentativas documentadas, permanecem sem comprovação independente: export atual completo, nulabilidade efetiva, comportamento com múltiplos `NULL`, constraints efetivas e rollback. Não fazer escrita live para testar esses itens. A tarefa 4 continua aberta; uma nova tentativa requer evidência ou mecanismo seguro novo, não repetição do mesmo caminho.

### Tarefa 10 — runtime com dados fictícios

1. **Validação local:** os testes e simulações documentados nesta change cobrem contratos e sequências no código local, mas não executam Xano.
2. **Recebimentos relatados:** o usuário informou os resultados parcial e total para o pedido real #12; esses casos não usaram registros fictícios e não cobrem os cenários negativos e de autorização exigidos.

Não há evidência registrada de datasource isolado ou de execução completa com registros fictícios e autorização específica. Como os relatos existentes não satisfazem os critérios e uma nova escrita live não está autorizada neste diagnóstico, a tarefa 10 permanece aberta. Não repetir teste real para preencher essa lacuna.

## Situação do arquivamento OpenSpec

Na configuração do projeto (`openspec/config.yaml`), a orientação de arquivamento exige confirmar que as tarefas da change foram concluídas. O CLI instalado permite iniciar `openspec archive recebimento-compras-estoque` com tarefas abertas, mas avisa e pede confirmação; em modo JSON, bloqueia sem `--yes`. O uso de `--yes` ignora o bloqueio de tarefas e não é uma conclusão válida das pendências. O validador de mudanças arquivadas (`openspec validate --archived`) sinaliza tarefas não concluídas como erro. Portanto, embora o CLI tecnicamente permita prosseguir após confirmação/bypass, arquivar agora contrariaria a orientação do projeto e deixaria a change arquivada inválida no strict. Recomendação: manter ativa com as tarefas 4 e 10 abertas, sem contornar o controle.

### Estado atual da flag

O código local atual usa `NEXSTOCK_PURCHASE_RECEIPTS_ENABLED` com padrão `true`; definir explicitamente `false` no ambiente do processo desabilita a funcionalidade. As instruções anteriores para manter `false` por padrão refletem uma decisão histórica de liberação. Como a conferência independente do contrato remoto atual e do comportamento de múltiplos NULL permanece pendente, ambientes sem essa evidência devem usar o override explícito `false` até a validação adequada. Não foi alterado `.env` nesta change.
