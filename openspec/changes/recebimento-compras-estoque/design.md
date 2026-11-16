# Recebimento vinculado — implementação local aprovada

O desenho abaixo foi aprovado pelo usuário e implementado somente em arquivos locais. Nenhuma migração, publicação ou escrita remota foi realizada.

## Evidências atuais

- EntryState.register_entry, em pages/movimentacoes.py, chama XanoAuthClient.create_stock_entry, que envia POST /entries. Não existe função separada de registro de entrada: entries_post.xs contém a operação.
- O endpoint exige stock.entry via authorize_permission, produto ativo, quantidade positiva, motivo, fornecedor ativo quando informado e saldo existente. db.transaction contém edição de inventory_stock e criação de inventory_movement, com ator auth.id.
- inventory_movement não tem purchase_request_id, unidade preservada nem chave idempotente. Produto/fornecedor/motivo/observação não comprovam origem em compra.
- purchase_request possui quantidade_recebida (inicial zero), quantidade_solicitada e active_product_id UNIQUE nullable, mas não possui unidade preservada. A unidade do Produto é editável no PATCH de produtos.
- Escritores de pedidos encontrados: POST cria com quantidade_recebida=0 e chave ativa; PATCH de status altera estados e libera a chave na rejeição; PATCH de cancelamento encerra e libera a chave; dispatcher altera email_status, não quantidade recebida. Não há escritor de recebimento_registrado. O schema de histórico e os contratos locais de notificações já reconhecem esse evento.
- Reposição exige produto ativo e saldo zero ou positivo abaixo do mínimo em ambas as abas, além de verificar solicitação ativa. A lista e o resumo de Compras reconhecem recebimento_parcial. A solicitação não deve depender da permanência do produto na Reposição.
- entries_post.xs contém throw nos catches, construção já rejeitada pelo importador para outro endpoint neste projeto. Não alterada nesta etapa. Antes de evoluir /entries, comparar com export atual e revisar tratamento compatível que não engula falhas na transação.

## Schema aditivo implementado somente nos arquivos locais

Em inventory_movement, acrescentar campos opcionais/nullable, sem backfill fictício:

1. purchase_request_id, referência a purchase_request e índice de consulta; obrigatório somente no recebimento vinculado.
2. chave_recebimento, texto com índice UNIQUE nullable; obrigatório no fluxo vinculado, para uma tentativa lógica inteira.
3. unidade_medida, snapshot da unidade no recebimento, para comparação idempotente e rastreabilidade posterior.

Em purchase_request, acrescentar unidade_medida_solicitada nullable inicialmente. Novos pedidos preservariam a unidade validada no backend na criação. Pedidos anteriores com NULL exigiriam conferência explícita e procedimento autorizado antes de receber; não inferir unidade histórica nem marcar recebimento retroativo. A associação é escolhida expressamente pelo operador autorizado, nunca inferida por produto igual.

Nenhuma tabela nova foi criada. Os campos foram acrescentados aos schemas locais; sua existência remota ainda não foi confirmada. Confirmar schema remoto, enums, tipos decimais e comportamento de múltiplos NULL do novo índice antes da migração autorizada. Não alterar índices ou dados remotos nesta etapa.

## Evolução de POST /entries

- Manter o contrato avulso quando purchase_request_id estiver ausente; nessa via não escrever em pedidos nem histórico de compras.
- Quando informado, exigir stock.entry e purchase_request.read, respeitando propriedade/read+manage ou administrador para acessar o pedido. Não conceder stock.entry ao perfil Compras; o recebimento permanece com operador de estoque autorizado. Não reutilizar status.update para permitir recebimento manual.
- Exigir chave_recebimento e quantidade decimal finita positiva. Validar pedido existente em aguardando_recebimento ou recebimento_parcial, mesmo produto, unidade preservada compatível e active_product_id coerente. Não converter unidades automaticamente.
- A decisão aprovada rejeita quantidade maior que o restante sem gravar estoque; não truncar silenciosamente. Pedido encerrado, cancelado, rejeitado ou sem unidade confirmada não pode receber.
- Em uma db.transaction nativa: consultar chave já existente; validar e reler pedido/produto/saldo; somar saldo; criar uma única movimentação vinculada; incrementar quantidade_recebida; gravar status/data e histórico com ID da movimentação, quantidade desta entrada, acumulado, unidade, status anterior/novo e ator autenticado.
- Se acumulado < solicitado: recebimento_parcial e chave ativa preservada. Se acumulado = solicitado: concluida, active_product_id=null e data_encerramento=now. A regra de atingir o solicitado é preservada; excesso é rejeitado antes de qualquer soma.
- Falhas de banco devem escapar da transação. Não capturar erro de histórico dentro dela de modo que permita commit parcial. Não fazer HTTP externo, e-mail ou Auditoria.

## Repetição e timeout

Gerar chave uma vez por tentativa lógica no cliente e mantê-la em timeout/resultado ambíguo. Sem retries automáticos. No backend, a chave UNIQUE é a proteção final contra inserção duplicada, não apenas uma consulta prévia. Repetição com mesma chave e mesmos campos de negócio/ator reutiliza a movimentação, sem alterar saldo, acumulado ou histórico. Payload diferente deve ser rejeitado.

Comparar produto, pedido, unidade preservada, quantidade, fornecedor, motivo, observação e data quando explicitamente fornecida. Não comparar um novo now com a data originalmente gerada pelo servidor. Após repetição, retornar identificação persistida da movimentação e estado confirmado atual do pedido; não fabricar o saldo anterior de uma resposta perdida a partir do saldo atual. Preservar resposta legada das entradas avulsas.

Conflito de índice ou timeout após possível commit exige leitura/reconciliação com a mesma chave, nunca criação automática de outra tentativa. Mapear erros e HTTP somente após conferência do comportamento Xano, sem prometer 409/422. O projeto não promete concorrência entre operadores; verificar funcionalmente unicidade, repetição e transação em cenário sequencial no Xano Free após autorização, sem tratar sintaxe como prova de rollback.

## Compatibilidade, arquivos e ordem

Arquivos implementados localmente: xano/table/inventory_movement.xs; xano/table/purchase_request.xs; xano/api/inventory_stock/entries_post.xs; purchase_requests_post.xs (somente snapshot de unidade, preservando e-mail/idempotência); GETs de detalhe/lista para expor unidade; Meu_projeto/services/xano_client.py; services/purchase_receipts.py; pages/movimentacoes.py; testes de entrada/recebimento. Leituras relacionadas são invalidadas após sucesso sem modificar TTL ou coordenador.

Revisar catálogo/grants existentes antes de escolher pedidos na tela de Entrada. O GET já existente de lista pode ser reutilizado com filtro de estado, sem novas chamadas por produto nem seleção silenciosa. Mostrar número, produto, unidade e restante; quantidade e vínculo devem ser confirmados pelo operador. Pedidos parciais continuam no filtro próprio de Compras mesmo fora da Reposição.

Ordem futura: aprovar schema/política de excesso/legados; conferir e preservar contratos remotos por leitura; validar localmente e preview seletivo dos schemas aditivos; publicação autorizada do schema; backend de criação/entrada compatível; frontend por último. Validar com registros fictícios e contas autorizadas, sem envio de e-mails. Não publicar ou migrar nesta etapa.

## Comportamento local e limites

A aprovação inclui vínculo, snapshots e rejeição de excesso. POST /entries usa operações nativas e não captura falhas de escrita dentro da transação. A antiga tradução com throw foi removida para deixar falhas abortarem a transação. HTTP e rollback reais precisam de validação separada.

Novos pedidos preservam unidade com um campo adicionado ao db.add do POST; o fluxo de e-mail não foi alterado. GETs expõem essa unidade opcional. Legados NULL são rejeitados para recebimento vinculado, preservando entrada avulsa. Não há backfill ou novo endpoint de confirmação de unidade histórica.

A Entrada consulta GET /purchase_requests por produto, com paginação de 20 e filtro local de estados elegíveis. Só consulta ao clicar, usa cache por sessão/escopo por 20 segundos e oferece Mais pedidos. Não há GET adicional na carga inicial, polling, seleção automática ou consultas por registro. A validação final é do POST, não do filtro visual.

NEXSTOCK_PURCHASE_RECEIPTS_ENABLED é false por padrão. Habilitar somente após schema e APIs publicados/validados; nenhum .env foi alterado. Desligada, a entrada avulsa mantém o payload anterior.

A tentativa vinculada guarda UUID, payload original e fingerprint de sessão no State. Recuperação manual usa o mesmo payload. Timeout, 429, falha desconhecida ou resposta sem confirmação preservam a tentativa e bloqueiam entrada substituta. Rejeições explícitas RECEIPT_* anteriores a qualquer escrita permitem corrigir os dados; conflito de chave não descarta a tentativa. Recuperação exige a mesma sessão e permissões. Não há retry automático.

LIMITAÇÃO: a tentativa permanece no State do servidor, sem persistência durável independente. Se o State expirar ou o servidor reiniciar após resultado ambíguo, reconciliar movimento/histórico/chave por leitura autorizada antes de registrar nova entrada equivalente. Não prometer recuperação automática após perda de State.

Se houver HTTP 200 sem confirmação do contrato vinculado, a UI bloqueia recuperação por POST e exige reconciliação por leitura. Um endpoint antigo pode ignorar parâmetros novos e ainda assim aumentar estoque; por isso a flag só pode ser ativada após conferir o backend correto e não se deve restaurar /entries antigo com tentativas pendentes.

A repetição consulta a chave antes de exigir estado elegível para nova entrada, permitindo recuperar pedido já concluído. Retorna movimento anterior, pedido atual e repeticao=true; saldos ficam null, sem reconstruir valores anteriores. Data omitida não é comparada com um novo now; se explicitamente fornecida, deve coincidir com o movimento. Colisão UNIQUE escapa da transação e exige recuperação manual com a mesma chave, sem retry interno. Não há garantia geral de concorrência.

Após sucesso, leituras de estoque, Reposição, compras, detalhe, resumo e notificações são invalidadas por sessão, além da invalidação central já existente para Dashboard/movimentos. Insuficiência continua dependendo do saldo real, não do status da compra.
