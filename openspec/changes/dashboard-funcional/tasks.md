# Tarefas

## Especificação e implementação local

- [x] 1.1 Registrar as decisões aprovadas para busca, notificações, saudação, senha, gráfico e orçamento.
- [x] 1.2 Remover a busca inoperante e manter sidebar/layout.
- [x] 1.3 Implementar saudação por primeiro nome autenticado e hora de São Paulo.
- [x] 1.4 Implementar menu de usuário com alteração voluntária de senha e logout existente.
- [x] 1.5 Criar contrato local de alteração de senha com validação da senha atual, confirmação, política e proteção de campos sensíveis.
- [x] 2.1 Criar localmente tabela mínima de recibo de leitura individual com índice único usuário/evento.
- [x] 2.2 Criar localmente GET de notificações com paginação, contador, marco obrigatório e escopo no backend.
- [x] 2.3 Criar localmente PATCH de marcação como lida usando somente identidade autenticada.
- [x] 2.4 Criar localmente GET de contagem diária e recentes com db.query/stream e filtros de data nativos, sem Direct Database Query nem soma de unidades.
- [x] 2.5 Integrar componentes Reflex, cliente Xano, cache e invalidação sem polling e sem alterar o limite do coordenador.
- [x] 2.6 Manter notificações, gráfico agregado e alteração de senha desligados por padrão nos arquivos; a ativação local ocorre somente pelo launcher explícito de desenvolvimento.

## Validação local

- [x] 3.1 Acrescentar testes de contratos, escopo de permissões, datas, série incompleta, senha e privacidade entre sessões.
- [x] 3.2 Executar testes direcionados do Dashboard, permissões e novos contratos: 75 aprovados na revisão anterior. As fixtures foram corrigidas posteriormente na estabilização de perfil-compras-solicitacoes (332 testes de base aprovados); esta etapa executou 60 testes direcionados do Dashboard.
- [x] 3.3 Validar os seis arquivos XanoScript novos/modificados pelo MCP (sintaxe local somente).
- [x] 3.4 Executar `reflex compile --dry`.
- [x] 3.5 Validar a change com OpenSpec `--strict`.
- [ ] 3.6 Resolver o whitespace preexistente em `xano/api/inventory_catalog/users_by_id_inactivate_patch.xs` ou tratar esse arquivo em revisão separada antes de exigir `git diff --check` limpo; ele está fora desta change e já tinha alterações locais.
- [ ] 3.7 Conferir visualmente em sessão Reflex autenticada e resolução desktop/móvel.

## Pendências de publicação e segurança

- [x] 4.1 Publicação seletiva dos contratos necessários reportada pelo usuário; funcionalidades de notificações, gráfico e senha foram confirmadas em uso. Esta anotação registra o estado informado e não autoriza nem executa nova publicação.
- [x] 4.2 Configuração do marco de ativação reportada pelo usuário; a central de notificações foi confirmada em funcionamento e continua sem backfill de histórico anterior.
- [ ] 4.3 Completar a verificação documentada no Xano publicado de permissões, propriedade, paginação, contagem nativa/stream, timezone, zeros diários e recibos de leitura; o funcionamento geral foi reportado, mas esta matriz completa não foi revalidada aqui.
- [ ] 4.4 Investigar com evidência do Xano a revogação de JWTs/sessões após troca de senha. Logout Reflex é local e não prova revogação remota.
- [x] 4.5 Teste funcional da alteração de senha reportado pelo usuário: logout, login com a nova senha e rejeição da senha anterior. Isso não comprova revogação de outras sessões nem proteção completa dos logs.
- [x] 4.6 Validar o launcher local que habilita as flags apenas no processo de desenvolvimento; manter os valores padrão desligados fora dessa execução.
- [ ] 4.7 Não declarar concorrência, rollback ou revogação de sessões comprovados por testes locais/sintaxe.
- [ ] 4.8 Confirmar os limites de exposição em Error Logs, debugger e observabilidade; decidir separadamente sobre ativação permanente da troca de senha. `Request History` Disabled e inputs sensíveis foram confirmados no endpoint, mas não provam mascaramento em todas as superfícies.

## Revisão do gráfico para Xano Free

## Evolução local de notificações e períodos

- [x] Preservar gráfico de linhas, cores, dimensões e legenda e acrescentar seleção 7d/30d/12m.
- [x] Parametrizar calendário de São Paulo, validação do cliente e agregação nativa diária/mensal, mantendo as cinco recentes e duas consultas de dados no endpoint.
- [x] Reutilizar cache por sessão/período e consultar apenas movimentações na troca de seleção, sem polling e sem ampliar orçamento.
- [x] Corrigir projeção dos metadados das notificações e reforçar proteção contra mudança de sessão/escopo durante GET/PATCH.
- [x] Validar confirmação de leitura antes de marcar localmente e identificar conclusão somente pelo status persistido no evento de recebimento.
- [x] Preparar plano seletivo em publicacao-notificacoes-grafico.md, mantendo flags sem ativação automática.
- [x] Validar localmente: 74 testes Dashboard (14 novos), 116 testes regressivos de compras, compile Reflex, OpenSpec strict e quatro XanoScripts válidos no MCP. São mocks/oráculos/estrutura; não comprovam execução remota.
- [ ] Executar conferência visual autenticada e validar runtime Xano após publicação autorizada; não confundir com mocks/sintaxe.

### Evidência histórica anterior

- [x] Remover SQL e validar sintaxe do endpoint nativo pelo MCP, sem publicar.
- [x] Acrescentar testes estruturais, oráculo independente de calendário/contagens e mocks do cliente para vazio, limites semiabertos, agrupamento, unidades e cinco recentes.
- [x] Executar 60 testes direcionados do Dashboard (nove novos), compile Reflex e OpenSpec strict das duas changes afetadas, sem ativar flags nem publicar.
- [ ] Validar em execução de leitura no Xano as fronteiras civis, os filtros, o stream completo e a correspondência com as linhas reais antes de habilitar a flag. Testes locais não executam XanoScript.

## Correções locais após erros publicados e ajustes visuais

- [x] Enviar fronteiras em Unix milliseconds com timezone obrigatório no cliente e reconstruir 00:00:00 explicitamente no Xano, mantendo validação e fim exclusivo.
- [x] Distinguir marco ausente/vazio/malformado/conversão falha em GET e PATCH, sem fallback nem exposição do valor.
- [x] Trocar seleção do gráfico por três chips e ajustar somente largura/quebra/overflow do popover de notificações.
- [x] Validar 80 testes direcionados de Dashboard, três XanoScripts no MCP, compile Reflex, OpenSpec strict e diff check dos arquivos desta correção.
- [ ] Confirmar com export publicado e GETs autorizados a causa exata dos erros; configuração remota e avaliação de parsing não foram inspecionadas em runtime nesta etapa.
- [ ] Comparar export posterior à publicação e executar previews seletivos dos três endpoints antes de autorizar atualização real. Conferência visual autenticada também permanece pendente.

## Registro de estabilização local — 2026-11-11

- [x] Reexecutar a suíte completa: 305 testes; 110 erros restantes, sem falhas/assertions.
- [x] Corrigir o fixture de `DashboardState` deste change para inicializar o bookkeeping do Reflex; os quatro erros do Dashboard desapareceram.
- [x] Reexecutar o conjunto direcionado de Dashboard/contratos/permissões: 75 aprovados.
- [x] Os 109 erros de bookkeeping e o UnboundLocalError registrados nessa execução histórica foram resolvidos na estabilização de perfil-compras-solicitacoes, com 332 testes de base aprovados. Nenhuma fixture desses módulos foi alterada novamente na etapa do gráfico.
- [x] Iniciar Reflex em modo prod; as rotas locais `/` e `/dashboard` responderam HTTP 200 em `http://127.0.0.1:3002`.
- [ ] Revisão visual autenticada e responsiva pendente: a ferramenta de navegador não conseguiu identificar a URL e encerrou o acesso. Nenhuma credencial foi usada; HTTP 200 não comprova aparência nem sessão autenticada.
- [x] Confirmar flags desligadas no processo local: notificações, gráfico real e troca de senha.
- [x] Revisar estaticamente os contratos locais de notificações e gráfico e a expiração dos tokens; nenhuma chamada de escrita/publicação remota foi feita.
- [ ] Revogação remota de JWT não comprovada: login/signup locais definem expiração de 86400 segundos; troca de senha altera a senha, mas não revoga tokens já emitidos. `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED` continua desligada.

## Diagn?stico de recentes, marco e resumo ? 2026-11-12

- [x] Revisar consulta global das cinco recentes, parser e proje??o; impedir descarte silencioso de itens n?o objetos. N?o alterar filtro nem criar consulta adicional.
- [x] Acrescentar diagn?stico sanitizado de recentes vazias com s?rie n?o vazia e falha do contrato solicitacoes_abertas; n?o registrar registros, token ou valor do marco.
- [x] Aumentar espa?amento m?nimo dos r?tulos de 30 dias, preservando s?rie di?ria, linhas, cores e per?odos.
- [ ] Confirmar retorno atual de recentes.items e sa?da da consulta recent_page. N?o h? evid?ncia suficiente para alterar o endpoint.
- [ ] Confirmar vers?o publicada e reconhecimento da vari?vel no workspace, sem fallback e sem alterar o marco aprovado.
- [ ] Capturar erro atual do resumo: o reflex.log dispon?vel ? de 11/11 e mostra ConnectError sem HTTP; n?o prova a causa da falha atual.

Valida??es desta etapa ser?o registradas em publicacao-notificacoes-grafico.md. Nenhum XanoScript ou m?dulo de Compras/Recebimento foi alterado.

### Corre??o da proje??o de recentes ap?s evid?ncia HTTP 200

- [x] Registrar evid?ncia fornecida pelo usu?rio: cinco elementos null no backend, s?rie v?lida.
- [x] Substituir map inline da resposta por foreach/array.push com os seis campos p?blicos, preservando consulta e gr?fico.
- [x] Criar regress?o estrutural contra retorno ao map inline; preservar testes que rejeitam itens null e mant?m as recentes nos tr?s per?odos.
- [ ] Confirmar objetos v?lidos no servidor ap?s revis?o/publica??o separadamente autorizadas; n?o declarar runtime corrigido com mocks.

## Corre??o da proje??o booleana de leitura

- [x] Registrar erro real informado pelo usu?rio: Invalid pattern em compara??o de ID do recibo dentro de eval, ap?s corre??o do nome do marco no painel.
- [x] Projetar somente read_receipt_id e calcular lida como booleano no stack, em foreach/array.push; n?o expor o ID auxiliar.
- [x] Preservar join por auth.id, consulta unread_total, autoriza??o, eventos, marco e metadados de pagina??o.
- [x] Validar 35 testes direcionados, incluindo quatro regress?es de estrutura/contrato, e sintaxe do GET no MCP. Mocks n?o executam o join nem comprovam a avalia??o no Xano.
- [ ] Confirmar em runtime lida true/false com recibos j? existentes, isolamento e importa??o ap?s revis?o/publica??o autorizadas. Nenhum PATCH de leitura executado.

### ParseError na proje??o do ID do pedido

- [x] Revisar schema inteiro/refer?ncia, joins, eval e consulta unread_total; localizar proje??o redundante de campos nativos.
- [x] Preparar remo??o de evals nativos e mapeamento id ? history_id no stack, com regress?o estrutural; n?o alterar joins nem escopo.
- [x] Validar 36 testes direcionados e sintaxe local do GET; sem prova de runtime.
- [ ] Confirmar a etapa exata do ParseError no Request History; se contador, investigar join publicado antes de atribuir a causa a eval.
- [ ] Validar resposta publicada e isolamento ap?s autoriza??o separada; n?o declarar o erro resolvido com valida??o local.

### Diagnóstico instrumentado, sem nova correção funcional

- [x] Registrar que a remoção de evals não resolveu o erro no runtime relatado; hipótese anterior insuficiente.
- [x] Preparar wrappers temporários LIST/COUNT com erros constantes sanitizados, preservando as duas consultas por hashes de regressão.
- [x] Documentar histórico existente, captura limitada, códigos temporários HTTP500 e remoção em diagnostico-parseerror-notificacoes.md.
- [x] Executar 40 testes locais; GET válido no MCP. Nenhuma chamada remota realizada.
- [ ] Revisar instrumentação e correção de nomes dos joins antes de publicação/execução separadamente autorizadas; confirmar a etapa e o comportamento no runtime.

### Coerência dos nomes dos joins de notificações

- [x] Alinhar os dois nomes declarados nos joins às referências existentes nas consultas de lista e contador, após autorização do usuário; preservar condições e contratos.
- [x] Adicionar regressão de referências a nomes declarados e manter hashes de proteção do restante das consultas.
- [ ] Confirmar no Xano publicado se o ajuste elimina o ParseError; validação sintática não comprova essa causa.

### HTTP 200 rejeitado após resposta vazia válida

- [x] Localizar as validações que geram XanoServerError com status 200 e preparar diagnóstico por campo/tipo sem expor valores.
- [x] Preservar validação estrita, isolamento e ausência de retries; revisar elegibilidade e limitação local sem alterar endpoints ou orçamento.
- [x] Criar testes com mocks para contratos vazio/preenchido, violações por campo, privacidade do log e cooldown local.
- [ ] Obter a linha sanitizada do runtime ou tipos da resposta existente para identificar o campo real inválido.
- [ ] Confirmar por leitura a elegibilidade dos eventos já criados, sem alterar o marco nem gerar registros.
- [ ] Corrigir e publicar somente se a evidência apontar uma alteração concreta necessária no endpoint; não considerar a funcionalidade resolvida com testes locais.

### Evidência do status_novo como objeto

- [x] Registrar evidência de resposta publicada com status_novo objeto, incompatível com string/null esperado pelo cliente.
- [x] Corrigir somente a extração de status_novo no GET para acesso direto a dados.status_novo, preservando consultas e demais campos.
- [x] Adicionar regressões contra objeto de metadados no campo de status, aceitando texto/null sem flexibilizar o contrato.
- [ ] Comparar a definição publicada atual e executar preview seletivo; CLI indisponível nesta sessão por ENOMEM antes da execução.
- [ ] Publicar o GET corrigido após preview e confirmar notificações dos eventos existentes, sem novos pedidos ou escritas comerciais.

### Refinamento visual e rolagem incremental da central

- [x] Registrar confirmação do usuário de que notificações, contador, leitura e autorização estão funcionando; preservar contratos Xano.
- [x] Remover Anterior/Próxima do painel e manter título/contador fora da lista com rolagem vertical limitada e sem overflow horizontal.
- [x] Implementar carregamento incremental por scroll com throttle, página esperada, trava de operação e deduplicação por history_id; preservar lista em falhas e não repetir automaticamente.
- [x] Oferecer Carregar mais como alternativa acessível por teclado, usando as mesmas travas e paginação.
- [x] Posicionar badge absoluto dentro do botão relativo, ocultar com total zero e limitar apresentação a 9+, mantendo total real e descrição acessível.
- [x] Criar testes locais com mocks para vazio, páginas adicionais, scroll fechado/aberto, sobreposição, falhas, cooldown, sessão, leitura confirmada e badge.
- [x] Aprovar 97 testes direcionados/regressivos locais, Reflex compile --dry e OpenSpec strict; chamadas GET/PATCH dos testes são simuladas.
- [ ] Confirmar visualmente em navegador autenticado nas larguras desktop/tablet/móvel, sem afirmar aceitação visual a partir da compilação.

### Abertura de detalhes pela notificação

- [x] Implementar abertura via purchase_request_id do item carregado e tentativa única de leitura via history_id, reutilizando o fluxo confirmado existente.
- [x] Preservar leitura/contador em falhas, permitir navegação autorizada e manter proteção de sessão e cooldown, sem retry automático.
- [x] Bloquear cliques repetidos até reabrir a central e separar Marcar como lida da ação de navegação com stop_propagation.
- [x] Manter layout e oferecer botão nativo acionável por teclado, foco visível e hover discreto.
- [x] Preservar a autorizacao dos detalhes: `purchase_request.read` permite pedidos proprios e a leitura global exige tambem `purchase_request.manage` ou bypass administrativo; o Xano aplica o escopo. Pedidos cancelados/concluidos continuam acessiveis conforme autorizacao; manter Voltar.
- [x] Adicionar testes locais com mocks para ações, permissões, erros, sessão, contador e eventos isolados.
- [x] Aprovar 122 testes direcionados/regressivos, Reflex compile --dry e OpenSpec strict, sem chamadas de escrita live.
- [ ] Validar visualmente a navegação autenticada e o comportamento real de leitura em procedimento autorizado; nenhum PATCH live foi executado nesta entrega.

### Conclusão local da alteração voluntária de senha

- [x] Reutilizar rota, menu, flag, cliente e PATCH existentes, preservando o fluxo obrigatório inicial e os quatro perfis.
- [x] Validar a senha atual e rejeitar senha nova igual pelo mecanismo nativo do Xano; manter identidade por auth.id e tipo password existente.
- [x] Completar formulário com labels, mostrar/ocultar, cancelamento, limpeza, prevenção de duplicidade e mensagens sanitizadas.
- [x] Exigir confirmação booleana e reutilizar complete_password_change para encerrar a sessão local com aviso no login, sem alegar revogação remota.
- [x] Proteger logs/payloads do cliente de senha e documentar configuração remota de Request History/debugger como pré-requisito operacional.
- [x] Criar testes locais de formulário, perfil, autorização estrutural, política, erros, privacidade e sessão; preservar flag false.
- [x] Aprovar 121 testes direcionados/regressivos locais, validação MCP do PATCH, Reflex compile --dry e OpenSpec strict. Senhas/hashes nativos e revogação remota não foram exercitados em runtime.
- [ ] Comparar com exportação remota atual e executar preview seletivo; CLI falhou em help por ENOMEM e não foi repetida.
- [ ] Conferir proteção efetiva de logs/histórico no endpoint publicado antes do primeiro teste com senha.
- [ ] Publicar sob autorização e validar funcionalmente com conta dedicada; nenhum teste de escrita live realizado.
- [ ] Rever proposta de revogação de outras sessões separadamente se esse requisito se tornar obrigatório; sem alteração estrutural automática.
