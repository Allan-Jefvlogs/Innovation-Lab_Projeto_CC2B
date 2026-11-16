# Perfil Compras e gerenciamento de solicitações

## ADDED Requirements

### Requirement: Navegar no detalhe sem confundir paginação do histórico

A interface MUST oferecer botão secundário Voltar com seta à esquerda para /compras. A paginação do histórico MUST ficar oculta quando houver zero ou uma página e MUST mostrar Anterior, Próxima e página atual/total quando houver mais de uma. MUST NOT navegar automaticamente entre pedidos nem alterar paginação da listagem principal.

#### Scenario: Histórico de uma página
- **WHEN** o histórico possui até uma página de eventos
- **THEN** ambos os botões de paginação ficam ocultos

#### Scenario: Histórico com várias páginas
- **WHEN** o histórico possui mais de uma página
- **THEN** os controles e indicador de páginas são exibidos e alteram apenas a página do histórico do mesmo pedido

### Requirement: Delimitar a entrega acadêmica a um operador de compras

A entrega MUST ser documentada como uso acadêmico com um único operador alterando compras por vez. MUST preservar permissões, isolamento, validações de transição e histórico. MUST NOT afirmar proteção contra atualizações simultâneas, implementar versão/reivindicação/Lock nesta etapa ou exigir testes avançados de concorrência como condição de conclusão. A validação funcional no Xano Free MUST preceder a demonstração.

#### Scenario: Comparação simples do estado esperado

- **WHEN** o pedido é consultado para uma alteração sequencial
- **THEN** o Xano compara o status lido com status_esperado antes da edição nativa
- **AND** a documentação informa que uma alteração simultânea entre leitura e gravação não está protegida por essa comparação.

### Requirement: Restringir o perfil Compras ao módulo de compras

O Xano MUST associar o perfil `compras` somente aos grants aprovados do domínio de solicitações. A interface MUST direcionar esse perfil para `/compras` após autenticação validada e MUST impedir acesso às demais rotas operacionais. O backend MUST continuar exigindo grants por endpoint.

#### Scenario: Login e URL direta

- **WHEN** usuário do perfil Compras conclui login ou restaura sessão válida
- **THEN** o destino é `/compras`, salvo quando a troca inicial de senha for obrigatória
- **WHEN** ele acessa diretamente Dashboard, Reposição ou outra rota operacional fora de Compras
- **THEN** o guard o redireciona sem carregar dados da rota negada
- **AND** endpoints dessas áreas negam acesso por ausência dos grants correspondentes

#### Scenario: Perfil sem privilégios gerais

- **WHEN** o perfil Compras é provisionado
- **THEN** recebe `purchase_request.read`, `purchase_request.manage` e `purchase_request.status.update`
- **AND** não recebe `administrator`, `stock.read`, `purchase_request.create` nem grants das áreas proibidas
- **AND** nenhum usuário recebe o perfil automaticamente

### Requirement: Consultar solicitações e histórico conforme escopo

O backend MUST exigir `purchase_request.read` para listagem e detalhe. Leitura isolada MUST limitar pedidos ao próprio solicitante; leitura combinada com `purchase_request.manage` ou bypass administrativo MUST permitir escopo global. A paginação, os filtros, o histórico e a projeção pública MUST ser preservados.

O resumo `GET /purchase_requests/summary` MUST respeitar o mesmo escopo. A consulta de Reposição MUST manter a visão global dos produtos com estoque insuficiente, mas MUST NOT expor ID, quantidade, urgência, status ou data de pedidos de outros solicitantes a quem não possui `purchase_request.manage` ou bypass administrativo. O backend MUST devolver esses campos como `null` e a marca booleana `solicitacao_detalhes_disponiveis=false` nos pedidos restritos, preservando produtos, totais e paginação. O consumidor MUST aceitar respostas legadas sem a marca, tratar explicitamente a restrição e MUST NOT reutilizar dados de cache global em uma leitura própria.

#### Scenario: Compras consulta todos e leitor consulta próprios

- **WHEN** usuário Compras consulta lista ou detalhe de um pedido de outro solicitante
- **THEN** recebe os campos públicos e histórico correspondentes
- **WHEN** usuário possui somente `purchase_request.read`
- **THEN** vê apenas pedidos próprios e não obtém detalhe de outro solicitante

#### Scenario: Reposição sem acesso gerencial

- **WHEN** usuário com `stock.read` e `purchase_request.read`, sem `purchase_request.manage`, consulta a Reposição
- **THEN** pode identificar produtos insuficientes e a existência de solicitação ativa para evitar duplicidade
- **AND** não recebe campos do pedido ativo de outro solicitante

#### Scenario: Compatibilidade e mudança de acesso

- **WHEN** a API retorna uma linha restrita com campos de pedido nulos
- **THEN** a interface mantém o produto e o saldo visíveis, apresenta detalhes restritos e não permite abrir cancelamento pela linha
- **WHEN** o escopo de leitura da sessão muda de global para próprio
- **THEN** linhas e cache do escopo anterior não são reutilizados, inclusive em falha temporária da consulta
- **AND** uma chave de escrita ambígua não é descartada por essa mudança de leitura

### Requirement: Salvar somente transições gerenciais permitidas

O backend MUST exigir autenticação e `purchase_request.status.update` específico. O seletor MUST oferecer somente a próxima transição permitida e MUST salvar automaticamente, mostrando carregamento, sucesso ou erro sem atualizar otimisticamente o estado confirmado.

`purchase_request.manage` sozinho MUST NOT autorizar a mudança de status. O bypass administrativo já existente no autorizador central permanece.

#### Scenario: Sequência aprovada

- **WHEN** o estado atual é `aberta`, `em_analise`, `aprovada` ou `em_compra`
- **THEN** as únicas escolhas são, respectivamente, `em_analise`; `aprovada` ou `rejeitada`; `em_compra`; `aguardando_recebimento`
- **AND** `recebimento_parcial` e `concluida` nunca são escolhas manuais

#### Scenario: Estado mudou ou escrita falhou

- **WHEN** `status_esperado` difere do estado relido antes da edição, a transição é inválida ou uma gravação de banco falha
- **THEN** o endpoint não confirma a nova situação nem grava histórico de sucesso
- **AND** a interface mantém o último status confirmado pelo servidor e permite reconciliação manual sem retry automático de escrita

#### Scenario: Gestor sem grant de status

- **WHEN** um usuário possui `purchase_request.read` e `purchase_request.manage`, mas não `purchase_request.status.update`
- **THEN** o Xano nega a alteração de status e não grava evento no histórico

#### Scenario: Rejeição encerra a solicitação

- **WHEN** uma solicitação `em_analise` é rejeitada por ator autorizado
- **THEN** o backend grava `rejeitada`, limpa `active_product_id`, registra data de encerramento e insere evento `rejeitada` com ator autenticado
- **AND** não altera saldo nem cria movimentação ou evento na Auditoria geral

#### Scenario: Gestores autorizados acessam a área sem mudar a página inicial

- **WHEN** um administrador ou gestor com `purchase_request.read` e `purchase_request.manage` acessa `/compras` ou um detalhe
- **THEN** o guard e a página permitem a consulta conforme a autorização do backend
- **AND** a página inicial desses perfis continua `/dashboard` e o menu oferece Compras solicitadas
- **AND** leitura sem `manage` não concede acesso à área gerencial, enquanto o perfil Compras permanece restrito à sua área

### Requirement: Registrar mudança e histórico na mesma transação

O endpoint de status MUST usar db.get/db.edit/db.add nativos para reler o pedido, validar a transição, atualizar o pedido e inserir o histórico dentro da mesma `db.transaction`, sem capturar falha de escrita de modo que confirme atualização parcial. MUST NOT depender de db.direct_query. A garantia de rollback em runtime MUST ser validada separadamente antes de ser declarada comprovada; teste avançado com falha induzida não é pré-requisito da entrega acadêmica.

#### Scenario: Falha de histórico

- **WHEN** a inserção do evento de histórico falha após a atualização do pedido
- **THEN** o endpoint não retorna sucesso
- **AND** a transação deve reverter a alteração do pedido, sujeito a confirmação de runtime no Xano

### Requirement: Reutilizar cancelamento e notificações existentes

O cancelamento MUST continuar sujeito às regras do PATCH existente, com justificativa obrigatória e confirmação. Eventos gerenciais MUST alimentar as notificações apenas por registros persistidos em `purchase_request_history`, respeitando o marco de ativação e os grants. MUST NOT enviar e-mails, criar histórico retroativo ou registrar solicitações na Auditoria geral.

#### Scenario: Cancelar e consultar notificações

- **WHEN** Compras cancela pedido `aberta` ou `em_analise` por fluxo confirmado
- **THEN** a rota existente registra `cancelada`, libera o produto e preserva estoque
- **WHEN** um evento `status_alterado` ou `rejeitada` é confirmado e a central de notificações está publicada/ativada
- **THEN** a central o lê do histórico persistido conforme o escopo de cada usuário
