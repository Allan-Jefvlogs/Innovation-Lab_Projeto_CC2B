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
