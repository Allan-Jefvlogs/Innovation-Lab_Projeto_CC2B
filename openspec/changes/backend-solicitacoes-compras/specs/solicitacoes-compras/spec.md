# Solicitações de Compras

## ADDED Requirements

### Requirement: Validar a elegibilidade de uma Solicitação de Compra no backend

O backend MUST permitir solicitação somente para Produto ativo com registro de estoque e saldo igual a zero ou abaixo do mínimo. A validação MUST usar os dados atuais do Xano. Ausência da linha de saldo MUST ser tratada como inconsistência, nunca convertida em zero. A interface e o cache MUST NOT ser autoridade para aceitar uma escrita.

#### Scenario: Produto elegível

- **WHEN** um usuário autorizado consulta reposição e o Produto está ativo, possui saldo e está zerado ou abaixo do mínimo
- **THEN** o backend o retorna na seção correspondente à existência ou não de solicitação ativa
- **AND** somente Produto sem solicitação ativa fica elegível para nova solicitação

#### Scenario: Produto inativo, normal ou sem saldo persistido

- **WHEN** uma consulta ou criação encontra Produto inativo, saldo normal ou saldo ausente
- **THEN** o backend não o aceita como Produto elegível
- **AND** saldo ausente produz erro explícito de integridade, sem criar solicitação

### Requirement: Impedir solicitações ativas duplicadas

O backend MUST impedir mais de uma Solicitação ativa para o mesmo Produto e MUST tratar repetições da mesma tentativa idempotentemente. A proteção concorrente MUST usar mecanismo aceito pelo Xano e validado na instância; consulta anterior à escrita e `db.transaction` isoladamente não satisfazem este requisito.

#### Scenario: Repetição da mesma tentativa

- **WHEN** o mesmo POST é repetido com a mesma chave de idempotência após resposta ambígua
- **THEN** o backend retorna a solicitação já criada sem inserir outra linha nem duplicar eventos de criação

#### Scenario: Outra solicitação ativa existe

- **WHEN** um POST chega para Produto com solicitação ativa
- **THEN** o backend retorna conflito controlado e não cria nova solicitação

#### Scenario: Duas criações simultâneas para o mesmo Produto

- **WHEN** duas requisições com chaves distintas tentam criar simultaneamente para o mesmo Produto
- **THEN** no máximo uma é criada e a outra recebe conflito controlado
- **AND** esse cenário permanece pendente até ser comprovado em ambiente isolado na instância Xano

### Requirement: Persistir estados auditáveis e manter estoque como fonte do saldo

O backend MUST registrar solicitante, quantidade, urgência, estado e histórico de alterações. A atividade da solicitação MUST depender do estado de negócio, nunca do estado de e-mail. Nenhum endpoint de Solicitações MUST alterar saldo diretamente; somente Entrada confirmada no Xano altera estoque.

#### Scenario: Estados ativos e encerrados

- **WHEN** a solicitação está `aberta`, `em_analise`, `aprovada`, `em_compra`, `aguardando_recebimento` ou `recebimento_parcial`
- **THEN** ela bloqueia nova solicitação para o Produto e entra na contagem de solicitações abertas
- **WHEN** está `cancelada` ou `rejeitada`
- **THEN** ela não bloqueia uma nova solicitação se o Produto ainda estiver insuficiente

#### Scenario: Recebimento parcial ou compra comercialmente concluída

- **WHEN** a compra está comercialmente concluída sem Entrada confirmada integral
- **THEN** a solicitação continua ativa e não altera o saldo
- **WHEN** uma Entrada Xano vinculada é confirmada parcialmente
- **THEN** somente essa Entrada altera saldo e o pedido permanece em `recebimento_parcial`

#### Scenario: Recebimento integral confirmado

- **WHEN** Entradas Xano vinculadas confirmam a quantidade integral solicitada e uma transição autorizada encerra o pedido
- **THEN** o backend grava auditoria e data de encerramento
- **AND** recalcula elegibilidade pelo saldo atual, permitindo nova solicitação somente se ainda houver insuficiência

### Requirement: Aplicar autorização dinâmica e registrar a identidade real

Os endpoints MUST validar no backend grants separados de leitura, criação, cancelamento e gestão. O solicitante e os atores de histórico MUST ser derivados da sessão autenticada. Nenhuma permissão MUST ser concedida automaticamente.

#### Scenario: Usuário sem grant de criação

- **WHEN** usuário autenticado sem `purchase_request.create` tenta criar
- **THEN** o backend rejeita a operação e não cria pedido nem histórico de criação

#### Scenario: Usuário sem grant de gestão

- **WHEN** usuário sem `purchase_request.manage` tenta aprovar, rejeitar ou mudar estado gerencial
- **THEN** o backend rejeita e preserva o estado e histórico

#### Scenario: Consultar a página completa de reposição

- **WHEN** um usuário consulta `GET /stock/replenishment`
- **THEN** o backend exige simultaneamente `stock.read` e `purchase_request.read`
- **AND** usuários sem qualquer um desses grants recebem acesso negado à página completa
- **AND** o Dashboard e os alertas gerais de estoque continuam sujeitos somente aos grants de seus próprios contratos

### Requirement: Limitar os campos expostos nas consultas

Os endpoints de leitura MUST retornar somente campos necessários à interface e à auditoria aprovada. Respostas de listagem e detalhe MUST NOT expor `chave_idempotencia`, `active_product_id` ou outros campos internos de controle. Histórico deve preservar ator, evento, justificativa, dados de auditoria e data do evento.

#### Scenario: Ler lista, detalhe e histórico

- **WHEN** usuário autorizado consulta solicitações e seus eventos
- **THEN** o backend preserva campos de negócio, Produto, solicitante, status, quantidades, urgência e datas
- **AND** omite a chave idempotente e a chave interna de atividade do Produto

### Requirement: Registrar criação sem alegar envio de e-mail

Na primeira fase, o backend MUST criar a solicitação com `email_status=pendente` sem executar envio. Falhas futuras de e-mail MUST manter o registro ativo. O status de e-mail MUST NOT encerrar nem liberar o Produto.

#### Scenario: Solicitação criada na primeira fase

- **WHEN** o Xano confirma o POST
- **THEN** retorna o pedido persistido com estado de negócio ativo e e-mail pendente
- **AND** a resposta não declara que o e-mail foi enviado

### Requirement: Persistir o destinatário comercial sem quebrar pedidos históricos

O schema MUST manter `email_destinatario` anulável para preservar pedidos existentes sem endereço. Na fase de transição, o POST MUST aceitar o campo ausente ou `NULL` para preservar clientes legados. Se informado, o endereço MUST ser validado, aparado nas extremidades, limitado a 254 caracteres e persistido; ausente e `NULL` são o mesmo valor para idempotência. A mesma chave com destinatário diferente MUST ser rejeitada como payload incompatível. GETs de listagem e Reposição MUST NOT expor o destinatário sem necessidade aprovada. O campo só se tornará obrigatório depois que o formulário Reflex com destinatário estiver funcionando e a API publicada for compatível.

#### Scenario: Criar com destinatário válido

- **WHEN** a versão nova do POST recebe e-mail válido com espaços externos
- **THEN** o endereço aparado é salvo junto à solicitação
- **AND** o estado inicial de e-mail continua `pendente` e nenhum e-mail é enviado

#### Scenario: Idempotência considera o destinatário

- **WHEN** a mesma chave é repetida com o mesmo destinatário normalizado e demais campos iguais
- **THEN** a solicitação já registrada é recuperada
- **WHEN** a mesma chave é repetida com outro destinatário
- **THEN** a operação é rejeitada como payload incompatível

#### Scenario: Ler pedido histórico sem destinatário

- **WHEN** um pedido antigo tem `email_destinatario = null`
- **THEN** consultas existentes continuam funcionando sem converter o valor em texto ou falhar
- **AND** o pedido não é tratado como se uma mensagem tivesse sido enviada

#### Scenario: Preservar clientes durante a transição

- **WHEN** um cliente legado omite `email_destinatario` ou envia `NULL`
- **THEN** o pedido é criado com destinatário `NULL` e as demais regras/idempotência permanecem iguais
- **AND** depois que o formulário com destinatário estiver funcionando, uma alteração coordenada poderá tornar o campo obrigatório

### Requirement: Cancelar solicitações somente em estados permitidos e com auditoria

O endpoint local `PATCH /purchase_requests/by_id/{request_id}/cancel` MUST exigir autenticação e `purchase_request.cancel` ou `purchase_request.manage`, respeitando o bypass canônico de administrador do autorizador central. Como política conservadora proposta, um solicitante com `purchase_request.cancel` MUST poder cancelar somente a própria solicitação; outro ator MUST possuir `purchase_request.manage`. Até revisão funcional final, somente `aberta` e `em_analise` são estados canceláveis. A operação MUST exigir justificativa não vazia, revalidar o estado dentro da transação, alterar o estado para `cancelada`, limpar `active_product_id`, preencher os timestamps de encerramento/atualização e registrar evento `cancelada` com o ator autenticado e justificativa. MUST NOT alterar saldo ou movimentações.

#### Scenario: Cancelar solicitação aberta ou em análise

- **WHEN** um ator autorizado cancela uma solicitação `aberta` ou `em_analise` dentro da política de propriedade
- **THEN** a solicitação passa a `cancelada`, libera `active_product_id` e recebe datas de encerramento e atualização
- **AND** o histórico registra `cancelada`, a justificativa e `$auth.id`
- **AND** a operação não altera `inventory_stock` nem cria `inventory_movement`

O cancelamento MUST preservar `email_destinatario`. Em fase futura, aviso de cancelamento somente poderá ser enviado se o envio original tiver sido confirmado; `email_status=pendente` não significa envio. A fase atual não envia e-mails.

#### Scenario: Recusar estado não cancelável ou repetição de cancelamento

- **WHEN** o estado é `aprovada`, `em_compra`, `aguardando_recebimento`, `recebimento_parcial`, `concluida` ou `rejeitada`
- **THEN** o endpoint rejeita sem alterar a solicitação nem criar evento
- **WHEN** o estado já é `cancelada`
- **THEN** retorna erro de domínio específico sem criar outro evento

#### Scenario: Recusar justificativa vazia, solicitação ausente ou ator sem acesso

- **WHEN** a justificativa é ausente/vazia, a solicitação não existe ou o ator não possui os grants e a propriedade exigidos
- **THEN** o endpoint rejeita a operação sem modificar estado ou histórico

#### Scenario: Concorrência no cancelamento

- **WHEN** dois cancelamentos, uma mudança gerencial de estado ou um recebimento concorrem sobre a mesma solicitação
- **THEN** o resultado deve preservar uma única transição e o histórico correspondente
- **AND** esta garantia permanece pendente até existir mecanismo condicional aceito e teste isolado na instância Xano

### Requirement: Manter entregas de e-mail fora do estado do pedido

O backend MUST registrar cada entrega original ou aviso de cancelamento em `purchase_request_email_delivery`, separada do estado comercial e do `email_status`. Cada intencao MUST incluir tipo do evento, solicitacao, destinatario, status, identificador do provedor quando confirmado, timestamps de tentativa/confirmacao, codigo de erro sanitizado, chave idempotente unica e snapshot estavel do payload. Pedido, historico e intencao original MUST ser persistidos na mesma transacao quando houver destinatario. Nenhuma chamada HTTP externa MUST ocorrer dentro da transacao nem no POST/PATCH.

Somente uma resposta 2xx com ID do provedor confirma `enviado`. Rejeicao explicita e `falhou`; timeout, resposta 5xx, conflito idempotente simultaneo ou 2xx sem ID sao `indeterminado`. O status original `email_status` so reflete entrega original confirmada/rejeitada e nao controla atividade do pedido. Falha de entrega MUST NOT apagar pedido ou alterar saldo.

#### Scenario: Criacao com ou sem destinatario

- **WHEN** o pedido e novo e tem destinatario validado
- **THEN** uma intencao original e gravada atomicamente com pedido e historico
- **AND** replay idempotente nao cria outra intencao
- **WHEN** um cliente legado omite o destinatario
- **THEN** o pedido permanece compativel e nao e criada intencao nem backfill de mensagem antiga

#### Scenario: Aviso de cancelamento

- **WHEN** a solicitacao e cancelada e a entrega original esta confirmada `enviado` com ID do provedor
- **THEN** uma unica intencao de cancelamento e registrada com o destinatario salvo
- **WHEN** a entrega original esta pendente, processando ou indeterminada
- **THEN** uma unica intencao de cancelamento fica `aguardando_confirmacao_original` e nao e enviada
- **AND** o PATCH nao suprime uma entrega original apenas por observar `pendente`, pois o dispatcher pode ja ter lido esse estado
- **WHEN** nao existe registro original (pedido legado), ou a entrega falhou/suprimida
- **THEN** nenhum aviso e criado

### Requirement: Enviar e-mails somente por dispatcher backend controlado

As chaves dos provedores MUST existir somente em environment variables/segredos do Xano. Intencoes que podem ser enviadas MUST gravar em `provedor` o valor explicito `brevo` ou `resend`, sem usar o default do schema como fallback. `NEXSTOCK_EMAIL_PROVIDER` seleciona apenas novas intencoes originais. Se o seletor for ausente/invalido, o pedido de compra MUST continuar quando suas validacoes de negocio forem satisfeitas, registrar `email_status=falhou` e um codigo sanitizado no historico, e MUST NOT criar outbox sem provedor conhecido. Se o seletor for valido mas a configuracao desse provedor estiver incompleta, o pedido MUST continuar e a outbox MUST registrar o provedor selecionado com status `falhou` e codigo sanitizado; nenhuma chamada externa e feita. O dispatcher MUST rotear exclusivamente pelo provedor gravado na intencao, sem reavaliar a selecao ativa e sem alterar registros existentes. O PATCH de cancelamento MUST continuar a transicao comercial mesmo se a configuracao de notificacao estiver indisponivel. Uma notificacao de cancelamento MUST herdar o provedor da intencao original e usar o snapshot de remetente dessa intencao; MUST NOT trocar para o provedor ativo. Se o provedor original for reconhecido, mas sua configuracao estiver incompleta, o aviso de cancelamento confirmado como necessario MUST ser registrado como `falhou`, com codigo sanitizado e sem chamada externa. Se o provedor original nao puder ser usado com seguranca, o PATCH MUST registrar o estado/codigo no historico e MUST NOT criar intencao com provedor ficticio. Para original pendente/processando/indeterminado, a notificacao permanece `aguardando_confirmacao_original` com o provedor original somente quando esse provedor e reconhecido; resultado ambiguo requer reconciliacao manual. A adaptacao de payload e resposta MUST preservar snapshot e chave de idempotencia. Nenhum endpoint de compra/cancelamento MUST chamar o provedor dentro da transacao. Nao pode haver retry automatico apos timeout, rejeicao ambigua ou resposta 2xx sem identificador. Corpo bruto do provedor e credenciais MUST NOT aparecer em logs ou respostas ao Reflex. Idempotencia do provedor tem janela limitada e nao prova entrega exatamente uma vez.

Para `resend`, manter a restricao atual de remetente de teste e destinatario em `RESEND_ALLOWED_TEST_RECIPIENT` somente no ramo Resend; a configuração do destinatário MUST ser conferida antes de registrar uma intenção elegível. Para `brevo`, usar `BREVO_API_KEY`, `BREVO_FROM_EMAIL`, `BREVO_FROM_NAME` e `BREVO_REPLY_TO` configurados no backend; nao impor a allowlist fixa do Resend. O adaptador Brevo MUST chamar `POST /v3/smtp/email`, mapear a snapshot para `sender`, `to`, `subject`, `textContent`, `htmlContent` e `replyTo`, e persistir `messageId` como identificador do provedor quando confirmado.

`NEXSTOCK_EMAIL_PROVIDER` seleciona somente novas intencoes. Trocar essa variavel MUST NOT redirecionar nem regravar intencoes anteriores. Credenciais ou remetente ausentes/incompativeis MUST impedir a chamada externa. Duplicidade reportada pelo provedor sem o identificador original e resultado indeterminado que requer reconciliacao.

#### Scenario: Resposta ambigua ou provedor indisponivel

- **WHEN** ocorre timeout, 5xx, 409 concorrente ou resposta 2xx sem ID
- **THEN** a outbox fica `indeterminado` sem reenvio automatico
- **AND** uma pessoa reconcilia o estado no provedor antes de uma nova tentativa

#### Scenario: Configuracao ausente ou incompleta nao bloqueia operacao comercial

- **WHEN** um pedido valido inclui destinatario mas o provedor ativo esta ausente/invalido
- **THEN** o pedido e seu historico sao persistidos, `email_status` fica `falhou` e o historico registra um codigo sanitizado
- **AND** nenhuma outbox e criada sem um provedor reconhecido e nenhuma chamada externa ocorre
- **WHEN** um pedido valido tem provedor reconhecido mas faltam credenciais/remetente
- **THEN** pedido, historico e uma outbox com o provedor real sao persistidos atomicamente, com status `falhou` e codigo sanitizado
- **WHEN** uma solicitacao elegivel e cancelada enquanto a configuracao do provedor original esta ausente
- **THEN** o cancelamento, a liberacao de `active_product_id` e o historico comercial sao persistidos
- **AND** a notificacao e registrada como nao enviada/falha quando a outbox puder guardar o provedor original; caso contrario o historico registra o motivo e nao e inventado um provedor
- **WHEN** a configuracao desaparecer entre o registro da intencao e uma execucao manual do dispatcher
- **THEN** nenhuma chamada HTTP e feita, a outbox e marcada `falhou` com codigo sanitizado, e o estado de entrega original e atualizado quando aplicavel
- **AND** nenhuma dessas falhas altera estoque ou afirma envio confirmado

#### Scenario: Seleção atual muda antes do aviso de cancelamento

- **WHEN** uma solicitação enviada pelo Resend e cancelada depois que `NEXSTOCK_EMAIL_PROVIDER` foi alterado para Brevo, ou vice-versa
- **THEN** a notificação de cancelamento herda o provedor e o snapshot de remetente da intenção original
- **AND** credenciais ausentes para esse provedor são auditadas sem trocar silenciosamente de provedor e sem impedir o cancelamento

#### Scenario: Selecionar Brevo para uma nova intencao

- **WHEN** `NEXSTOCK_EMAIL_PROVIDER=brevo` e as variaveis necessarias do Brevo estao configuradas
- **THEN** uma intencao nova grava `provedor=brevo` e congela remetente, destinatario, assunto, texto e reply-to opcionais na snapshot
- **AND** o dispatcher envia pelo endpoint Brevo e somente uma resposta de sucesso com `messageId` confirma `enviado`

#### Scenario: Selecionar Resend para uma nova intencao

- **WHEN** `NEXSTOCK_EMAIL_PROVIDER=resend`
- **THEN** uma intencao nova grava `provedor=resend` e a restricao de remetente/destinatario de teste aplica-se somente ao Resend

#### Scenario: Selecao ausente ou invalida

- **WHEN** `NEXSTOCK_EMAIL_PROVIDER` esta ausente ou nao e `brevo` nem `resend`
- **THEN** nenhuma nova intencao escolhe provedor implicitamente e nenhuma chamada externa e feita

#### Scenario: Alteracao do provedor ativo

- **WHEN** o provedor ativo muda depois que uma intencao foi persistida
- **THEN** o dispatcher continua usando o valor `provedor` daquela linha e nao migra nem reenvia registros anteriores

#### Scenario: Timeout ou duplicidade reportada pelo Brevo

- **WHEN** a chamada Brevo expira, retorna duplicidade da chave ou nao fornece um `messageId` confirmavel
- **THEN** o estado permanece `indeterminado` e nao ha retry automatico
- **AND** uma pessoa reconcilia a situacao antes de decidir nova tentativa


### Requirement: Restricao de envio de teste por provedor e supressao ao cancelar

No ramo Resend, o dispatcher MUST continuar fail closed com `RESEND_FROM_EMAIL=onboarding@resend.dev`, `RESEND_API_KEY` presente e destinatario igual a `RESEND_ALLOWED_TEST_RECIPIENT`, configurada no Xano. No ramo Brevo, deve usar remetente configurado/autorizado no Brevo e nao pode reutilizar a allowlist fixa do Resend. `BREVO_REPLY_TO` e `RESEND_REPLY_TO` sao opcionais e congelados na snapshot. Nenhum caminho pode alterar a snapshot ou fazer retry automatico apos resultado ambiguo. Se a restricao IP estiver habilitada no Brevo, a origem Xano deve ser validada e autorizada; o projeto nao desabilita essa protecao automaticamente.

#### Scenario: Cancelar enquanto o despacho original ainda pode estar em curso

- **WHEN** o PATCH cancela uma solicitacao cuja entrega original esta `pendente`
- **THEN** a intencao original permanece sem alteracao e o aviso fica `aguardando_confirmacao_original`
- **AND** se o dispatcher observar a solicitacao cancelada antes da chamada externa, ele suprime a entrega original e o aviso aguardando
- **AND** se a chamada externa ja tiver avancado ou seu resultado for ambiguo, nenhuma mensagem subsequente e decidida sem reconciliacao manual

#### Scenario: Aguardar reconciliacao de envio original

- **WHEN** a entrega original esta `pendente`, `processando` ou `indeterminado`
- **THEN** o aviso fica bloqueado aguardando reconciliacao e so se torna elegivel apos confirmacao do original como `enviado`
- **AND** uma nova execucao nao reenvia registros `processando`, `indeterminado`, `enviado`, `falhou` ou `suprimido`

#### Scenario: Bloquear configuracao fora do escopo de teste

- **WHEN** o remetente ou destinatario nao respeita a configuracao de teste
- **THEN** o dispatcher nao faz chamada externa e nao expoe endereco ou segredo na resposta

A janela de idempotencia do provedor e limitada e a disputa concorrente entre cancelamento e uma chamada de envio ja em andamento permanece uma limitacao nao comprovada. Nenhum teste local substitui validacao controlada no Xano/Resend.
