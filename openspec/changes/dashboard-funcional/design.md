# Decisões de implementação

## Limites e evidências

### Registro histórico de implementação local — 2026-11-11

Na revisão de 11/11/2026, nenhum objeto desta change tinha sido publicado ou executado remotamente. Naquele estado, os contratos novos eram condicionados a flags locais desligadas até publicação e configuração do marco. Essa anotação é histórica e não descreve o estado atual do código ou do Xano. Validação MCP de XanoScript comprova sintaxe reconhecida pelo validador, não importação ou runtime.

### Estado posterior reportado pelo usuário — 2026-11-14

O usuário informou que o gráfico com dados reais e os períodos de 7 dias, 30 dias e 12 meses funcionam; que notificações reais, contador, leitura individual e permissões funcionam; e que testou a alteração de senha com logout, login pela nova senha e rejeição da senha anterior. Também informou validação visual manual do Dashboard em desktop e viewport móvel em 16/11/2026. São relatos/aceitações do usuário, sem capturas ou logs independentes, e não foram repetidos nesta revisão documental.

### Estado conferido no código local — 2026-11-16

- `NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED` tem padrão `true` em `Meu_projeto/pages/dashboard.py`.
- `NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED` tem padrão `true` em `Meu_projeto/state/dashboard_notifications.py`.
- `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED` tem padrão `false` em `Meu_projeto/pages/account_password.py`.
- `scripts/iniciar_nexstock_dev.ps1` somente inicia o Reflex pela `.venv`; não define nem restaura essas três flags. `scripts/iniciar_teste_alteracao_senha.ps1` controla somente a flag da alteração de senha no processo local.

Logo, a descrição histórica de que as três flags têm padrão `false` e de que o launcher de desenvolvimento as ativa está desatualizada. Esta reconciliação não altera defaults, launcher ou ambiente. Os módulos leem as flags ao importar; o valor efetivo também pode ser substituído pelo ambiente do processo que inicia o Reflex.

A aceitação manual informada pelo usuário cobre o Dashboard autenticado em desktop a 1920 × 960 e a conferência do Dashboard em viewport móvel, suficiente para a tarefa geral 3.7. A dimensão efetivamente usada no viewport móvel não foi informada. Não há evidência específica de tablet ou de todos os detalhes da central rolável; a tarefa histórica específica de notificações permanece pendente. Não foram fornecidas capturas ou logs independentes, nem feitas novas verificações visuais ou remotas neste ciclo.

Permanecem limitações: a matriz completa de autorização, propriedade, paginação, recibos de leitura, timezone, zero preenchido e comportamento do stream no Xano publicado não foi revalidada; a autorização efetiva do backend não é comprovada pelos guards Reflex; e a revogação de tokens de outras sessões não está implementada. Request History desabilitado e inputs sensíveis foram informados pelo usuário para o PATCH de senha, mas não comprovam mascaramento em Error Logs, debugger ou demais superfícies. Não se deve converter ausência de comprovação em falha funcional confirmada. Nenhuma nova tentativa remota será realizada neste ciclo.

A antiga pendência de whitespace em `xano/api/inventory_catalog/users_by_id_inactivate_patch.xs` foi tratada anteriormente. A inspeção local atual não encontrou espaço ou tabulação final nesse arquivo; nenhuma alteração de XanoScript foi feita nesta reconciliação.

## Cabeçalho e saudação

Remover apenas a busca sem ação. Manter sidebar fixa, barra superior e responsividade. O sino usa a central de notificações; o menu de usuário oferece `/conta/alterar-senha` e `AuthState.logout`. A saudação usa o primeiro nome já autenticado e horário `America/Sao_Paulo`: 05–11 bom dia, 12–17 boa tarde e demais horas boa noite. Se não houver nome, mostra somente a saudação. Não há chamada adicional para esse cálculo.

## Notificações internas

`purchase_request_history` permanece a fonte de verdade. A tabela local `purchase_request_notification_read` contém apenas `user_id`, `history_id` e `read_at`, com unicidade composta por usuário e evento. A identidade sempre deriva de `$auth.id`.

O backend exige `purchase_request.read`. Leitores comuns veem apenas pedidos cujo solicitante é o usuário autenticado. A visão global exige também `purchase_request.manage`; administradores mantêm o bypass do autorizador/perfil atual. Lista, contador e marcação aplicam o mesmo escopo e o marco `$env.NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT`. Eventos anteriores ao marco ficam fora da central, sem backfill.

São projetados apenas eventos realmente gravados: `criada`, `cancelada`, `rejeitada`, `status_alterado` e `recebimento_registrado`. Eventos de e-mail são excluídos. O frontend dá rótulos em português aos códigos existentes; não cria transições. A conclusão só é identificada quando o evento de recebimento possui dados.status_novo=concluida, persistido pelo fluxo de recebimentos. A estrutura de recibos não duplica a descrição comercial.

O carregamento ocorre ao abrir o Dashboard, com cache por sessão de 20 segundos e sem polling. Abrir o sino não repete uma leitura válida. Marcar como lida exige PATCH confirmado. O índice único protege repetição sequencial; comportamento de colisão simultânea ainda depende do banco remoto e requer teste após publicação.

## Alteração de senha

A evolução de períodos e notificações não altera a funcionalidade de senha nem resolve sua pendência de revogação remota.

O PATCH local `auth/change-password` autentica o usuário, deriva o ID de `$auth.id`, compara senha atual com `security.check_password`, verifica confirmação e a política existente (mínimo de oito caracteres, letra ASCII e dígito), e grava apenas a senha do usuário autenticado. Os três campos são sensíveis. O cliente redige chaves de senha nos logs e o endpoint não registra payload.

Após resposta confirmada, Reflex executa o logout local e exige nova autenticação. A inspeção local não encontrou endpoint ou armazenamento de sessões que permita revogar todos os JWTs emitidos. O token Xano pode continuar utilizável até sua expiração; logout local não o revoga. Revogação remota de sessões é pendência de segurança e exige investigação/aprovação separada antes de alegar encerramento global.

## Gráfico e custo de leitura

O gráfico de linhas mede **número de operações**, não quantidade física. Preserva cores, dimensões, legenda e eixos; apenas acrescenta seleção 7d (padrão), 30d e 12m. Os períodos diários incluem hoje em `America/Sao_Paulo`; 12m começa no primeiro dia do mês de onze meses atrás e termina no primeiro dia do mês seguinte ao atual. Assim, apresenta 12 meses civis incluindo o atual; registros futuros datados dentro do mês corrente também pertencem ao intervalo, sem afirmar que já ocorreram fisicamente. O GET exige `movement.read` ou `report.read`.

A versão local usa operações nativas, sem db.direct_query. Valida início à meia-noite local e, para 12m, no primeiro dia do mês. Gera 7/30 chaves Y-m-d ou 12 chaves Y-m com contadores inteiros zerados. Avança por amanhã ou +1 month, com timezone explícito; o fim deve corresponder exatamente ao período selecionado. A sintaxe de avanço mensal é validada localmente, mas seus resultados precisam de conferência no Xano. Não usa duração UTC fixa para dias civis.

Uma db.query inventory_movement filtra data_hora >= date_from e < date_to, projeta apenas tipo/data_hora e retorna stream. Cada linha incrementa uma contagem no dia/mês local; não soma quantidades nem consulta por produto ou intervalo individual. O segundo foreach monta a série ordenada. São no máximo 30 contadores, mas 12 meses podem exigir processamento de muitas linhas: runtime e custo no Free continuam pendentes de validação com dados autorizados. A segunda consulta preserva as cinco movimentações recentes globais, independentemente do período do gráfico. Nenhum índice/schema de movimentos é alterado nesta etapa.

Trocar período consulta apenas a fonte movements. A chave de cache usa sessão, datas e period, com TTL operacional existente; mudar seleção não recarrega produtos, estoque ou resumo de compras. O cliente valida todas as chaves em ordem, sem aceitar datas duplicadas/ausentes. Não reaproveita série de outro período como se fosse da seleção atual.

## Correção local dos erros publicados do Dashboard

O relato de runtime identificou DATE_RANGE_MUST_START_AT_LOCAL_MIDNIGHT e NOTIFICATIONS_ACTIVATION_MARKER_MISSING. Sem valores intermediários nem export posterior à publicação, a causa exata dessas execuções não está comprovada. O frontend gera meia-noite civil de São Paulo e agora transporta date_from/date_to como Unix milliseconds inteiros, mantendo ISO com timezone apenas para cálculo/cache local. O Xano reconstrói a fronteira com data e hora 00:00:00 explícitas, evitando depender da hora implícita de um parse apenas de data; mantém a igualdade e o fim exclusivo.

O nome e acesso $env.NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT seguem o contrato existente. Não se consultaram valores remotos. GET e PATCH agora distinguem null estrito (MISSING), texto vazio após trim (EMPTY), formato diferente de 13 dígitos positivos (INVALID) e conversão inteira sem round-trip fiel (CONVERSION_FAILED). As consultas usam apenas activation_at validado; não há fallback para zero, now ou histórico inteiro. Configurar no workspace correto o timestamp de ativação aprovado, sem aspas, expressão PowerShell ou formato de data local. Se a variável realmente não estiver disponível no contexto publicado, a correção local continuará bloqueando a central até a configuração ser conferida.

O gráfico mantém linhas e substitui o select por três chips horizontais (7 dias, 30 dias, 12 meses) com seleção destacada e chamada do mesmo handler. O popover de notificações define largura no contêiner externo, filho a 100%, min-width zero e quebra de texto/botões, com overflow horizontal oculto e vertical preservado. Nenhum estilo global é alterado. A aparência autenticada permanece pendente de conferência no navegador.

Na central, a projeção paginada inclui itemsTotal/curPage/perPage. Cache distingue sessão e escopo próprio/global. Respostas e confirmações de leitura são descartadas se a sessão/permissão mudar durante a chamada; badge/lista também verificam proprietário e escopo. O 429 bloqueia abertura/retry imediato até o cooldown e não agenda nova chamada. PATCH exige confirmação history_id/lida antes de alterar o estado local. O UNIQUE de recibos garante a restrição declarada, sem promessa de tratamento automático de colisões concorrentes.

A segunda consulta preserva as cinco movimentações recentes globais, ordenadas por `data_hora desc, id desc`, com produto/usuário e suas quantidades individuais. O envelope permanece `{serie: [{dia, entradas, saidas}], recentes: {items, curPage: 1, perPage: 5}}`. São duas declarações nativas de consulta de dados e um único GET do frontend, sem consulta em loop e sem filtro de período aplicado à lista de recentes. A documentação oficial descreve stream com foreach para reduzir uso de memória; comportamento do cursor, timezone, volume e resultado final ainda exigem validação no Xano publicado. Ver [grafico-xano-free.md](grafico-xano-free.md).

Historicamente, com `NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED=false`, o Dashboard preserva a consulta antiga das movimentações recentes e informa que a série aguarda publicação; não apresenta dados demonstrativos. O GET agregado substitui — não soma — a consulta antiga quando habilitado. O comportamento atual dos defaults e do launcher está registrado acima; esta seção descreve o contrato de fallback, não os valores atuais das flags.

Com notificações habilitadas e permissão de leitura de compras, carga fria total prevê até cinco GETs de dados: produtos, estoque, resumo de compras, gráfico+recentes e notificações. Sem a permissão de compras, não há GET do resumo nem notificações. Validação de sessão é separada. Coordenador, orçamento e TTLs existentes não foram ampliados. Sem polling e sem chamadas em troca de aba.

## Publicação e riscos

Objetos Xano locais: tabela de recibos, função de escopo, GET de notificações, PATCH de leitura, GET agregado de movimentações e PATCH de senha. A tabela e os endpoints precisam ser revisados/publicados seletivamente; `$env.NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT` precisa ser configurado com marco aprovado. As flags Reflex permanecem desligadas até contratos publicados. A consulta nativa do gráfico, filtros por grants, timezone, resposta, índices, conflito concorrente de recibo e autenticação devem ser verificados em leitura e em execução controlada no Xano antes de ligar as flags.

Nenhuma alteração de senha, leitura, compra, estoque ou e-mail real foi executada nesta implementação. A mudança não altera `purchase_request_history`, grants, tabelas remotas ou endpoints já publicados.

## Estabilização local e evidências — 2026-11-11

- A suíte completa foi executada novamente: 305 testes, 110 erros e nenhuma falha de assertion. 109 erros são fixtures de testes que criam instâncias de `rx.State` sem inicializar `_was_touched` (Reposição 40, Relatórios 28, Auth 18, Produtos 18, Saídas 5). O erro restante é um `UnboundLocalError` em `tests/test_replenishment_ui.py`: o teste reutiliza `state` fora do loop que o inicializa. Esses erros ocorrem no setup dos testes; não constituem evidência de regressão de produção desta change e os módulos fora do escopo não foram alterados.
- Um fixture dos testes de resumo do Dashboard foi corrigido com `DashboardState._init_bookkeeping`; os quatro erros que pertenciam a esse fixture desapareceram. O conjunto direcionado de Dashboard, contratos e permissões passou com 75 testes.
- O servidor Reflex iniciou em modo de produção e respondeu HTTP 200 nas rotas `/` e `/dashboard`, em `http://127.0.0.1:3002`. Isso confirma inicialização e roteamento HTTP, não validação visual autenticada.
- A inspeção visual não foi concluída: a integração de navegador não conseguiu determinar a URL atual e interrompeu o acesso. Não se usaram credenciais ou dados de sessão. A disposição desktop/móvel e a renderização após autenticação permanecem pendentes de conferência no navegador.
- O código remove a busca do cabeçalho; o cumprimento disso foi confirmado por inspeção estrutural e teste, não por captura visual. A saudação deriva do primeiro nome autenticado e do relógio `America/Sao_Paulo`; o menu do usuário chama `AuthState.logout` para sair.
- As flags `NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED`, `NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED` e `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED` estavam desligadas no processo local e têm padrão `false`; as rotas opcionais continuam inativas.
- Revisão local dos contratos: notificações leem apenas linhas existentes de `purchase_request_history`, após o marco de ativação; a API exige `purchase_request.read`, restringe pedidos próprios por `$auth.id` e amplia o escopo somente para `purchase_request.manage` ou administrador. GET é paginado, o PATCH de leitura usa o usuário autenticado, e a interface apresenta datas em `America/Sao_Paulo`. A lista inclui apenas códigos/eventos persistidos; nesta cópia local, há escritores explícitos apenas para `criada` e `cancelada`, portanto os outros tipos só aparecerão se uma linha real desse tipo existir. Não há teste de runtime nem publicação Xano.
- O gráfico agrega contagens de operações por tipo, sem somar quantidades/unidades, para sete datas civis de São Paulo e usa intervalo UTC semiaberto; dias zero são preenchidos após agregação. O endpoint exige `movement.read` ou `report.read`. A revisão posterior removeu seu SQL; as operações nativas, permissões e resultados ainda precisam de validação no Xano após publicação.
- Os endpoints locais `auth/login` e `auth/signup` chamam `security.create_auth_token` com `expiration = 86400`. O PATCH de senha verifica a atual e grava a senha do `$auth.id`, mas não contém revogação de token nem existe controle de sessão/denylist neste change. O logout de Reflex remove o token local, mas não prova invalidação remota; um JWT existente pode continuar válido até expirar. Revogação global exigiria desenho separado (por exemplo, versão de sessão consultada em todos os endpoints protegidos) e revisão de segurança. A flag de senha permanece desabilitada.
- Nenhuma operação foi escrita no Xano e nenhum dado, dispatcher ou e-mail foi tocado nesta etapa.

## Refinamento local da central de notificações

O usuário confirmou notificações reais, contador, leitura individual e permissões funcionando. Esta revisão trata apenas de layout e estado local. Nenhum XanoScript, contrato HTTP, flag, cache global, coordenador, gráfico, Compra ou recebimento é alterado.

O botão do sino mantém 40 x 40 px, contorno e foco nativos. Um texto circular absoluto de 18 px no canto superior direito usa vermelho discreto e texto branco. Só aparece com total positivo e escopo/sessão correspondentes. O rótulo visual limita-se a 9+; o total real permanece no estado, no cabeçalho do painel e no aria-label. O badge ignora eventos de ponteiro e fica dentro do botão relativo.

O popover continua alinhado ao fim do botão, com largura min(420px, 86vw), máximo de 90vw e altura do conteúdo limitada a min(65vh, 520px). O título e o contador ficam fora da lista rolável. A lista usa max-height min(48vh, 380px), min-height zero e overflow vertical auto/horizontal hidden. Textos quebram, separadores são discretos e as ações de leitura continuam compactas; o estado Lida é texto secundário.

O on_scroll nativo usa rx.call_script para medir somente o elemento da lista. A cada no máximo 600 ms, a verificação retorna apenas near_end e a página renderizada. Quando o usuário já rolou e restam menos de 96 px, on_list_scroll pode carregar a próxima página. O código não usa polling, observer externo, dependência nova ou timer de retry. Referências: https://reflex.dev/docs/events/event-actions/ e https://reflex.dev/docs/api-reference/browser-javascript/

O estado mantém apenas um carregamento por vez e só avança page depois de uma resposta confirmada para a página/tamanho solicitados. Acrescenta eventos sem duplicar history_id, preservando a ordem e leitura já confirmadas. Um evento atrasado com página antiga é descartado. Falhas preservam a lista e cursor, bloqueiam novas tentativas por scroll e oferecem recuperação explícita da mesma página após cooldown. Confirmar uma leitura não remove esse bloqueio de paginação. Resultados de outra sessão/escopo são descartados como antes.

Carregar mais no rodapé usa as mesmas travas e permite navegação por teclado ou recuperação quando a primeira página não produzir scrollbar. Anterior/Próxima deixam a interface. Fechar o painel impede novas chamadas incrementais; não cancela uma leitura já iniciada. Abertura reutiliza o cache existente. Quando a primeira página expira, uma nova abertura pode iniciar uma lista atualizada; não há acompanhamento em tempo real. A paginação por offset existente pode deslocar registros se novos eventos surgirem durante a leitura: sobreposições são deduplicadas; novos eventos no topo aparecem numa nova carga, sem inventar uma garantia de snapshot/cursor.

Os testes usam mocks para vazio, poucos/muitos itens, páginas, duplicatas, leitura, erros, cooldown, sessão e badge 0/1/2/9/10+. A compilação e os componentes gerados validam a ligação dos eventos e limites responsivos; não substituem a conferência visual autenticada em navegador. Não havia servidor nas portas 3000/8000 nem Playwright instalado no ambiente consultado. Não foram instaladas dependências, usadas credenciais ou iniciadas operações reais.

Conferência manual pendente: reiniciar o processo Reflex com as flags atuais; testar sino fechado/aberto, scroll com eventos já existentes e larguras 1920, 1024 e 360 px. Confirmar título fixo, ausência de rolagem horizontal, badge dentro do botão e preservação dos itens ao carregar páginas. A marcação real como lida não foi executada nesta revisão; seus testes locais usam mocks.

## Navegação por notificação

Cada linha passa a oferecer abertura do pedido usando o purchase_request_id armazenado no item carregado para a sessão. A área principal usa botão nativo, acionável por Enter/Espaço, com foco visível e indicação discreta por cursor/hover. O botão separado Marcar como lida permanece irmão do botão de abertura; ambos interrompem propagação do clique para a linha, conforme https://reflex.dev/docs/events/event-actions/ . Não há botão aninhado nem alteração das dimensões do painel/sino.

open_notification recebe history_id e localiza a notificação no estado validado, sem aceitar um destino arbitrário. Confere sessão, proprietário, escopo e grants atuais. A rota /compras/[request_id] existente exige read + manage no Reflex; essa restrição continua valendo e não foi ampliada nesta entrega. O backend mantém autorização por registro. Quem possui apenas read pode continuar consultando as notificações permitidas e usando Marcar como lida, mas recebe mensagem de acesso ao tentar abrir a área gerencial. Esta limitação já existia na rota, não constitui uma nova concessão ou mudança de perfil.

Para evento não lido, a abertura chama o mesmo fluxo interno de leitura usado pelo botão. Somente confirmação válida do cliente existente atualiza o item e contador. Falha de rede/provedor ou recusa do PATCH não impede encaminhar à rota do pedido; o estado permanece não lido e o GET de detalhes ainda pode recusar acesso. Não há retry automático. Cooldown também pode dispensar a tentativa, permitindo navegar com o estado não lido. Um 401 mantém logout; sessão/permissão trocada durante a chamada impede redirecionar usando dados antigos.

Uma trava de abertura é reservada antes do primeiro yield e permanece até reabrir a central. Isso bloqueia cliques repetidos inclusive após falha ambígua, quando o redirecionamento já foi emitido. Reabrir o painel libera a trava; o cache e carregamento incremental continuam como antes. A notificação lida dispensa completamente o PATCH. Cancelamento/conclusão não são filtrados pela ação. Nenhum status comercial, botão Voltar, XanoScript, gráfico ou regra de estoque foi alterado.

Testes locais usam mocks para sucesso/falha/timeout/401, contador, clique repetido, botão isolado, troca de sessão, cooldown, estados finais e negação pelo guard atual. O clique real e a leitura live não são executados durante os testes. Conferência manual: com sessão autorizada, abrir o sino e acionar evento existente; verificar /compras/ID e Voltar. Em teste autorizado de leitura, confirmar redução apenas após backend; usar outra notificação para confirmar que Marcar como lida mantém a página. Conferir foco e ativação por Tab/Enter/Espaço.
