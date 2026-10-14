# Especificação: perfis e permissões

## ADDED Requirements

### Requirement: Consulta administrativa real

A tela `/perfis` MUST exigir autenticação e perfil Líder. Ela MUST carregar perfis, catálogo de permissões e matriz de grants do `GET /permissions`, sem exibir dados fictícios. O Xano MUST continuar exigindo autorização `administrator` na consulta.

#### Scenario: Líder abre a página
- **WHEN** o Líder abre `/perfis`
- **THEN** os nomes dos perfis e os códigos disponíveis vêm da resposta real do Xano

#### Scenario: Perfil sem acesso
- **WHEN** Almoxarife ou Auxiliar tenta abrir a página ou chamar as APIs administrativas
- **THEN** a rota é bloqueada e o Xano recusa a operação

### Requirement: Edição de grants com revisão

Para `stockkeeper` e `read_only`, a tela MUST distinguir permissões salvas das marcações em edição. O salvamento MUST enviar a lista final de códigos do catálogo e a `permission_revision` ao PATCH existente. Depois do sucesso, MUST refletir os grants persistidos. Conflito de revisão MUST exigir nova revisão dos dados antes de outra tentativa.

#### Scenario: Alteração local
- **WHEN** o Líder marca ou desmarca uma permissão
- **THEN** apenas o rascunho local muda até clicar em Salvar

#### Scenario: Troca de perfil com rascunho
- **WHEN** o Líder troca de perfil com alterações não salvas
- **THEN** o rascunho é descartado e os grants salvos do novo perfil são exibidos

#### Scenario: Salvar
- **WHEN** o Líder salva códigos válidos para Almoxarife ou Auxiliar
- **THEN** o Xano substitui os grants, incrementa a revisão e registra a auditoria existente

### Requirement: Líder protegido

O perfil `administrator` MUST aparecer como acesso integral somente para consulta. A interface MUST bloquear a edição e o backend MUST continuar recusando alteração dos grants desse perfil.

#### Scenario: Tentar alterar Líder
- **WHEN** alguém tenta editar `administrator`
- **THEN** nenhuma alteração é aceita

### Requirement: Menu condicionado às permissões reais

A resposta autenticada de `/auth/me` MUST incluir o código do perfil e os códigos de permissões efetivos do usuário. Para `administrator`, os códigos MUST representar acesso integral ao catálogo atual. Para os demais perfis, os códigos MUST corresponder aos grants persistidos no Xano. A sidebar MUST renderizar Produtos com `product.read`, Categorias com `category.read`, Fornecedores com `supplier.read`, Estoque com `stock.read`, Histórico com `movement.read`, Relatórios com `report.read`, Entradas com `stock.entry` e Saídas com `stock.exit`. Usuários e Perfis e permissões MUST aparecer apenas para `administrator`. A verificação visual MUST acompanhar os grants efetivos e MUST NOT substituir a autorização do backend.

#### Scenario: Usuário sem permissão de leitura
- **WHEN** o usuário não possui `product.read`
- **THEN** Produtos não aparece na navegação
- **AND** o acesso direto continua protegido pela autorização do backend

#### Scenario: Auxiliar sem permissões de cadastros
- **WHEN** Auxiliar não possui `product.read`, `category.read` nem `supplier.read`
- **THEN** Produtos, Categorias e Fornecedores não aparecem na navegação

#### Scenario: Permissão concedida e sessão atualizada
- **WHEN** `product.read` é concedida ao perfil do usuário
- **AND** o usuário inicia uma nova sessão ou restaura a sessão
- **THEN** Produtos aparece na navegação

#### Scenario: Estoque sem Histórico
- **WHEN** Auxiliar possui `stock.read`, mas não possui `stock.entry` nem `stock.exit`
- **AND** não possui `movement.read`
- **THEN** Estoque aparece e Histórico não aparece
- **AND** Entradas e Saídas não aparecem

### Requirement: Granularidade independente para Histórico e Relatórios

O Histórico MUST ser controlado por `movement.read`; Relatórios MUST ser controlado por `report.read`; Estoque MUST continuar controlado por `stock.read`. `GET /movement_users` MUST exigir `movement.read`. `GET /movements_summary` e as opções mínimas de filtro MUST exigir `report.read`. Como `GET /movements` é compartilhado, MUST autorizar `movement.read` OU `report.read`. Nenhum endpoint de relatório MUST exigir `product.read` ou `supplier.read` apenas para carregar filtros. APIs sem permissão MUST continuar recusando o acesso.

#### Scenario: Perfil sem movement.read
- **WHEN** o perfil não possui `movement.read`
- **THEN** Histórico não aparece
- **AND** a API exclusiva do Histórico recusa o acesso

#### Scenario: Histórico separado do estoque
- **WHEN** o perfil possui `stock.read` mas não possui `movement.read`
- **THEN** Estoque aparece
- **AND** Histórico não aparece

#### Scenario: Perfil com report.read e sem stock.read
- **WHEN** o perfil possui `report.read` mas não possui `stock.read`
- **THEN** Relatórios continua acessível pelos contratos protegidos por `report.read`
- **AND** as opções de filtro e `GET /movements` funcionam sem grants operacionais de produto ou fornecedor

#### Scenario: Relatório e histórico autorizam endpoint compartilhado
- **WHEN** o perfil possui `report.read` ou `movement.read`
- **THEN** `GET /movements` autoriza a consulta compartilhada
- **AND** somente `report.read` autoriza resumo e opções de filtro de Relatórios

#### Scenario: Grants iniciais preservam acesso
- **WHEN** os grants forem migrados para separar `stock.read`
- **THEN** perfis que atualmente possuem `stock.read` recebem inicialmente `movement.read` e `report.read`
- **AND** perfis sem `stock.read` não recebem esses grants por inferência
- **AND** nenhuma execução de seed ou migração ocorre nesta change

#### Scenario: Rotas administrativas
- **WHEN** o usuário não possui o perfil `administrator`
- **THEN** Usuários e Perfis e permissões não aparecem
- **AND** as APIs administrativas continuam recusando a solicitação
