## MODIFIED Requirements

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
