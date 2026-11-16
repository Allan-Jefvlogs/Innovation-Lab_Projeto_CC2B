# Tarefas

- [x] Inspecionar entrada, movimento, pedido, histórico, unidade editável, escritores e Reposição sem consultar ou alterar dados remotos.
- [x] Documentar ausência de vínculo e propor migração aditiva, contrato compatível e testes antes de implementar.
- [x] Aprovar campos de vínculo, chave UNIQUE nullable e snapshots de unidade, tratamento de legados e rejeição de excesso.
- [ ] Conferir schemas e contratos publicados, preservar backup e confirmar compatibilidade do novo índice no Xano Free.
- [x] Implementar localmente schema e entrada idempotente vinculada com transação de saldo/movimento/pedido/histórico, após aprovação.
- [x] Adaptar seleção explícita na Entrada e cliente; manter perfil Compras sem stock.entry e preservar isolamento.
- [x] Criar testes locais de parcial, total, sucessivas, avulsa, produto/unidade incompatível, legado, excesso, repetição e payload divergente; distinguir testes estruturais e mocks de execução real no Xano.
- [x] Validar localmente sintaxe XanoScript, contratos, testes, compile e OpenSpec strict, sem declarar execução no Xano.
- [ ] Revisar previews seletivos antes de qualquer publicação autorizada.
- [ ] Obter autorização separada para migração/publicação e testes funcionais com registros fictícios; não executar writes live nesta etapa.

Os exemplos de 15 KG são dados exclusivamente de testes locais, não registros remotos. A estrutura foi aprovada e implementada localmente. Migração e publicação continuam pendentes. A flag NEXSTOCK_PURCHASE_RECEIPTS_ENABLED permanece false por padrão.

Histórico da preparação anterior à aprovação: 43 testes direcionados existentes/visuais, compile e strict aprovados. Naquela etapa os scripts de entrada/status foram apenas lidos e validados sintaticamente. Não houve teste de recebimento implementado naquela preparação; os resultados posteriores estão abaixo.

## Implementação local aprovada — evidências posteriores

101 testes direcionados: 19 novos de recebimento, 32 de Compras, 11 de Reposição/escopo, 12 de sessão, 3 de Auditoria e 24 de autorização de rotas. Os novos testes cobrem pré-validação decimal, cliente, State, estrutura XS e simulações sequenciais de parcial/total/duplicidade/falha de histórico, incluindo bloqueio de reenvio para contrato desconhecido. SequentialXanoFake é um double de contrato: não executa XanoScript e não comprova UNIQUE nem rollback do Xano. Nenhum arquivo da Auditoria foi editado. Compile, strict das duas changes e seis scripts aprovados pela biblioteca do Xano Developer MCP 2.2.6. Diff check dos arquivos desta etapa é verificado separadamente do worktree anterior; o global acusa whitespace preexistente em users_by_id_inactivate_patch.xs:35, não alterado aqui.

Schemas aditivos e POST/GETs locais preparados. O POST de compras recebeu somente o snapshot de unidade no db.add, sem alterar o fluxo de e-mail. Toda escrita do recebimento fica na transação; não há catch interno. O State preserva chave/payload e exige recuperação explícita na mesma sessão para resultado ambíguo; não faz retry automático. Após perda de State, exigir reconciliação antes de nova entrada equivalente.

Permanecem pendentes: comparação remota atual, aplicação dos campos e índice, múltiplos NULL, previews, HTTP reais, testes funcionais e habilitação da flag. Sem backfill de unidades antigas, publicação, migração, provisão de perfil, envio de e-mail ou escrita real nesta execução.
