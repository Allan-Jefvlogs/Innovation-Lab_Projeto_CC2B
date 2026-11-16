## ADDED Requirements

### Requirement: Gráfico real com períodos selecionáveis
O Dashboard DEVE (MUST) apresentar o painel “Movimentação do estoque” com contagens reais de operações de entrada e saída, linhas em verde sálvia e amarelo pêssego, eixo temporal, legenda e linhas de referência discretas. O usuário DEVE (MUST) poder selecionar 7 dias, 30 dias ou 12 meses, com 7 dias como padrão.

#### Scenario: Exibição dos dados reais
- **WHEN** o painel é exibido com dados reais disponíveis para o período selecionado
- **THEN** o gráfico apresenta as contagens de entradas e saídas daquele período, sem somar quantidades de unidades diferentes
- **AND** dias ou meses sem operações são representados conforme o contrato de dados, sem valores demonstrativos
- **AND** a largura e a altura do gráfico se adaptam à tela sem criar rolagem horizontal no Dashboard.

#### Scenario: Seleção de período
- **WHEN** o usuário seleciona 7 dias, 30 dias ou 12 meses
- **THEN** o mesmo gráfico de linhas exibe a série real do período selecionado e destaca a opção ativa
- **AND** a seleção não altera os indicadores nem os registros de movimentações recentes.

#### Scenario: Disposição em desktop
- **WHEN** a página é exibida em 1920 × 960
- **THEN** a barra superior tem aproximadamente 78 px e a sidebar aproximadamente 252 px
- **AND** o conteúdo é centralizado com largura máxima de 1440 px e padding desktop de 38 px
- **AND** os três indicadores têm larguras iguais e intervalos de 17 px
- **AND** o gráfico tem aproximadamente 204 px de desenho e 24 px para os dias, à esquerda dos alertas, com a tabela de movimentações abaixo dos dois painéis.
- **AND** os cartões têm altura mínima de 131 px, cantos de 17 px e fundos suaves, sem copiar os números demonstrativos do protótipo.

### Requirement: Separação entre apresentação e dados do estoque
O gráfico NÃO DEVE (MUST NOT) alterar indicadores, movimentações, estoque, relatórios ou permissões. A série DEVE (MUST) permanecer separada da lógica de escrita do estoque e ser recebida pelo componente de apresentação; a leitura e o cache devem respeitar os contratos existentes do Dashboard.

#### Scenario: Abertura do Dashboard
- **WHEN** o Dashboard carrega os indicadores, a série do período padrão e os registros reais existentes
- **THEN** o gráfico não deriva totais da lista limitada de movimentações recentes
- **AND** os estados de autorização, carregamento, falha e cache existentes são preservados.

### Requirement: Identidade visual e navegação existentes
As páginas existentes DEVEM (MUST) compartilhar a paleta sálvia, menta, pêssego e taupe, mantendo textos legíveis, estados semânticos e rotas, incluindo Auditoria.

#### Scenario: Navegação entre páginas
- **WHEN** o usuário navega entre as telas permitidas pela sessão
- **THEN** menu, cabeçalho, botões e tabelas mantêm o padrão visual compartilhado
- **AND** a consulta de Auditoria continua em `/auditoria`, sem reintroduzir a antiga consulta `/movimentacoes`.
