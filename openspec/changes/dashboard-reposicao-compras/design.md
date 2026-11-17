# Design: Dashboard e Reposição de Estoque

## Dependências

A Change backend `backend-solicitacoes-compras` deve fornecer endpoints de resumo e reposição antes da integração visual. A Change `integracao-dashboard-real` permanece separada e com sua validação manual pendente. Esta Change não a arquiva nem altera seus artefatos.

## Dashboard

- Extrair o desenho geométrico inline da tela Login para um componente Reflex reutilizável e aplicar o mesmo componente à sidebar, mantendo marca, cores e proporções existentes.
- Manter o card Produtos ativos.
- Remover somente os cards Categorias e Fornecedores do Dashboard; manter seus módulos e caches próprios.
- Mostrar “Estoque insuficiente” como quantidade de Produtos ativos com saldo zero ou positivo abaixo do mínimo. A contagem inclui Produtos com solicitações ativas. Os alertas continuam visíveis mesmo após o Produto sair da lista “A solicitar”.
- Tornar o card uma navegação para Reposição.
- Adicionar “Solicitações abertas”, com contagem de estados ativos segundo o backend e visibilidade limitada por grant de leitura.
- Preservar Movimentações recentes e Alertas de estoque.
- Ajustar alinhamento e espaçamento das colunas Quantidade e Data sem alterar ordenação ou dados.

## Contratos e consumo

Endpoints candidatos, sujeitos à revisão e publicação própria:

1. `GET /dashboard/stock_summary`: contagem e amostra pequena de Produtos ativos zerados/abaixo do mínimo, sem exclusão por solicitação aberta.
2. `GET /purchase_requests/summary`: contagem de solicitações em estado de negócio ativo.
3. Reutilizar `GET /products` para Produtos ativos e `GET /movements` para movimentações recentes.

Ao remover as consultas de Categorias e Fornecedores do Dashboard e substituir a consulta de estoque por um resumo que inclui zero, a estimativa é quatro GETs frios com os grants de leitura aplicáveis: Produtos, resumo de estoque, resumo de solicitações e Movimentações. A validação `/auth/me`, quando necessária, adiciona uma chamada. É uma estimativa por contrato, não medição runtime. O endpoint de resumo pode ser agregado mais tarde se reduzir chamadas sem enfraquecer a autorização independente de cada seção.

O resumo de estoque deve exigir `stock.read`. A contagem de solicitações exige `purchase_request.read`. Produtos e Movimentações continuam sujeitos aos grants existentes. O servidor não deve devolver seção privada sem grant. Frontend continua exibindo estado sem acesso/erro, nunca zero fictício.

## Criação e cancelamento via Reflex (2026-10-26)

O usuário confirmou que `POST /purchase_requests` e `PATCH /purchase_requests/by_id/{request_id}/cancel` estão publicados no workspace 152211, branch `v1`, e foram exercitados funcionalmente: criação com status `aberta` e evento `criada`, seguida de cancelamento com justificativa e evento `cancelada`; esses endpoints não alteraram estoque. Esta confirmação é evidência runtime informada pelo usuário. A implementação da interface e os testes desta etapa são locais e simulados; nenhum POST ou PATCH foi executado pelo agente.

`XanoAuthClient` envia a criação a `POST /purchase_requests` no grupo Inventory Stock com `produto_id`, quantidade decimal normalizada, urgência em código minúsculo e `chave_idempotencia`. A resposta só é aceita quando contém ID inteiro positivo, o produto correspondente, status reconhecido, estado de e-mail válido, sinalizador de repetição booleano e `email_enviado: false`. Resposta HTTP de sucesso com formato incompleto é tratada como resultado não confirmado, preservando a mesma chave para reconciliação manual. Nenhum retry automático é realizado. A chave é criada uma vez por tentativa lógica; em timeout, erro de transporte, 429 remoto ou 5xx, formulário e payload ficam travados para edição e a ação manual mantém essa chave. Respeita-se `Retry-After`/cooldown; o limite local do coordenador é distinto de um 429 recebido do Xano.

A submissão valida a sessão e `purchase_request.create` novamente. Quantidade deve ser finita e maior que zero; urgência precisa corresponder às opções da interface. A elegibilidade exibida pela API não substitui a validação definitiva do Xano. Duplo clique é bloqueado por estado de submissão. Somente após resposta de sucesso validada a interface fecha o modal, informa ID/status e estado de e-mail sem alegar envio, invalida leituras da reposição, da lista/resumo de compras e atualiza as duas listas. O Dashboard não recebe mutação local: seu resumo de compras é invalidado para a próxima consulta e o indicador de estoque insuficiente permanece baseado no endpoint de estoque.

O acompanhamento permite abrir o modal de cancelamento apenas para solicitações `aberta` ou `em_analise`, e somente com `purchase_request.cancel` ou `purchase_request.manage`. O modal exige justificativa não vazia e confirmação explícita. A propriedade da solicitação e a transição continuam sob validação definitiva do Xano; a consulta de acompanhamento não projeta o solicitante, então a interface não presume propriedade e apresenta o erro de autorização do backend sem alterar a linha. Não há atualização otimista. Após resposta confirmada, invalida-se a leitura da reposição, lista e resumo de compras, as duas listas são recarregadas e a interface informa que o estoque não foi alterado. Uma resposta do backend `PURCHASE_REQUEST_ALREADY_CANCELLED` é reconciliada como estado terminal já alcançado e as leituras são atualizadas. Timeout/429 remoto/5xx mantém a tentativa e justificativa para ação manual, sem novo envio automático.

O cliente preserva status HTTP e códigos de domínio recebidos sem presumir que cada código de erro corresponda sempre a HTTP 409 ou 422. 401 segue o logout central; 403 fica restrito à operação; 404 e demais erros conhecidos são exibidos na operação correspondente; 429 mantém o cooldown; falhas de rede e resultados ambíguos não são reportados como sucesso. POST/PATCH não alteram estoque nem enviam e-mail nesta integração. A confirmação runtime anterior do usuário não substitui validação visual deste fluxo Reflex, nem testes repetidos de idempotência, concorrência ou falha induzida.

Os testes automatizados usam mocks para contratos do cliente, grants, quantidade/urgência inválidas, duplo clique, repetição manual com a mesma chave após timeout/429, status canceláveis, justificativa, autorização, invalidação de cache, recarga das duas abas e independência do Dashboard. São evidências simuladas; não demonstram execução real do fluxo no navegador nem comportamento de concorrência/rollback no Xano. Na validação local de 2026-10-26, `python -m unittest discover -s tests -v` passou com 213 testes, `reflex compile --dry` concluiu, ambas as Changes (`dashboard-reposicao-compras` e `backend-solicitacoes-compras`) passaram em OpenSpec strict e `git diff --check` passou. Nenhuma chamada de escrita ao Xano foi executada nesta etapa.

### Confirmação manual do ciclo pelo Reflex (2026-10-26)

O usuário informou que realizou o fluxo real na interface Reflex: a solicitação ID 2 foi criada para “Produto Teste”, quantidade 15 KG, urgência alta, com status inicial `aberta`; ela apareceu em “Compra já solicitada”. O usuário abriu o modal de cancelamento, confirmou a operação, recebeu a mensagem de sucesso e viu a solicitação sair da lista ativa. Esse relato é evidência manual de runtime informada pelo usuário; nenhum POST/PATCH ou outra operação foi executada pelo agente nesta revisão.

Na inspeção estrutural local, tanto a criação quanto o cancelamento, após resposta confirmada, chamam `_invalidate_purchase_reads`, que invalida `GET /stock/replenishment`, `GET /purchase_requests` e `GET /purchase_requests/summary` no `SessionReadCache` da sessão. A criação também reinicia as páginas e recarrega as duas listas; o cancelamento faz o mesmo. `GET /purchase_requests/summary` é a fonte do card de compras no Dashboard e é incluído na invalidação. Isso comprova o caminho de invalidação no código, não que o Dashboard tenha sido visualmente reaberto ou atualizado após cancelar a solicitação ID 2.

O código mantém uma chave de idempotência para cada tentativa lógica de criação e preserva chave e payload após resultado ambíguo; a próxima tentativa é manual e reutiliza a mesma chave. O estado de submissão bloqueia chamadas duplicadas. O cancelamento também bloqueia chamadas simultâneas na interface e preserva os dados da tentativa quando o resultado é ambíguo. O cliente comum não aplica retry automático a POST/PATCH. Esses pontos foram verificados estruturalmente e pelos testes automatizados com mocks; não equivalem a testes runtime de idempotência ou concorrência no Xano.

Continuam sem evidência independente para a solicitação ID 2: o registro de histórico `cancelada`, a limpeza de `active_product_id` e a confirmação de que o saldo e as movimentações permaneceram inalterados. Também falta confirmar visualmente a atualização do card Solicitações de Compras do Dashboard depois do cancelamento. A tarefa 4.4 permanece pendente por exigir validação visual completa do Dashboard, listas, formulário e acompanhamento; a tarefa 4.5 permanece pendente por incluir rejeição, recebimento e confirmação das invariantes de estoque, além do ciclo agora exercitado.

## Destinatário comercial no formulário — fase local (2026-10-26)

O modal agora contém Produto, Quantidade solicitada, Urgência e E-mail do destinatário, sem seleção de setor ou fornecedor. O novo campo usa validação de endereço e limite visual de 254 caracteres. A normalização aparando espaços é compartilhada com o cliente Xano; quantidade positiva, urgência válida e bloqueio durante envio continuam obrigatórios. A idempotency signature da tentativa passa a incluir o destinatário quando o contrato estiver ativo.

Para preservar o serviço publicado, `NEXSTOCK_PURCHASE_REQUEST_EMAIL_ENABLED` é lido como flag local, default `false`, sem alterar `.env`. Com a flag desligada, e-mail vazio conserva o payload antigo sem a propriedade `email_destinatario`; endereço preenchido é bloqueado com aviso explícito para não o descartar. O contrato backend local de transição agora aceita campo ausente/NULL, de modo que o POST publicado atualizado poderá manter clientes antigos. Após publicar e validar esse contrato, a flag pode ser habilitada; então o formulário exige e envia e-mail, mantendo chave e payload em tentativa ambígua. A obrigatoriedade backend será avaliada somente depois que o formulário novo estiver funcionando. Nenhuma fase envia e-mail; o sucesso ainda informa que `email_status` está pendente.

Após resposta confirmada de criação, a invalidação existente continua abrangendo Reposição, lista e resumo; o cancelamento continua preservando o destinatário no backend e invalidando as mesmas leituras. Nenhum GET passa a expor o endereço. O desenho futuro exige aviso de cancelamento somente se a entrega original tiver status confirmado `enviado`, dirigido ao endereço persistido. `email_status` não representa a segunda entrega; uma estrutura de outbox/entrega separada será avaliada quando provedor, credenciais e política de retry forem definidos. Não foi implementado envio, e-mail de cancelamento ou mudança de status para alegar entrega.

## Página de Reposição

- “A solicitar” apresenta Produtos ativos com estoque insuficiente e sem solicitação ativa.
- “Compra já solicitada” apresenta Produtos ainda insuficientes com uma solicitação ativa; a seção é informativa e não oferece criação duplicada.
- Linhas mostram código, nome, saldo atual, estoque mínimo e situação “Abaixo do mínimo” ou “Sem estoque”.
- A ação Solicitar compra aparece somente com `purchase_request.create` e quando o backend retorna elegibilidade atual.
- A página usa `stock.read` para exibir saldo e `purchase_request.read` para acompanhamento; se faltarem grants, cada área mantém seu próprio estado sem acesso.

## Formulário

O formulário recebe Produto, saldo e mínimo do resultado atual, mas o Xano revalida no POST. Quantidade sugerida é déficit positivo; para saldo zero e mínimo zero, uma unidade. Campo é editável, obrigatório e positivo. Urgência: baixa, normal, alta ou crítica.

“Cancelar” antes de enviar apenas fecha o formulário e descarta o rascunho. Não cria endpoint nem mutação. Cancelamento de solicitação persistida é uma ação separada na área de acompanhamento, visível apenas quando permitida por `purchase_request.cancel` e pela transição atual.

Após sucesso do POST, a interface confirma o registro e informa e-mail pendente/não enviado. Só então remove o Produto da seção elegível, atualiza a seção de pedidos ativos e invalida as chaves do cache afetadas. Resposta ambígua, timeout ou 429 não deve ser repetida com chave nova: reconsulta-se o estado ou se repete com a mesma chave idempotente, depois de respeitar o coordenador.

## Cache, autorização e indisponibilidade

Reutilizar `SessionReadCache` e `XanoRequestCoordinator`, sem cache persistente, polling ou outro limitador. Cache é por sessão e curto para resumos/listas; operações POST, cancelamento, mudança de estado e entrada vinculada sempre validam o Xano. Escrita confirmada invalida resumo e fila da sessão; falha de escrita não altera cache como se houvesse sucesso. 429 mantém estado anterior identificado como potencialmente desatualizado e bloqueia novas tentativas durante o cooldown. Dados antigos não habilitam ação de criar.

## Testes e aceite

Mocks devem cobrir a projeção da marca compartilhada, cards, contagem zero/abaixo, inclusão de Produtos com pedidos ativos nos alertas, separação das duas listas, grants, quantidade sugerida, urgência, submissão idempotente, cancelamento apenas de rascunho, cancelamento persistido separado, cache, invalidação, 429 e preservação da resposta anterior. Testes com mocks não provam o contrato publicado. A interface exige teste manual com usuário/grants válidos e API Xano publicada, sem dados reais alterados.

## Escopo visual independente do backend (2026-10-18)

A marca geométrica do Login foi extraída para `Meu_projeto/components/brand.py` e é reutilizada na sidebar; o desenho, as cores, dimensões e o arranjo do Login foram preservados. Os cards Categorias e Fornecedores foram removidos apenas do Dashboard e os respectivos GETs deixaram de ser executados por esse carregador. Os módulos e páginas próprios permanecem intactos.

O espaço visual de Solicitações de Compras é um card estático com o texto “Aguardando integração”. Ele não exibe contagem, não navega e não chama endpoints. A contagem real e a navegação ficam pendentes da publicação e validação dos contratos de `backend-solicitacoes-compras`.

O card existente “Abaixo do mínimo” e a consulta atual `GET /stock` com `situacao=abaixo_minimo` foram preservados sem mudança funcional. Esse contrato não cobre saldo zero e não filtra corretamente todos os Produtos inativos; portanto, o card e os alertas atuais não podem ser interpretados como a cobertura completa de necessidade de reposição. A inclusão de saldo zero, o filtro de Produto ativo e a distinção entre “A solicitar” e “Compra já solicitada” dependem de `GET /stock/replenishment` ou contrato equivalente. Após uma solicitação confirmada, o Produto deve sair somente de “A solicitar”; enquanto o saldo real permanecer insuficiente, continuará na contagem de estoque insuficiente e nos alertas, inclusive quando possuir solicitação ativa.

A retirada dos dois cards elimina dois GETs do carregamento frio quando os grants correspondentes existem. Permanecem as consultas existentes de Produtos, Estoque e Movimentações segundo os grants atuais, além da validação de sessão quando necessária. Não foram adicionados GETs de compras, alterados TTLs ou alterado o coordenador.

## Interface inicial de Reposição (2026-10-19)

A rota protegida `/reposicao` foi adicionada com o título e a descrição aprovados, além das abas “A solicitar” e “Compra já solicitada”. Ambas as tabelas exibem os cabeçalhos definidos no contrato e têm estado próprio para carregamento, vazio, erro e integração indisponível. Como os endpoints de compras ainda não estão publicados, o carregamento autorizado termina em “Integração indisponível”; as listas ficam sem linhas e a interface não afirma que não existem produtos ou solicitações.

O carregador executa primeiro `AuthState.require_auth()` e depois verifica a sessão válida e os dois grants `stock.read` e `purchase_request.read`. Sem qualquer um deles, redireciona ao Dashboard sem consultar APIs. O formulário de rascunho foi preparado com Produto somente leitura, quantidade decimal editável (`step=any`), urgência Baixa/Normal/Alta/Crítica e cancelamento que fecha e limpa apenas o estado local. A ação “Enviar pedido” permanece desabilitada e sem handler; não existe chamada aos endpoints locais ou remotos de Reposição/Compras. A abertura do formulário também revalida sessão e grants atuais, exige `purchase_request.create`, disponibilidade da integração e dados de Produto elegíveis. O Xano continuará sendo a autoridade de elegibilidade e prevenção de duplicidade quando a integração for implementada.

No Dashboard, o card existente “Abaixo do mínimo” passou a navegar para `/reposicao` apenas quando a sessão validada possui `stock.read` e `purchase_request.read`; o evento repete essa checagem. O valor, a descrição, a consulta de estoque e o desenho do card foram preservados. O card ainda representa somente o contrato atual de estoque positivo abaixo do mínimo: não inclui saldo zero nem filtra todos os Produtos inativos. A grade e o espaçamento aprovados da tabela “Movimentações recentes” não foram alterados nesta etapa.

Os testes novos usam apenas estado simulado local para verificar rota, grants, quantidade fracionária, abertura/limpeza do rascunho e botão de envio desabilitado. Eles não validam publicação nem execução no Xano. Permanecem pendentes a publicação/revisão do backend, a confirmação dos grants no catálogo, a integração das listas e contagens reais e a verificação visual no navegador. As tarefas 1.3, 2.5 e 3.3 representam decisões e preparação local já comprovadas; não indicam que a criação de compras esteja disponível.

## Mapeamento previsto para `GET /stock/replenishment` (2026-10-19)

O contrato local retorna `a_solicitar` e `compra_ja_solicitada`, cada um com `items`, `curPage`, `perPage` e `itemsTotal` próprios. Não há chamada ativa a esse endpoint nesta página; o mapeamento abaixo é para um adaptador futuro, após publicação, autorização e teste runtime.

| Campo do endpoint | View model de `pages/reposicao.py` | Uso |
|---|---|---|
| `produto_id` | `id` | Identificador usado pela ação futura de solicitação. |
| `codigo` | `codigo` | Código mostrado nas duas listas. |
| `nome` | `produto` | Nome mostrado nas duas listas. |
| `unidade_medida` | `unidade` | Unidade da quantidade no formulário futuro. |
| `quantidade_disponivel` | `estoque_atual` | Saldo mostrado nas duas listas. |
| `estoque_minimo` | `estoque_minimo` | Limite cadastrado exibido. |
| `situacao_estoque` | `situacao` | `sem_estoque` ou `abaixo_minimo`. |
| `quantidade_solicitada` | `quantidade_solicitada` | Somente em `compra_ja_solicitada`. |
| `urgencia` | `urgencia` | Somente em `compra_ja_solicitada`. |
| `solicitacao_status` | `status` | Somente em `compra_ja_solicitada`. |
| `data_criacao_solicitacao` | `data_solicitacao` | Somente em `compra_ja_solicitada`. |

`produto_ativo` e `saldo_registrado`, atualmente recebidos como argumentos do handler de formulário, são pré-condições já asseguradas pela resposta de uma lista elegível e pela verificação explícita de saldo ausente no contrato. O futuro adaptador poderá preenchê-los como verdadeiros somente para um item retornado em `a_solicitar`; não são campos adicionais projetados pelo endpoint. Essa inferência só será válida após confirmar que a versão publicada preserva esses filtros e o precondition. A paginação do primeiro grupo deve alimentar `requestable_page`/`requestable_total`, e a do segundo `requested_page`/`requested_total`; nunca combinar os totais.

Os estados das listas continuam indisponíveis até a integração e não devem ser convertidos em lista vazia ou zero. A criação permanece desabilitada. O índice único remoto de `active_product_id`, necessário para manter uma solicitação ativa por Produto sem duplicar linhas no join, e a resposta de runtime ainda exigem conferência no painel/teste Xano; testes estruturais locais não comprovam esses comportamentos.

## Resumo de estoque insuficiente do Dashboard (2026-10-19)

A auditoria confirmou que `GET /stock` com `situacao=abaixo_minimo` não inclui saldo zero nem aplica de forma suficiente o filtro de Produto ativo. `GET /stock_summary` usa outra classificação, não filtra Produtos inativos e não fornece a amostra de alertas exigida. `GET /stock/replenishment` exige `purchase_request.read` e consulta a tabela de solicitações, portanto não é apropriado como fonte do Dashboard.

Foi preparado localmente `GET /stock/insufficient_summary`, autenticado e autorizado somente com `stock.read`. O contrato retorna `items`, `itemsTotal`, `curPage` e `perPage`; cada alerta contém `product_id`, `codigo`, `nome`, `quantidade_disponivel`, `estoque_minimo`, `unidade_medida` e `situacao_estoque`. Uma consulta `db.query` com `return = {type: "count"}` calcula o total global; uma consulta paginada separada retorna no máximo 20 alertas (5 por padrão). As duas usam o mesmo filtro: Produto ativo e saldo zero ou saldo positivo abaixo do mínimo. Uma terceira consulta de existência, por join left, mantém `STOCK_BALANCE_NOT_FOUND` explícito para Produtos ativos sem linha de saldo. Nenhuma consulta por Produto nem leitura de `purchase_request` foi adicionada. O total não é inferido do tamanho da página.

O cliente Reflex possui um método dedicado ao contrato e rejeita página, total ou envelope inválidos. A projeção do Dashboard valida IDs únicos, quantidades finitas e não negativas, unidade e coerência da situação: saldo zero é `sem_estoque` inclusive quando o mínimo também é zero; saldo positivo só é aceito quando menor que o mínimo. A lista limitada não reduz a contagem global.

A troca da fonte no Dashboard é opt-in por `NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED`, cujo padrão é `false`. Enquanto continuar desligado, a tela segue consultando apenas o endpoint antigo publicado, com título e descrição antigos; não depende do contrato local ainda não publicado. Quando ativado depois da publicação e do teste remoto, a mesma fonte `stock` é substituída (não adicionada), e os três GETs frios permanecem Produtos, resumo insuficiente e movimentações. A flag é lida na inicialização do processo Reflex, então sua ativação exige reiniciar o servidor e só deve ocorrer após a validação remota. O grant `purchase_request.read` continua sendo exigido apenas para abrir `/reposicao`, conforme o guard existente; ele não é necessário para carregar o indicador. A apresentação da nova situação e unidade nos alertas também acompanha a flag.

O novo endpoint foi adicionado à lista de invalidação do cache de leitura após escritas bem-sucedidas. Não houve alteração de TTL, coordenador, orçamento, retry, operações de estoque nem da página `/reposicao`. A validação MCP e os testes locais comprovam sintaxe e contratos simulados, não publicação nem execução real. O comando seletivo para um preview futuro, ainda não executado, é `xano workspace push --dry-run -w 152211 -b v1 -d ./xano -i "api/inventory_stock/stock_insufficient_summary_get.xs"`; deve-se revisar que o preview corresponda somente a esse endpoint e não confirma publicação. Permanecem necessários o dry-run, sua revisão, autorização de publicação, publicação seletiva no workspace 152211 / branch `v1`, teste Run & Debug cobrindo contagem versus alertas limitados e saldo ausente, e ativação controlada da flag com validação no navegador. As tarefas 2.3, 4.2 e 4.4 permanecem pendentes; nenhuma evidência simulada foi registrada como runtime.

## Integracao de leitura publicada (2026-10-19)

O usuario confirmou que `GET /stock/replenishment` foi publicado no workspace 152211, branch `v1`, e executou Run & Debug no Xano: a primeira pagina retornou 6 itens em `a_solicitar`, 0 em `compra_ja_solicitada`, distinguiu `abaixo_minimo` de `sem_estoque` e incluiu produto com saldo e minimo iguais a zero. Essa e evidencia de execucao do endpoint no Xano, informada pelo usuario; nao e um teste da interface Reflex.

`pages/reposicao.py` agora consulta o endpoint por `auth_client.list_stock_replenishment`. Um unico GET devolve as duas listas; cada envelope usa `items`, `curPage`, `perPage` e `itemsTotal`. A paginacao e mantida independentemente para cada lista e a quantidade de paginas e derivada de `itemsTotal` e `perPage`, pois o contrato nao retorna `pageTotal`. A unidade e exibida junto ao saldo e ao minimo. A situacao vem de `situacao_estoque`; os campos da solicitacao vem somente da lista `compra_ja_solicitada`.

Antes da consulta, a sessao precisa estar validada e os grants `stock.read` e `purchase_request.read` precisam estar presentes. O grant `purchase_request.create` controla somente a disponibilidade do rascunho. A leitura e armazenada no `SessionReadCache`, isolada pelo fingerprint da sessao, escopo e parametros, com TTL configuravel de 15 segundos por padrao. Alternar abas nao faz GET; abrir a pagina dentro do TTL pode reutilizar o resultado. Paginar, expirar o cache ou tentar novamente apos erro pode fazer uma nova chamada, sempre pelo coordenador existente.

Uma falha nunca e convertida em lista vazia. HTTP 401 limpa o estado e encerra a sessao; 403 bloqueia a visualizacao sem reaproveitar linhas privadas; 404 indica integracao indisponivel; erros temporarios podem preservar uma resposta em cache identificada como desatualizada, mas bloqueiam a abertura do formulario. Nao existe POST no fluxo: `Enviar pedido` continua desabilitado e sem handler.

Os testes locais com mocks verificam mapeamento das duas listas, metadados de pagina, uma chamada para carregar ambas, alternancia de abas sem chamada adicional, isolamento por sessao, grants, estados vazios/erro, 401/403/429, recuperacao manual, situacao de estoque, unidade, quantidade fracionaria e ausencia de escrita. Esses testes nao chamam o Xano e nao comprovam o comportamento visual. Ainda e necessaria validacao manual no navegador com uma sessao Reflex que possua ambos os grants, incluindo uma resposta real 401/403 se a conta de teste nao possuir os dois grants. O POST de compra continua indisponivel e nao foi publicado nem chamado.

## Atualizacao do resumo de estoque do Dashboard (2026-10-19)

O usuario informou que `GET /stock/insufficient_summary` foi publicado no workspace 152211, branch `v1`, mas o Run & Debug retornou `ERROR_FATAL: Unable to locate var: item.quantidade_disponivel` em uma etapa `Conditional`. Esse relato substitui a observacao anterior de que o endpoint ainda nao havia sido publicado; nao comprova que a consulta esteja funcional.

Na versao local, `item` e declarado pelo `each as $item` dentro do `foreach ($insufficient_page.items)`, a condicao esta dentro desse bloco, as referencias usam o mesmo alias e a projecao da consulta inclui `items.quantidade_disponivel`. O filtro de contagem e o da lista paginada sao iguais; a consulta de contagem retorna o total global e nao consulta solicitacoes de compra. A validacao MCP local passou sem avisos. Portanto, a inspecao local nao encontrou a referencia fora de escopo nem o campo ausente da projecao; nao era possivel atribuir a causa do erro a uma linha local especifica sem comparar o Xano publicado ou obter a estrutura efetivamente iterada no runtime.

O preview seletivo foi tentado somente para `api/inventory_stock/stock_insufficient_summary_get.xs`, mas a CLI terminou com `uv_os_get_passwd returned ENOMEM`; nenhum push foi executado e a diferenca entre o arquivo local e o publicado continuava sem verificacao. O teste estrutural local protege o pareamento entre alias do loop, campos projetados e leituras no corpo do loop, mas nao substitui Run & Debug. A flag `NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED` permanece desativada; o Dashboard continua usando o endpoint antigo.

## Ajuste da paginacao do resumo do Dashboard (2026-10-19)

O diagnostico da IA do Xano identificou que a consulta de alertas usava `metadata: false`, que retorna o array sem o envelope `items`, enquanto o codigo percorria `$insufficient_page.items`. A hipotese foi confirmada no arquivo local. A consulta agora usa `totals: true`, no padrao dos endpoints de Estoque e Reposicao, mantendo o foreach em `.items` e os campos da projecao. O `itemsTotal` da resposta do Dashboard continua vindo exclusivamente de `$insufficient_total`, calculado pela consulta global separada; o total da pagina nao substitui essa contagem.

O filtro, a autorizacao `stock.read`, a consulta explicita de saldo ausente, o limite padrao de cinco alertas e as tres consultas internas (verificacao de saldo ausente, contagem global e pagina de alertas) foram preservados. Nao ha consulta por Produto nem acesso a `purchase_request`. A flag `NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED` segue desativada. A correcao local sera validada por MCP e testes, mas exige novo Run & Debug no Xano antes de habilitar o Dashboard. O preview de publicacao deve incluir somente `api/inventory_stock/stock_insufficient_summary_get.xs`; nenhum push esta autorizado nesta etapa.

## Execucao real do resumo insuficiente no Xano (2026-10-19)

O usuario confirmou que o endpoint corrigido foi publicado no workspace 152211, branch `v1`, e executado com sucesso no Run & Debug. Resultado informado: `itemsTotal` 6, `curPage` 1, `perPage` 5, cinco elementos em `items`, dos quais quatro tinham `situacao_estoque` `sem_estoque` e um tinha `situacao_estoque` `abaixo_minimo`. O JSON bruto nao foi fornecido nesta confirmacao, portanto esses nomes sao conferidos contra a resposta definida no XanoScript local e os campos exigidos pelo parser, nao por inspecao independente do payload exibido no Run & Debug.

O parser do cliente usa as chaves de envelope `items`, `itemsTotal`, `curPage` e `perPage`. O projetor do Dashboard usa `itemsTotal` como total global e le de cada item `product_id`, `codigo`, `nome`, `unidade_medida`, `quantidade_disponivel`, `estoque_minimo` e `situacao_estoque`; a interface traduz esses dados apenas na apresentacao. A paginacao requisitada continua em `page=1` e `per_page=5`. A autorizacao do endpoint permanece `stock.read` e o carregador nao exige `purchase_request.read` para esse resumo.

A ativacao e somente por variavel de ambiente do processo local. Nao foi alterado `.env` nem configuracao de outros ambientes. A contagem e os alertas agora podem ser verificados no navegador local; isso ainda nao e evidencia de validacao visual nesta Change. O tratamento de falhas, a preservacao do cache e a ausencia de retry automatico permanecem cobertos por testes simulados; o usuario deve confirmar a estabilidade visual e os tres GETs de dados na carga fria.


## Integracao do indicador de solicitacoes (2026-10-19)

O usuario confirmou a publicacao de `GET /purchase_requests/summary` no workspace 152211, branch `v1`, e uma execucao real no Run & Debug com a resposta exata `{"solicitacoes_abertas": 0}`. Isso comprova o contrato e o caso vazio no Xano, informado pelo usuario. A validacao do valor positivo e do comportamento visual ainda e local/simulada; nao foi inventada uma contagem positiva nem uma inspecao no navegador.

`XanoClient.get_purchase_requests_summary` consulta `/purchase_requests/summary` pelo grupo Inventory Stock e valida que a resposta seja objeto com `solicitacoes_abertas` do tipo inteiro exato e nao negativo. Null, texto, boolean, decimal, valor negativo, campo ausente e resposta nao objeto sao rejeitados como erro de contrato; nenhum e convertido em zero.

O Dashboard consulta essa fonte somente quando a sessao validada passa por `AuthState.has_permission("purchase_request.read")`; o bypass administrativo existente continua vindo desse metodo. Sem o grant, o GET nao ocorre, o card mostra `Sem acesso` e a cache desse endpoint/sessao e invalidada, sem alterar o carregamento dos outros indicadores. Um 401 segue o tratamento central de sessao. Um 403 limpa somente o valor do indicador e informa falta de autorizacao no proprio card, sem banner ou retry global; a tela nao repete automaticamente essa consulta enquanto o erro de autorizacao persistir. Um 429 usa o cooldown compartilhado, nao e repetido automaticamente e pode preservar apenas o resumo anterior da mesma sessao como dado desatualizado.

O card reutiliza o mesmo componente e a mesma posicao, espacamento, icone, tipografia, cores e borda dos cards existentes. O detalhe normal e `Solicitacoes em andamento`; os estados sem acesso, carregamento, indisponibilidade, erro e cache desatualizada nao exibem zero ficticio.

A leitura usa `SessionReadCache` com a chave de escopo `dashboard:purchase_request.read`, endpoint `GET /purchase_requests/summary`, fingerprint da sessao e parametros vazios. O TTL e o operacional existente (`DASHBOARD_OPERATIONAL_TTL`, 15 segundos por padrao); grants nao sao armazenados nessa cache. O endpoint foi incluido na lista comum de invalidacao executada apos escrita nao-GET bem-sucedida por `_inventory_request`, para que futuras operacoes de solicitacoes que usem esse cliente invalidem o resumo. Nenhum endpoint de escrita foi criado ou chamado.

Com permissao, a carga fria faz quatro GETs de dados: Produtos, resumo de estoque, Movimentacoes e resumo de solicitacoes. Sem `purchase_request.read`, permanece em tres. Uma eventual validacao de `/auth/me` e adicional. Os testes com mocks cobrem contagens zero/positiva e valores invalidos, bypass administrativo, ausencia de grant, 401/403/429, independencia dos outros cards, quatro versus tres chamadas, cache por sessao, expiracao e invalidacao apos escrita. Nenhum teste local chama o Xano.

A tarefa 2.4 foi concluida com o endpoint publicado e a resposta real informada, integracao local e verificacoes automatizadas. A cobertura geral da tarefa 4.2 e a validacao visual da tarefa 4.4 continuam pendentes. Ainda e necessario abrir o Dashboard no navegador com uma sessao autorizada e confirmar o valor, a descricao, o estado sem grant, a estabilidade apos erro e as chamadas no painel Network. `Enviar pedido` continua desabilitado; nenhum POST foi adicionado ou habilitado.

## Fase 2 de e-mail — limite do frontend

A preparacao da outbox e do dispatcher ocorre exclusivamente no backend Xano e esta documentada em `backend-solicitacoes-compras`. Reflex continua sem chave, chamada direta ao Resend ou envio de mensagens. O formulario existente coleta o destinatario sob a flag ja aprovada e a API antiga continua sem acionar entrega. Estados de entrega individuais nao sao mostrados como confirmados na interface nesta fase; a mensagem de sucesso da solicitacao nao afirma que o e-mail foi enviado. Nenhum layout, fluxo de criacao/cancelamento, cache ou endpoint frontend foi alterado nesta etapa.

## Aceitacao manual do indicador de estoque insuficiente (2026-11-16)

O usuario confirmou que acessou o Dashboard autenticado com `NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED=true` definido somente no processo local. Informou que o indicador de estoque insuficiente apareceu corretamente, que a contagem estava coerente e que nao houve erros visiveis. A flag permanece `false` por padrao no codigo; nao houve alteracao de configuracao persistente. Esta e uma aceitacao manual informada pelo usuario, sem captura de tela ou log independente. Em conjunto com o contrato local e a evidencia anterior de execucao do endpoint no Xano informada pelo usuario, atende ao criterio da tarefa 2.3 de integrar o indicador com produtos ativos zerados ou abaixo do minimo. Nao se afirma que cada estado de erro, autorizacao negada ou caso-limite foi exercitado individualmente.

## Revisao de evidencias das tarefas 4.4, 4.5 e 5.4 (2026-11-16)

Esta revisao corrige as tarefas 4.4, 4.5 e 5.4 para pendentes porque as evidencias disponiveis nao cobrem todos os seus criterios. Para 4.4, ha a aceitacao manual do indicador do Dashboard descrita acima e o relato anterior do ciclo de criacao/cancelamento; nao ha evidencia suficiente aqui para afirmar a validacao visual completa das duas listas, do formulario e do acompanhamento com todos os grants e estados previstos. Para 4.5, os relatos existentes cobrem criacao e cancelamento da solicitacao ID 2 e recebimento parcial/concluido da solicitacao #12, mas nao comprovam o fluxo de rejeicao nem todas as invariantes de historico, liberacao de produto e ausencia de alteracao indevida de saldo/movimentacoes. Para 5.4, o codigo e testes locais documentam o modo legado e o modo com destinatario; nao ha confirmacao manual registrada dos tres cenarios exigidos apos publicacao do POST de transicao: cliente legado sem campo, formulario habilitado com destinatario persistido e pedido antigo com `NULL`. Ausencia dessas evidencias nao confirma falha funcional. A flag de e-mail permanece uma configuracao local e nenhum envio e afirmado por esta revisao. Nao foram realizadas novas tentativas para essas tres tarefas neste ciclo, conforme decisao do usuario.
