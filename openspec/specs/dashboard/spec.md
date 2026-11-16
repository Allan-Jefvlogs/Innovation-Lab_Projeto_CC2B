# dashboard Specification

## Purpose
Define o comportamento permanente do Dashboard operacional integrado do NexStock, incluindo dados autorizados do Xano, cache, gráfico, notificações e apresentação responsiva.

## Requirements

### Requirement: Resumo operacional usa dados reais e grants

O Dashboard MUST apresentar informações originadas de respostas reais do Xano, podendo reutilizar respostas atuais ou cacheadas segundo o requisito de cache. Os indicadores MUST refletir Produtos ativos, estoque abaixo do mínimo e solicitações de compra abertas conforme os contratos de cada recurso; MUST NOT restaurar cartões antigos de Categorias ou Fornecedores nem exibir valores de protótipo como reais. A contagem de Produtos ativos MUST usar `itemsTotal` da consulta filtrada por ativo. A quantidade de alertas MUST usar a contagem autorizada do recurso de estoque, sem percorrer páginas apenas para contar. O Xano MUST continuar como autoridade de autenticação e autorização.

#### Scenario: Consulta autorizada
- **WHEN** uma sessão validada abre o Dashboard com grants para os recursos exibidos
- **THEN** cada indicador mostra a contagem derivada da resposta real do recurso correspondente
- **AND** as movimentações recentes e os alertas exibem apenas registros retornados pelo Xano.

#### Scenario: Resposta atual ou cacheada
- **WHEN** o Dashboard apresenta uma resposta obtida anteriormente do Xano que ainda está no cache
- **THEN** os valores continuam identificáveis como dados de origem real
- **AND** quando a resposta estiver potencialmente desatualizada, a interface informa esse estado conforme o requisito de falhas.

#### Scenario: Recurso sem grant
- **WHEN** a sessão não possui o grant de leitura de um recurso
- **THEN** o Dashboard não consulta esse recurso
- **AND** informa indisponibilidade por permissão sem representar a ausência de acesso como zero.

### Requirement: Falhas permanecem distintas de resultados vazios

O Dashboard MUST distinguir carregamento, resposta válida vazia, falta de permissão, resposta atual, resposta em cache e falha de consulta. A existência de cache não transforma uma resposta anterior em atualização confirmada. Dados cacheados exibidos após falha temporária MUST ser identificados como potencialmente desatualizados e MUST NOT autorizar nem confirmar operações. Falhas MUST NOT ser convertidas em contagens, listas ou séries vazias/zero que pareçam respostas válidas.

#### Scenario: Resposta válida sem registros
- **WHEN** o Xano confirma uma resposta válida sem registros para uma fonte
- **THEN** a interface mostra o estado vazio correspondente, distinto de erro.

#### Scenario: Falha temporária com cache
- **WHEN** uma consulta falha temporariamente e há dados anteriores da mesma sessão
- **THEN** a interface pode preservá-los com indicação de possível desatualização
- **AND** a falha não é apresentada como contagem zero nem como confirmação de uma operação.

#### Scenario: Falha sem cache utilizável
- **WHEN** uma fonte falha sem dados anteriores utilizáveis
- **THEN** a interface mostra estado indisponível e não inventa valores.

#### Scenario: Cache potencialmente desatualizado
- **WHEN** uma consulta atual falha, mas há uma resposta anterior da mesma sessão
- **THEN** a interface pode manter essa resposta com indicação explícita de possível desatualização
- **AND** não a apresenta como confirmação de que os dados continuam atuais.

### Requirement: Cache isolado por sessão e invalidado após escrita

Leituras do Dashboard MUST usar cache com prazo limitado e chave isolada por identidade/sessão e parâmetros relevantes. Uma troca de identidade MUST NOT reutilizar dados privados de outra sessão. Escrita Xano relevante confirmada MUST invalidar as entradas do Dashboard daquela sessão; falha de escrita MUST NOT invalidar nem atualizar o cache como se a operação tivesse sido concluída. O Dashboard MUST NOT implementar polling ou retries automáticos e MUST respeitar o coordenador e o cooldown de requisições existente.

#### Scenario: Leitura repetida dentro do prazo
- **WHEN** a mesma sessão solicita novamente uma fonte ainda válida no cache, com os mesmos parâmetros
- **THEN** o Dashboard reutiliza o resultado sem consulta redundante.

#### Scenario: Escrita confirmada
- **WHEN** uma operação relevante de escrita retorna confirmação do Xano
- **THEN** as entradas de cache afetadas da sessão são invalidadas para que a próxima leitura busque dados atuais.

#### Scenario: Escrita falha ou resultado não confirmado
- **WHEN** a operação de escrita falha ou não é confirmada
- **THEN** o Dashboard não atualiza os dados como sucesso nem invalida o cache como se a escrita tivesse ocorrido.

#### Scenario: Troca de identidade ou limite de requisições
- **WHEN** uma nova identidade abre o Dashboard ou o coordenador detecta rate limit
- **THEN** dados privados da identidade anterior não são reutilizados e não há polling nem retry automático fora do cooldown.

### Requirement: Gráfico de linhas mostra contagens reais por período

O Dashboard MUST manter o gráfico de linhas de entradas e saídas alimentado por movimentações reais. MUST oferecer os períodos de 7 dias (padrão), 30 dias e 12 meses, agrupados no timezone `America/Sao_Paulo`. Cada movimento MUST contar como uma operação; quantidades de unidades diferentes MUST NOT ser somadas. Dias ou meses sem operações só podem receber zero após a agregação completa. A troca de período MUST preservar o restante do Dashboard e a tabela das cinco movimentações recentes, que não fica limitada ao intervalo do gráfico.

#### Scenario: Seleção de período
- **WHEN** o usuário seleciona 7 dias, 30 dias ou 12 meses
- **THEN** o mesmo gráfico de linhas mostra a série real do período correspondente
- **AND** somente a fonte de movimentações é atualizada, respeitando o cache por sessão e período.

#### Scenario: Operações com unidades distintas
- **WHEN** há movimentos de produtos com unidades diferentes no intervalo
- **THEN** cada movimento contribui uma vez para a série de seu tipo e dia/mês, sem somar quantidades físicas.

#### Scenario: Período sem movimentos
- **WHEN** a agregação real do período é concluída sem movimentos em uma data ou mês
- **THEN** essa posição aparece com contagem zero, sem ser confundida com falha ou ausência de autorização.

### Requirement: Notificações refletem eventos persistidos e respeitam o escopo

As notificações MUST derivar de eventos realmente persistidos no histórico de solicitações de compra, após o marco de ativação configurado. Com `purchase_request.read`, o usuário MUST ver somente eventos e detalhes de pedidos próprios; o escopo global MUST exigir também `purchase_request.manage`, preservando o bypass administrativo existente. A mesma política MUST valer para lista, detalhe e histórico, e MUST ser aplicada pelo Xano e respeitada pelos guards e pela navegação Reflex. A leitura MUST ser individual por evento e usuário autenticado; o contador MUST refletir as leituras confirmadas. Eventos de e-mail, eventos retroativos anteriores ao marco e eventos de negócio não persistidos MUST NOT ser apresentados.

#### Scenario: Escopo de leitura próprio ou global
- **WHEN** um usuário consulta notificações
- **THEN** `purchase_request.read` limita notificações, detalhes e histórico aos pedidos em que ele é solicitante
- **AND** a consulta global exige `purchase_request.read` e `purchase_request.manage`, ou o bypass administrativo existente
- **AND** dados de outros solicitantes não são expostos a um usuário sem acesso global.

#### Scenario: Marcar como lida
- **WHEN** o usuário marca uma notificação como lida
- **THEN** a leitura é associada ao evento e ao usuário autenticado
- **AND** a interface atualiza o estado e o contador somente após confirmação do Xano.

#### Scenario: Abrir notificação
- **WHEN** o usuário ativa uma notificação acessível
- **THEN** o Dashboard navega para o detalhe do pedido referenciado pela própria notificação
- **AND** se ainda não estiver lida, tenta uma única marcação de leitura; falha de leitura não bloqueia a navegação nem altera o pedido.

#### Scenario: Carregar páginas adicionais
- **WHEN** o usuário rola próximo ao fim da lista e há outra página
- **THEN** o Dashboard acrescenta a página seguinte sem duplicar eventos nem perder os já carregados
- **AND** bloqueia carregamentos simultâneos e não implementa polling ou retry automático.

### Requirement: Apresentação do Dashboard preserva a composição responsiva

O Dashboard MUST preservar a composição visual operacional aprovada: sidebar fixa de aproximadamente 252 px em desktop, cabeçalho de aproximadamente 78 px, área centralizada de até 1440 px com padding desktop de aproximadamente 38 px, três cartões dos indicadores atuais com larguras iguais, intervalo de 17 px, altura mínima de 131 px e cantos de 17 px, painéis de gráfico e alertas lado a lado, e tabela de movimentações recentes abaixo. O gráfico permanece à esquerda dos alertas, com proporção aproximada de 1,5:0,9 e desenho de aproximadamente 204 px mais 24 px para o eixo temporal. Em viewport estreito, os painéis MUST se reorganizar verticalmente sem rolagem horizontal da página. Seleção de períodos, notificações, estados de erro e dados reais MUST permanecer utilizáveis. As cores globais e tokens MUST ser definidos pela capability separada `identidade-visual`, sem duplicar a paleta neste contrato.

#### Scenario: Desktop
- **WHEN** a sessão autenticada abre o Dashboard em viewport desktop
- **THEN** a composição mantém a hierarquia aprovada e as proporções aproximadas descritas para navegação, cabeçalho, indicadores, gráfico/alertas e movimentações recentes.

#### Scenario: Viewport estreito
- **WHEN** o Dashboard é exibido em viewport estreito
- **THEN** os painéis são empilhados, textos e ações permanecem acessíveis e a página não cria rolagem horizontal.

#### Scenario: Estados de interface
- **WHEN** uma fonte está carregando, vazia, indisponível ou com dados potencialmente desatualizados
- **THEN** a apresentação identifica o estado sem substituir dados reais nem alterar as regras de autorização.

#### Scenario: Composição na resolução desktop de referência
- **WHEN** o Dashboard autenticado é exibido em 1920 × 960
- **THEN** a composição preserva a sidebar, o cabeçalho, os indicadores, o gráfico, os alertas e a tabela conforme as proporções desktop descritas neste requisito.

### Requirement: Saudação usa a identidade autenticada e o horário de São Paulo

O Dashboard MUST mostrar uma saudação baseada no primeiro nome disponível do usuário autenticado e no horário de `America/Sao_Paulo`. MUST NOT inventar um nome quando ele não estiver disponível nem mostrar os textos antigos “VISÃO GERAL DO ESTOQUE” ou “Aqui está o resumo do seu estoque hoje”.

#### Scenario: Saudação autenticada
- **WHEN** uma sessão válida abre o Dashboard
- **THEN** o texto usa Bom dia (05–11), Boa tarde (12–17) ou Boa noite (18–04) em `America/Sao_Paulo`
- **AND** usa o primeiro nome disponível sem inventar nome
- **AND** não mostra “VISÃO GERAL DO ESTOQUE” nem “Aqui está o resumo do seu estoque hoje”.
