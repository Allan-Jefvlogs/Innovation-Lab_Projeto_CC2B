## ADDED Requirements

### Requirement: Exibir resumo real do estoque e das movimentações

A página `/dashboard` MUST apresentar informações derivadas dos endpoints existentes do Xano. MUST NOT exibir contagens, movimentações ou alertas fixos de protótipo como se fossem atuais. Contagens MUST usar metadados paginados quando disponíveis, sem percorrer todas as páginas apenas para contar.

#### Scenario: Sessão com grants aplicáveis abre o resumo

- **WHEN** uma sessão validada com os grants de leitura disponíveis abre `/dashboard`
- **THEN** o sistema consulta Produtos ativos, Categorias, Fornecedores, Estoque abaixo do mínimo e Movimentações recentes pelos endpoints existentes
- **AND** exibe contagens e registros retornados pelo Xano
- **AND** solicita no máximo uma página pequena por recurso

#### Scenario: Sessão sem um grant de leitura

- **WHEN** a sessão validada não possui o grant de um recurso do Dashboard
- **THEN** o frontend não solicita esse recurso nem mostra um número fictício como zero
- **AND** indica que o recurso não está disponível para essa sessão
- **AND** o Xano continua responsável por autorizar cada chamada realizada

### Requirement: Tratar indisponibilidade sem falsificar resultados

A página MUST distinguir carregamento, dados carregados, ausência real de registros e falha de consulta. Falhas MUST NOT ser representadas como uma contagem zero. Dados anteriores eventualmente mantidos após falha temporária MUST ser identificados como potencialmente desatualizados e MUST NOT ser usados para autorizar ou confirmar operações.

#### Scenario: Falha temporária em uma fonte

- **WHEN** uma consulta do Dashboard falha por limite de requisições, conexão ou indisponibilidade do servidor
- **THEN** o erro não é convertido em lista vazia ou contagem zero
- **AND** dados anteriores seguros podem permanecer visíveis com indicação de desatualização
- **AND** uma ação manual pode tentar novamente somente as fontes com falha, respeitando o coordenador e o cooldown

#### Scenario: Cache após escrita ou troca de sessão

- **WHEN** uma escrita Xano é confirmada ou uma sessão diferente abre o Dashboard
- **THEN** os dados em cache da sessão atual são invalidados após sucesso da escrita ou permanecem isolados por impressão digital da sessão
- **AND** uma falha de escrita não atualiza nem invalida os dados como se a mutação tivesse sido concluída
