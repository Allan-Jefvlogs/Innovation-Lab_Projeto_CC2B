## 1. Contrato e modelagem

- [x] 1.1 Revisar payloads, grupos de API, estados ativos/terminais e política de propriedade/cancelamento com o projeto. Contratos e decisões locais consolidados em `design.md` e nesta spec; isso não atesta publicação ou autorização remota.
- [ ] 1.2 Confirmar no workspace a disponibilidade de índices únicos, coluna anulável e tratamento de conflito, sem publicar alterações.
- [x] 1.3 Especificar `purchase_request`, histórico auditável e relação de Entradas confirmadas. Modelo e relação local estão descritos em `design.md`/spec e refletidos nos artefatos locais; publicação e runtime permanecem pendentes.
- [ ] 1.4 Definir grants no catálogo e matriz por perfil sem concedê-los automaticamente.

## 2. Persistência e integridade

- [x] 2.1 Criar os artefatos locais de tabela e validar a sintaxe XanoScript.
- [ ] 2.2 Implementar a chave idempotente e o mecanismo candidato de unicidade do Produto ativo, condicionado ao suporte confirmado.
- [ ] 2.3 Implementar transições de estado auditadas, sem aceitar encerramento manual antes de recebimento permitido.
- [ ] 2.4 Vincular Entradas confirmadas à solicitação e manter `inventory_stock` como única fonte do saldo.

## 3. APIs e autorização

- [x] 3.1 Implementar leitura paginada de solicitações e resumo de estados abertos.
- [x] 3.2 Implementar consulta paginada de reposição com Produtos ativos insuficientes, separados entre elegíveis e já solicitados.
- [ ] 3.3 Implementar POST idempotente com revalidação de sessão, Produto, saldo, urgência e duplicidade.
- [ ] 3.4 Implementar cancelamento persistido e operações de gestão com grants distintos e auditoria.
- [ ] 3.5 Atualizar contrato de Entrada somente para vincular movimentação e atualizar recebimento, preservando validação `stock.entry`.
- [ ] 3.6 Validar resposta, erros, paginação e autorização de cada contrato com MCP e dry-run seletivo; dry-run não contará como publicação.

## 4. Verificação

- [ ] 4.1 Adicionar testes isolados de elegibilidade, estados, auditoria, grants, idempotência e falhas.
- [ ] 4.2 **Fora do escopo acadêmico / evolução futura:** comprovar em ambiente isolado repetição após timeout, duas criações simultâneas, conflito único e nenhuma duplicidade; não registrar como aprovado sem teste.
- [ ] 4.3 **Fora do escopo acadêmico / evolução futura:** comprovar Entrada vinculada parcial/integral, rollback e invariantes de saldo, movimentos e solicitação; não registrar como aprovado sem teste.
- [x] 4.4 Validar runtime no Xano e registrar versão/contrato publicado sem incluir credenciais nas evidências. Evidência manual informada pelo usuário em 2026-10-26: criação e cancelamento executados pela interface Reflex no workspace 152211 / branch `v1`; os GETs publicados e seus resultados runtime estão registrados nas seções anteriores de `design.md`. Esta tarefa não atesta idempotência, concorrência, rollback nem conferências independentes do histórico ou do saldo.
- [x] 4.5 Revisar riscos restantes e manter concorrência/rollback como limitações não comprovadas; os testes avançados não são bloqueio do aceite acadêmico decidido em 2026-10-25. Riscos e dependências restantes foram consolidados em `design.md` sem declarar validação remota.

## 5. Destinatário de e-mail — fase local

- [x] 5.1 Manter `email_destinatario` anulável e preparar o POST local para aceitar campo ausente/NULL na transição, validando e persistindo o endereço quando informado e comparando-o em todos os caminhos idempotentes.
- [x] 5.2 Preservar destinatário em cancelamento e manter GETs sem exposição desnecessária do e-mail; manter compatibilidade de leitura para registros NULL.
- [x] 5.3 Adicionar testes estruturais e simulados de validação, trim, idempotência, payload legado e estados de e-mail sem envio.
- [ ] 5.4 Publicar o POST de transição e validar no Xano payload legado, NULL, endereço persistido e idempotência antes de ativar o campo no Reflex; tornar obrigatório somente depois que o formulário novo estiver funcionando.
- [ ] 5.5 Implementar entrega real somente após definir provedor/credenciais; avaliar outbox separado para envio original e aviso de cancelamento, sem reutilizar `email_status` para ambos.

## 6. Entrega transacional por e-mail — preparacao local

- [x] 6.1 Criar schema local da outbox com evento, solicitacao, destinatario, snapshot, status, chave unica e datas; validar XanoScript MCP. Nao publicado.
- [x] 6.2 Enfileirar entrega original na transacao do POST com historico, somente se houver destinatario; replay idempotente nao duplica entrega e nenhum HTTP e chamado pelo endpoint.
- [x] 6.3 Preparar intencao de cancelamento na transacao do PATCH somente com entrega original confirmada ou aguardando reconciliacao; manter pedidos antigos sem backfill.
- [x] 6.4 Preparar templates em portugues, classificador de resposta e dispatcher interno Resend usando secrets do Xano; dispatcher nao foi invocado.
- [x] 6.5 Executar validacao MCP e testes locais estaticos/simulados, Reflex compile, OpenSpec strict e diff check; nao e teste runtime de Xano/Resend.
- [ ] 6.6 Publicar seletivamente e validar schema/indices/transactions; configurar o remetente de teste Resend e destinatario institucional allowlisted; executar envio controlado somente apos aprovacao explicita. Dominio proprio nao e pre-requisito assumido para este primeiro teste, mas a aceitacao do destinatario pelo remetente de teste ainda precisa ser confirmada.
- [x] 6.7 Evitar que o PATCH suponha que uma entrega `pendente` ainda nao foi lida pelo dispatcher; manter o aviso `aguardando_confirmacao_original` para entregas `pendente`, `processando` ou `indeterminado`, sem reprocessamento automatico ou decisao sobre resultado ambiguo.
- [x] 6.8 Congelar remetente e `reply_to` opcional no snapshot, adicionar guarda local fail-closed para remetente de teste e destinatario allowlisted, e verificar contrato Resend sem invocar dispatcher ou enviar mensagens.
- [ ] 6.9 Configurar `RESEND_ALLOWED_TEST_RECIPIENT` no Xano, conferir sem expor valores que o remetente de teste e permitido para esse destinatario institucional e validar runtime controlado apos aprovacao explicita.

## 7. Selecao local entre Brevo e Resend

- [x] 7.1 Resolver `NEXSTOCK_EMAIL_PROVIDER` de forma estrita (`brevo`/`resend`) sem fallback; validar configuracao sem bloquear a operacao comercial e registrar a notificacao nao enviada, sem retornar segredos.
- [x] 7.2 Gravar o provedor por nova intencao, preservar snapshots e registros existentes, manter replay idempotente sem nova outbox e nao reencaminhar itens ao trocar a configuracao ativa.
- [x] 7.3 Implementar adapters Brevo/Resend no dispatcher interno; mapear `messageId`/`id`, preservar allowlist somente no Resend e manter timeout/duplicidade ambigua sem retry automatico.
- [x] 7.4 Atualizar testes estruturais/simulados e OpenSpec para selecao, falhas de configuracao nao bloqueantes, provedor herdado no cancelamento, snapshot, segredos e limites; validar sintaxe local com MCP, suite Python, strict e diff check. Sem publicacao ou chamadas a provedores.
- [ ] 7.5 Confirmar manualmente variaveis e remetente no Xano/Brevo, egress IP e politica de allowlist, publicar seletivamente e validar runtime com uma entrega controlada apos aprovacao. Nao comprovado localmente.
- [ ] 7.6 Ativar execucao automatica somente apos definir mecanismo compativel com o plano, monitoramento e reconciliacao; nenhuma agenda ou trigger foi criada.
