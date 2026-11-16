# Tarefas

## Decisão vigente

Entrega acadêmica com um único operador alterando compras por vez. SQL direto foi substituído localmente por db.get/db.edit/db.add em db.transaction. Não são exigidos versão, reivindicação UNIQUE, Lock, testes simultâneos ou rollback induzido. As investigações anteriores não bloqueiam mais a entrega; autenticação, isolamento, transições, histórico e testes funcionais no Xano Free continuam obrigatórios. Plano vigente: publicacao-academica.md.

## Revisão e preparação local

- [x] 1.1 Revisar esta proposta e confirmar grants fixos do perfil Compras e mudança de escopo dos GETs existentes.
- [ ] 1.2 Conferir por leitura perfil, catálogo, grants, status e referências no Xano publicado antes de qualquer provisionamento.
- [x] 1.3 Preparar provisionamento seletivo de `compras` e `purchase_request.status.update`, sem seed geral nem atribuição automática a usuários (função interna local, não executada).
- [x] 1.4 Adaptar matriz `GET /permissions` e política da página Perfis para apresentar o perfil Compras sem liberar grants gerais, localmente.

## Backend local

- [x] 2.1 Restringir localmente GET de listagem/detalhe e resumo a pedidos próprios com `read` e a todos com `read` + `manage` ou administrador; preservar projeções, filtros e paginação.
- [x] 2.2 Criar localmente PATCH de status com grant específico, transições aprovadas e estado esperado.
- [ ] 2.3 Validar funcionalmente o PATCH nativo no Xano Free com solicitações fictícias autorizadas: status confirmado, histórico e liberação de active_product_id na rejeição. Não declarar rollback comprovado sem evidência de runtime.
- [x] 2.4 Revisar localmente estado esperado divergente, autorização e propagação de falhas de banco sem captura interna; documentar a limitação de concorrência aceita.

## Frontend local

- [x] 3.1 Adaptar localmente destino de login, restauração de sessão, guards de URL e menu exclusivo do perfil Compras.
- [x] 3.2 Criar localmente rota `/compras` e detalhe, com lista paginada, filtros e histórico da API.
- [x] 3.3 Integrar localmente seletor de status com envio único, feedback e reconciliação sem atualização otimista.
- [x] 3.4 Reutilizar localmente cancelamento com justificativa e confirmação, sem alterar seu endpoint nem o fluxo de e-mail.
- [x] 3.5 Preservar notificações baseadas no histórico e invalidação de cache apenas após escrita confirmada.

## Validação e publicação futura

- [ ] 4.1 Testar grants e rotas com Compras, administrador, leitor isolado e demais perfis; negar acesso por URL e API.
- [ ] 4.2 Testar lista/detalhe, paginação, filtros, transições, rejeição, erros e cancelamento; confirmar ausência de escrita em estoque/Auditoria.
- [x] 4.3 Validar localmente XanoScript por MCP, testes Reflex/Python, compile, OpenSpec strict e diff check; a nova revisão nativa deve registrar seus resultados ao final. Validação funcional permanece nos itens 2.3 e 4.5.
- [ ] 4.4 Preparar dry-runs seletivos, revisar impacto dos GETs nos consumidores e obter autorização separada antes de publicar.
- [ ] 4.5 Validar no Xano publicado os fluxos sequenciais, histórico, liberação do índice ativo e rejeição de estado já desatualizado; registrar que concorrência e rollback induzido não foram comprovados nem exigidos nesta entrega.
- [ ] 4.6 Associar usuário ao novo perfil somente após validação dos endpoints e da interface, com autorização específica.
- [x] 4.7 Corrigir localmente o contrato de Reposição: preservar produtos insuficientes, ocultar detalhes alheios sem escopo global, adaptar consumidor e cache e testar compatibilidade. Comprovação de autorização em runtime continua pendente.
- [ ] 4.8 Confirmar que `Inventory/purchase_request_notification_all_access` está publicado antes dos GETs modificados; validar a ordem `GET /permissions` → provisionamento do perfil → GETs/PATCH.
- [ ] 4.9 Validar a resposta publicada da Reposição com leitor proprietário, leitor de terceiro, gestor e administrador, inclusive paginação e mudança de acesso.
- [x] 4.10 Remover SQL do PATCH e preparar edição nativa com validação do status lido para o uso acadêmico de um operador por vez, sem adicionar schema.
- [x] 4.11 Diagnosticar versionamento/reivindicação UNIQUE, alternativas de schema, participação do cancelamento e propriedades que exigem prova de banco; registrar a opção nativa Lock aceita sintaticamente, sem implementar os protocolos.

## Itens dispensados por decisão do projeto

O antigo item 4.12 (escolha e prova de Lock/versão/UNIQUE) e os testes avançados de concorrência/rollback induzido saíram dos critérios da entrega acadêmica. Não foram aprovados por execução nem implementados. O diagnóstico anterior permanece como registro histórico, sem investigação adicional nesta etapa.

## Evidências locais desta implementação

### Refinamento visual e investigação de recebimentos

- Botão secundário Voltar com seta à esquerda e destino /compras implementado localmente. Controles Anterior/Próxima do histórico aparecem somente com mais de uma página, junto do indicador atual/total. Paginação da lista e seletor de status preservados.
- Fluxo de recebimento permanece sem implementação: inventory_movement não possui vínculo com compra, chave de repetição nem unidade preservada. Plano de schema/entrada/active_product_id e matriz de cenários sujeitos a aprovação em ../recebimento-compras-estoque; não associar pedido apenas por produto ou saldo. Não declarar recebimentos ou prevenção de duplicidade testados em runtime.
- Validação desta etapa: 32 testes de Compras e 11 de isolamento da Reposição aprovados; compile Reflex e strict das duas changes aprovados. Biblioteca local do Xano Developer MCP 2.2.6 aceitou entries_post.xs e purchase_requests_by_id_status_patch.xs sem erros; scripts apenas lidos, não alterados ou executados. Validação sintática não comprova importação nem comportamento de recebimento.

### Correção local da paginação do histórico no detalhe

- GET de detalhe local e backup habilitam totals: true, mas a projeção de purchase_request_history omitia itemsTotal, curPage e perPage. Os três metadados foram incluídos na projeção, mantendo historico: history_page, o filtro pelo pedido, ordenação, limites e autorização próprio/global antes da consulta do histórico. Não há contagem artificial ou consulta adicional.
- ID extraído de /compras/<id> e parâmetros history_page/history_per_page verificados com mocks. Parser continua estrito; diagnóstico agora informa seção e campo incompatível (solicitacao, produto ou historico), sem valores pessoais, payloads ou tokens. O detalhe distingue erro de conexão, servidor e contrato, sem retry automático. Nenhuma regra de listagem foi alterada.
- 30 testes direcionados aprovados. Xano Developer MCP local 2.2.6 validou o script sem erros. Não há HTTP real observado para o detalhe nos logs disponíveis; a omissão estrutural foi corrigida, mas sua relação com a falha atual requer leitura autenticada do endpoint publicado. Nenhuma chamada remota, escrita ou publicação foi executada nesta revisão.

### Correção local dos metadados de GET /purchase_requests

- Evidência fornecida na sessão Reflex: HTTP 200, response_contract, itemsTotal ausente. Tanto o GET local quanto o backup anterior habilitam totals: true, mas sua projeção selecionava somente items.*; não há envelope alternativo nem renomeação de itemsTotal nesses contratos.
- Adicionados itemsTotal, curPage e perPage à projeção pública da consulta paginada. A resposta continua sendo requests_page; o total é produzido pela consulta filtrada, sem contagem da página, fallback zero, consulta adicional ou mudança de autorização.
- Regressão estrutural verifica os metadados na projeção real do XanoScript; testes com mocks cobrem seis itens com total maior, segunda página menor e vazio legítimo. Isso não executa a consulta no Xano; retorno publicado corrigido ainda depende de preview, autorização de publicação e GET autenticado.
- Validações desta correção: 26 testes direcionados aprovados, Reflex compile --dry, OpenSpec strict e diff check dos arquivos alterados aprovados. A biblioteca local já instalada do Xano Developer MCP 2.2.6 validou purchase_requests_get.xs sem erros; isso não comprova o retorno em runtime. Nenhum dry-run ou push foi executado nesta revisão.

### Diagnóstico local da falha de listagem

- A mensagem genérica ocultava erros de transporte, servidor e contrato; o rodapé apresentava Total 0 mesmo sem leitura concluída. Adicionados logs sanitizados com endpoint, status, classe, origem e campo/tipo inválido de paginação, sem payload, tokens ou dados de pedidos. Totais e paginação só aparecem após sucesso (lista preenchida ou vazia).
- O parser preserva suas validações; somente os diagnósticos foram detalhados. Não foram alterados contrato Xano, helper, grants, cache, coordenador ou retries.
- O reflex.log disponível não contém a falha de GET /purchase_requests; portanto, causa raiz e HTTP real permanecem não confirmados. Próxima evidência: uma consulta manual na sessão autenticada com o código recarregado e leitura da linha Purchase list read failed. Não houve GET remoto nem execução de escrita nesta revisão.

### Correção local de acesso do Líder à área Compras

- Removidos os bloqueios por nome de perfil no guard de rota e no estado da página: acesso exige read + manage, preservando o bypass administrativo. O menu regular oferece Compras solicitadas somente a gestores autorizados.
- Página inicial do Líder e demais perfis existentes continua /dashboard; Compras continua em /compras e sem acesso às demais áreas. Reposição permanece uma página separada.
- Testes com mocks cobrem administrador, gestor, leitor sem manage, lista/detalhe e redirecionamento do perfil Compras. Compile local aprovado e rotas /compras e /compras/8 responderam HTTP 200; isso não comprova a sessão autenticada nem que o backend em execução recarregou os guards.
- GET /permissions lê o catálogo persistido: publicar endpoints ou a definição do provisionamento não cadastra purchase_request.status.update nem o perfil. Existência remota da função e do catálogo ainda precisa de conferência autorizada; nenhum provisionamento ou consulta ao Xano foi executado nesta revisão.

### Revisão vigente — PATCH nativo acadêmico

- PATCH de status sem db.direct_query, versão, reivindicação ou Lock; db.get, validação do estado lido, db.edit e db.add de histórico na mesma db.transaction.
- MCP aprovou a sintaxe final, sem warnings. Foram aprovados 98 testes direcionados: 18 de Compras, 56 de Reposição e 24 de autorização de rotas. Não são testes de execução dos scripts no Xano.
- Reflex compile --dry e OpenSpec strict aprovados. O plano publicacao-academica.md contém os previews seletivos e os testes funcionais ainda pendentes, sem execução remota.
- O uso de um operador por vez e a ausência de garantia contra concorrência estão documentados. Nenhum teste avançado foi declarado aprovado.

As evidências abaixo registram etapas anteriores. As referências a bloqueio por SQL/concorrência foram superadas pela decisão vigente; não significam que propriedades de concorrência foram comprovadas.

### Revisão de estabilização em 2026-11-11

- Revisão Free/isolamento: 332 testes aprovados, incluindo 11 novos testes estruturais e com mocks para Reposição, perfis, projeção restrita, compatibilidade e cache. Compile Reflex e OpenSpec strict aprovados; seis arquivos XanoScript revisados passaram na sintaxe MCP. Os arquivos desta etapa não apresentaram whitespace.
- MCP instalado 2.2.6 rejeitou tanto db.bulk.update com where quanto isolation=serializable. O gráfico local também depende de db.direct_query; a alternativa nativa está documentada em compatibilidade-xano-free.md, sem alteração de dashboard-funcional ou do gráfico.

- A suíte completa passou após corrigir exclusivamente a inicialização de bookkeeping nas fixtures Reflex e uma variável não inicializada no teste de Reposição: 321 testes aprovados. As asserções foram preservadas.
- O MCP aceitou a sintaxe do PATCH de status, mas rejeitou `db.bulk.update ... where` em uma amostra local. A documentação oficial restringe Direct Database Query a Launch/Scale atualizados; não foi comprovada sua disponibilidade no Xano Free nem a participação do SQL na mesma transação do histórico. Itens 2.3 e 4.5 permanecem abertos; o PATCH não está liberado para publicação.
- A revisão seguinte corrigiu localmente a exposição de pedidos alheios em `GET /stock/replenishment`, incluindo compatibilidade do consumidor e separação de cache próprio/global. O item 4.7 está concluído apenas localmente; o item 4.9 exige validação no Xano publicado.
- Os testes locais não validam autorização, importação, conflitos, rollback ou isolamento em runtime do workspace. Nenhum dry-run, publicação ou escrita remota foi executado nesta revisão.

- Os seis XanoScripts criados/modificados passaram na validação sintática do Xano Developer MCP. Isso não comprova aceitação pelo importador remoto nem execução em `v1`.
- Os 16 testes novos com mocks e análise estrutural passaram; o conjunto direcionado com compras, autorização operacional, contratos de compra e Dashboard teve 76 testes aprovados após a revisão final.
- `reflex compile --dry` e `openspec validate perfil-compras-solicitacoes --strict` passaram.
- A execução anterior da suíte teve 110 erros: 109 fixtures Reflex sem `_was_touched` e um `UnboundLocalError` em `tests/test_replenishment_ui.py`. Essas causas foram corrigidas nas fixtures e no teste, sem remover cobertura; a execução atual passou com 321 testes.
- `git diff --check` global continua bloqueado por whitespace preexistente em `xano/api/inventory_catalog/users_by_id_inactivate_patch.xs:35`. Os arquivos alterados por esta change não apresentaram whitespace.
- Não houve acesso ao Xano remoto, provisionamento, associação de usuários, publicação ou teste de concorrência/rollback em runtime.
