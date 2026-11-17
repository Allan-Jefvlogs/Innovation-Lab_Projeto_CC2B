# Tarefas

- [x] Inspecionar entrada, movimento, pedido, histórico, unidade editável, escritores e Reposição sem consultar ou alterar dados remotos.
- [x] Documentar ausência de vínculo e propor migração aditiva, contrato compatível e testes antes de implementar.
- [x] Aprovar campos de vínculo, chave UNIQUE nullable e snapshots de unidade, tratamento de legados e rejeição de excesso.
- [ ] Conferir schemas e contratos publicados, preservar backup e confirmar compatibilidade do novo índice no Xano Free.
- [x] Implementar localmente schema e entrada idempotente vinculada com transação de saldo/movimento/pedido/histórico, após aprovação.
- [x] Adaptar seleção explícita na Entrada e cliente; manter perfil Compras sem stock.entry e preservar isolamento.
- [x] Criar testes locais de parcial, total, sucessivas, avulsa, produto/unidade incompatível, legado, excesso, repetição e payload divergente; distinguir testes estruturais e mocks de execução real no Xano.
- [x] Validar localmente sintaxe XanoScript, contratos, testes, compile e OpenSpec strict, sem declarar execução no Xano.
- [x] Revisar previews seletivos antes de qualquer publicação autorizada, conforme o resumo informado pelo usuário e registrado em `publicacao-controlada.md`.
- [ ] Obter autorização separada para migração/publicação e completar testes funcionais com registros fictícios; não executar writes live nesta etapa.

Os exemplos de 15 KG são dados exclusivamente de testes locais, não registros remotos. A estrutura foi aprovada e implementada localmente. A publicação foi relatada pelo usuário; a verificação independente atual do contrato remoto continua pendente. No código atual, `NEXSTOCK_PURCHASE_RECEIPTS_ENABLED` tem padrão `true`, e o override explícito `false` desabilita a funcionalidade. O padrão `false` documentado anteriormente era uma decisão histórica, não o estado atual do código.

Histórico da preparação anterior à aprovação: 43 testes direcionados existentes/visuais, compile e strict aprovados. Naquela etapa os scripts de entrada/status foram apenas lidos e validados sintaticamente. Não houve teste de recebimento implementado naquela preparação; os resultados posteriores estão abaixo.

## Implementação local aprovada — evidências posteriores

101 testes direcionados: 19 novos de recebimento, 32 de Compras, 11 de Reposição/escopo, 12 de sessão, 3 de Auditoria e 24 de autorização de rotas. Os novos testes cobrem pré-validação decimal, cliente, State, estrutura XS e simulações sequenciais de parcial/total/duplicidade/falha de histórico, incluindo bloqueio de reenvio para contrato desconhecido. SequentialXanoFake é um double de contrato: não executa XanoScript e não comprova UNIQUE nem rollback do Xano. Nenhum arquivo da Auditoria foi editado. Compile, strict das duas changes e seis scripts aprovados pela biblioteca do Xano Developer MCP 2.2.6. Diff check dos arquivos desta etapa é verificado separadamente do worktree anterior; o global acusa whitespace preexistente em users_by_id_inactivate_patch.xs:35, não alterado aqui.

Schemas aditivos e POST/GETs locais preparados. O POST de compras recebeu somente o snapshot de unidade no db.add, sem alterar o fluxo de e-mail. Toda escrita do recebimento fica na transação; não há catch interno. O State preserva chave/payload e exige recuperação explícita na mesma sessão para resultado ambíguo; não faz retry automático. Após perda de State, exigir reconciliação antes de nova entrada equivalente.

Permanecem pendentes: conferir o contrato remoto publicado atual, comprovar o comportamento do índice UNIQUE nullable com múltiplos NULL e completar os testes funcionais requeridos com registros fictícios e autorização separada. O resumo dos seis previews, a confirmação visual das tabelas/índices e os relatos de recebimento real do pedido #12 estão em `publicacao-controlada.md`, com origem e limites de evidência. Sem backfill de unidades antigas, nova migração, provisão de perfil, envio de e-mail ou escrita remota nesta reconciliação documental.

## Registro das tarefas remotas pendentes

O limite adotado para cada pendência é de no máximo duas tentativas justificadas. As tentativas abaixo já documentadas não autorizam novas escritas ou consultas live; se a evidência continuar indisponível, a limitação fica registrada e não se declara a tarefa concluída.

### Tarefa 4 — contrato remoto e índice nullable

- **Implementado localmente:** schemas aditivos, campos de vínculo/unidade/chave e POST `/entries` com validações e transação; detalhes estão neste design e nos XanoScripts locais.
- **Verificado localmente:** estrutura dos arquivos e testes locais de contrato/simulação. Esses testes não executam Xano nem comprovam migração, rollback ou semântica do índice no banco.
- **Relato manual disponível:** o usuário informou que inspecionou as definições de `purchase_request` e `inventory_movement` no workspace 152211, branch `v1`, datasource `live`, e que os campos/índices de recebimento estavam visíveis. Os seis previews e a confirmação visual estão discriminados em `publicacao-controlada.md`; não foram fornecidas capturas nem export posterior nesta etapa.
- **Tentativas e resultado:** (1) uma leitura automatizada anterior pela Xano CLI falhou com `uv_os_get_passwd returned ENOMEM`; não foi repetida. (2) a verificação manual relatada confirmou visualmente as definições/índices, mas não demonstrou o contrato completo exportado nem o comportamento de múltiplos `NULL`.
- **Não comprovado / risco:** estado remoto atual e correspondência semântica integral, nulabilidade efetiva de `chave_recebimento`, aceitação de múltiplos `NULL`, constraints efetivas e rollback. Não testar múltiplos `NULL` por inserção no datasource compartilhado.
- **Motivo e acompanhamento:** não há nesta etapa ferramenta autenticada de leitura independente nem artefato visual/exportado para comparar; comprovar semântica de armazenamento exigiria documentação confiável ou ambiente isolado adequado. A tarefa permanece aberta; não repetir tentativas sem nova evidência/meio seguro.

### Tarefa 10 — testes funcionais com registros fictícios

- **Implementado/verificado localmente:** suíte de testes de recebimento e simulações sequenciais descritas acima, sem escrita remota; o double local não comprova runtime, autorização efetiva ou rollback do Xano.
- **Relato manual disponível:** o usuário informou recebimento parcial de 2 CX no pedido real #12 (solicitadas 30 CX, 28 CX restantes, status parcial) e, depois, que o teste de conclusão desse pedido também funcionou. Não foram informadas a data nem os detalhes da conclusão.
- **Tentativas e resultado:** (1) testes locais automatizados/simulados passaram conforme registro histórico, mas não usam Xano real. (2) os dois cenários do pedido #12 foram relatados como reais e bem-sucedidos; por usarem um pedido real, não atendem ao requisito de registros fictícios nem cobrem a matriz negativa.
- **Não comprovado / risco:** autorização separada associada a uma execução controlada com dados fictícios; sequência completa de parcial/total, avulsa, idempotência, excesso, incompatibilidades, falta de grant e leitura final dos registros; transação/rollback em runtime. Não foi identificada evidência de um datasource isolado disponível para esses testes.
- **Motivo e acompanhamento:** os relatos disponíveis não cobrem os critérios e não é seguro ampliar testes no datasource live sem ambiente e autorização próprios. A tarefa permanece aberta; não repetir testes live para preencher a lacuna.
