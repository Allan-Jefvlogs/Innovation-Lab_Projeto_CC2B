# Spec Delta: identidade visual

## Purpose

Define o tema visual global do NexStock de forma reutilizável e acessível, separado dos requisitos específicos de composição e dados do Dashboard.

## ADDED Requirements

### Requirement: Paleta global centralizada

O sistema MUST centralizar as cores de marca em tokens reutilizáveis e aplicar um tema claro consistente nas páginas existentes. A paleta de referência é verde menta `#BEEADB`, verde sálvia `#8DBAA6`, amarelo pêssego `#F7C683`, rosa pêssego `#F0CBB9` e taupe `#9E8D85`; o sálvia é a cor estrutural principal e os demais tons são acentos moderados com funções semânticas. Esta capability define cores globais, não a disposição específica dos componentes do Dashboard.

#### Scenario: Aplicação da paleta
- **WHEN** uma página existente é renderizada
- **THEN** as cores da interface seguem os tokens globais e a cor sálvia identifica navegação ativa e ações principais
- **AND** fundos de destaque usam tons suaves sem prejudicar a leitura.

### Requirement: Estados visuais acessíveis

Estados positivos, de atenção e de falha MUST permanecer identificáveis por rótulo, ícone ou texto além da cor. Textos e ícones MUST manter contraste legível em fundos claros ou coloridos.

#### Scenario: Situação de estoque
- **WHEN** um produto aparece abaixo do mínimo ou sem estoque
- **THEN** a cor de atenção é acompanhada por rótulo ou ícone que comunica o estado.

#### Scenario: Falha de operação
- **WHEN** uma operação falha
- **THEN** a mensagem de erro é visualmente distinguível e a apresentação não altera o resultado ou comportamento da operação.

### Requirement: Identidade visual preserva funcionamento e responsividade

Atualizações do tema MUST preservar rotas, chamadas, autorização, dados e ações existentes, além de manter as páginas utilizáveis em desktop e viewport estreito.

#### Scenario: Usuário navega por páginas autorizadas
- **WHEN** o usuário navega entre páginas permitidas pelos grants do backend
- **THEN** o tema permanece consistente e as páginas mantêm seus comportamentos e guards.

#### Scenario: Viewport estreito
- **WHEN** uma página é exibida em viewport estreito
- **THEN** o conteúdo continua legível e utilizável sem rolagem horizontal desnecessária.
