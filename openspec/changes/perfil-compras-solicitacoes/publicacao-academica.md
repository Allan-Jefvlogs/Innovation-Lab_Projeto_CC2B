# Publicação controlada para demonstração acadêmica

## Contrato vigente

PATCH /purchase_requests/by_id/{request_id}/status, no grupo Inventory Stock, autenticado.

Entrada preservada: request_id na rota; status_esperado, novo_status e justificativa opcional no corpo (obrigatória para rejeitada). A identidade do ator vem de auth.id. Exige purchase_request.status.update pelo autorizador central, incluindo seu bypass administrativo existente.

Fluxo local: validar entrada e transição; em db.transaction, ler o pedido, exigir existência e status esperado, executar db.edit e inserir purchase_request_history; retornar os campos públicos da linha editada após o histórico. Não há SQL direto, alteração de estoque, movimentação, Auditoria geral, outbox ou envio de e-mail nesse PATCH. Não houve mudança de schema ou do PATCH de cancelamento.

Transições: aberta → em_analise; em_analise → aprovada ou rejeitada; aprovada → em_compra; em_compra → aguardando_recebimento. Rejeição exige justificativa, limpa active_product_id e registra encerramento. Cancelamento mantém sua rota, autorização, justificativa e confirmação existentes. recebimento_parcial/concluida não são escolhas manuais.

## Limites aceitos

O uso pressupõe um operador alterando compras por vez. status_esperado detecta divergência na releitura, mas não impede mudança simultânea entre leitura e edição. Não há garantia de concorrência, versão, reivindicação, Lock ou escalabilidade avançada.

A transação nativa mantém pedido/histórico na mesma estrutura e falhas de banco não são capturadas internamente. Isso não comprova rollback em runtime. Validação funcional sequencial no Xano Free é obrigatória; teste de corrida e rollback induzido não são condições da entrega acadêmica. Não declarar que tais testes passaram.

## Validação local desta revisão

- Sintaxe do PATCH aceita pelo Xano Developer MCP, sem warnings.
- 98 testes direcionados aprovados: 18 de Compras (incluindo contrato nativo, ordem de validação/gravação e rejeição), 56 de Reposição e 24 de autorização de rotas.
- Reflex compile --dry e OpenSpec strict aprovados.
- Testes usam mocks e inspeção estrutural; nenhum PATCH, provisionamento ou teste funcional foi executado no workspace. Nenhum preview foi executado nesta etapa.

## Dependências e ordem segura

1. Conferir por leitura workspace 152211, branch v1 e datasource live; comparar os objetos locais com os publicados e preservar cópia dos contratos para recuperação seletiva. Não incluir alterações locais da Auditoria ou e-mail.
2. Conferir tabelas existentes inventory_profile, inventory_permission, inventory_profile_permission, purchase_request e purchase_request_history, seus campos/enums e os grants atuais. Não publicar schemas nem criar tabelas.
3. Revisar preview e publicar seletivamente GET /permissions e o helper Inventory/purchase_request_notification_all_access, se ele ainda não existir. O autorizador central já existente não deve ser sobrescrito sem diferença revisada.
4. Revisar/publicar um por vez os GETs de lista, detalhe, resumo e Reposição com escopo próprio/global. Validar leitura e não exposição de pedidos alheios sem manage.
5. Revisar/publicar somente o PATCH de status nativo e testar com pedidos fictícios autorizados.
6. Publicar a definição da função interna de provisionamento, sem executá-la automaticamente. A execução para criar perfil/código/grants depende de autorização separada. Os grants exatos continuam read, manage e status.update; não há grants administrativos.
7. Antes da demonstração, obter autorização específica para usar uma conta de demonstração com esse perfil, sem atribuir perfil a usuários nesta etapa. Validar login e rotas /compras e /compras/[request_id].

Não publicar POST, cancelamento já existente, arquivos de e-mail, dispatcher, schema ou objetos da Auditoria neste lote. Notificações continuam lendo histórico persistido; sua ativação depende do contrato correspondente de dashboard-funcional, sem criar eventos fictícios ou disparar e-mails.

## Dry-runs preparados, não executados

Executar do diretório raiz do projeto, um comando por vez. Conferir que o preview mostra somente o objeto escolhido; parar em erro ou alteração inesperada.

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_catalog/permissions_get.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "function/inventory/purchase_request_notification_all_access.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_get.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_by_id_get.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_summary_get.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/stock_replenishment_get.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/purchase_requests_by_id_status_patch.xs" --dry-run
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "function/inventory/provision_purchase_profile.xs" --dry-run
```

Não usar push geral, --sync, --delete, --records ou --force. Publicação real só após nova autorização. Se a CLI apresentar ENOMEM, parar e reportar; não ampliar o lote nem improvisar sincronização geral.

## Testes funcionais após autorização de publicação

- Confirmar por leitura que os pedidos/produtos escolhidos são fictícios e registrar ID, status e histórico inicial. Se não houver pedidos adequados, solicitar autorização específica e preparar sua criação sem disparos de e-mail; não reutilizar registros comerciais reais.
- Com uma sessão de demonstração autorizada, executar uma transição por vez no seletor: aberta → em_analise → aprovada → em_compra → aguardando_recebimento. Conferir status público e exatamente o evento correspondente em cada etapa.
- Em outro pedido fictício, rejeitar de em_analise com justificativa e confirmar status, evento rejeitada, encerramento e active_product_id nulo por leitura autorizada.
- Repetir uma requisição com status_esperado antigo, testar salto inválido, ausência de justificativa e sessão sem status.update; conferir erro sem novo histórico nem alteração. Confirmar o HTTP real em vez de presumir 409/422.
- Validar o cancelamento existente em pedido fictício elegível com justificativa/confirmação somente após conferir seus efeitos de e-mail no fluxo de demonstração. Não executar dispatcher nem envio; preservar e conferir estoque inalterado.
- Validar isolamento próprio/global, acesso direto por ID, ausência de acesso às demais rotas pelo perfil Compras e preservação dos outros perfis.
- Confirmar que a interface mostra apenas o status confirmado, mantém feedback de erro, não repete PATCH automaticamente e atualiza leituras/cache após sucesso. Notificações, quando publicadas/ativas, devem corresponder ao mesmo histórico, sem duplicação.

## Interrupção e recuperação

Se preview, importação ou teste funcional falhar, interromper o lote e não atribuir o novo perfil. Comparar o objeto afetado com a cópia preservada e revisar sua restauração seletiva, sem sobrescrever outros trabalhos. Se houver resultado ambíguo de PATCH, reler pedido e histórico antes de qualquer nova tentativa. Não repetir escrita automaticamente nem apagar registros para esconder uma falha.

## Limitações registradas — ciclo de 2026-11-16

Não serão realizadas novas tentativas remotas nesta etapa. A change permanece ativa, e estas pendências serão consideradas na consolidação posterior solicitada para o relatório acadêmico. Este documento não é o relatório final.

### Tarefa 2.3 — teste funcional remoto do PATCH de status

- **Evidência disponível:** implementação local do PATCH nativo com `db.transaction`, leitura e validação do status esperado, edição do pedido e gravação do histórico; validação sintática pelo Xano Developer MCP e testes locais com mocks/inspeção estrutural, registrados acima. O usuário informou que o teste funcional do PATCH no Xano Free não foi executado.
- **Não comprovado:** execução no workspace publicado, confirmação de status e histórico em runtime e liberação de `active_product_id` após rejeição.
- **Motivo e dependências:** requer publicação seletiva autorizada, solicitações fictícias apropriadas e sessão/conta de teste autorizada. Nenhuma escrita remota será repetida neste ciclo.
- **Risco residual:** o comportamento em runtime permanece desconhecido; não há falha funcional confirmada. Testes locais e validação de sintaxe não substituem o teste remoto.

### Tarefa 4.4 — dry-runs, impacto e autorização

- **Evidência disponível:** plano de publicação com oito comandos seletivos em modo dry-run, identificando objetos e ordem de dependências; revisão local dos consumidores e restrições de publicação descritas neste documento. O histórico registra que os previews não foram executados nesta etapa. Há registro anterior de falha da CLI com `uv_os_get_passwd returned ENOMEM`; não se repetiu esse comando.
- **Não comprovado:** resultados dos oito dry-runs, impacto confirmado pelo preview do Xano e autorização específica para publicação real.
- **Motivo e dependências:** a CLI falhou ao resolver o usuário do sistema operacional e ainda é necessária autorização separada após revisão dos previews.
- **Risco residual:** publicar sem inspecionar cada preview pode afetar objetos não pretendidos; não há publicação nem impacto remoto confirmado.

### Tarefa 4.5 — transições, histórico, índice ativo e estado desatualizado

- **Evidência disponível:** contratos locais, cenários e testes automatizados com mocks/estrutura; PATCH local valida o estado lido dentro da transação e registra histórico. O usuário relatou resultados funcionais anteriores em registros de compra, mas eles não constituem evidência independente nem comprovam todos os critérios desta tarefa.
- **Não comprovado:** sequência completa no Xano publicado, histórico correspondente, liberação do índice ativo na rejeição e rejeição de estado já desatualizado.
- **Motivo e dependências:** depende da publicação autorizada do PATCH e de pedidos fictícios com estado inicial conhecido, além de consulta autorizada de leitura para confirmar os efeitos.
- **Risco residual:** transições e efeitos no servidor não foram confirmados; isso representa ausência de comprovação, não falha funcional conhecida. Concorrência e rollback induzido permanecem fora dos critérios acadêmicos vigentes.

### Tarefa 4.6 — associação autorizada da conta de teste

- **Evidência disponível:** a função local de provisionamento declara o perfil e os grants esperados e não atribui perfil automaticamente. Houve relato anterior do usuário de que uma conta Compras autenticou e acessou a área `/compras`.
- **Não comprovado:** que a associação daquela conta ocorreu após a validação exigida e mediante a autorização específica prevista nesta tarefa; o relato de acesso não comprova essa sequência nem validação do backend publicado.
- **Motivo e dependências:** associação requer aprovação específica do usuário e depende das validações de endpoints/interface previstas anteriormente. Nenhuma associação foi realizada nesta revisão.
- **Risco residual:** sem confirmação de escopo e autorização, não se deve inferir que a conta de demonstração está pronta para uso; não há evidência de acesso indevido.

### Tarefa 4.8 — publicação do helper de escopo global

- **Evidência disponível:** `Inventory/purchase_request_notification_all_access` existe como arquivo local e integra a ordem de publicação documentada.
- **Não comprovado:** existência/publicação do helper no workspace 152211, branch `v1`, nem sua disponibilidade para os GETs publicados.
- **Motivo e dependências:** exige inspeção remota somente de leitura e, se ausente, autorização para publicação seletiva; a inspeção remota não será repetida neste ciclo.
- **Risco residual:** os endpoints remotos podem não resolver o helper ou podem divergir do escopo local; nenhum defeito remoto foi confirmado.

### Tarefa 4.9 — grants, isolamento e paginação em `/stock/replenishment`

- **Evidência disponível:** implementação local aplica escopo próprio/global e projeção restrita; testes locais com mocks cobrem casos de isolamento e compatibilidade, conforme registrados nas evidências desta change.
- **Não comprovado:** respostas do endpoint publicado para leitor proprietário, leitor de terceiro, gestor e administrador, incluindo paginação e mudança de acesso.
- **Motivo e dependências:** depende da publicação autorizada do helper e do endpoint, além de contas/sessões de teste com grants conhecidos e consultas de leitura no ambiente publicado.
- **Risco residual:** isolamento, grants e paginação remotos não foram confirmados; não há evidência de exposição ou falha funcional em runtime. A proteção local não prova a configuração publicada.

## Estado do ciclo

As tarefas 2.3, 4.4, 4.5, 4.6, 4.8 e 4.9 permanecem pendentes. As evidências locais e os relatos do usuário foram preservados, mas não foram promovidos a validação remota independente. A change continua ativa; não houve consulta ou escrita no Xano, publicação, teste funcional remoto ou criação do relatório acadêmico final neste ciclo.
