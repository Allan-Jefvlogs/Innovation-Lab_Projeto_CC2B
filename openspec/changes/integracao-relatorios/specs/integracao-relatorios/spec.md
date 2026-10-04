# Requisitos da integração de Relatórios

## ADDED Requirements

### Requirement: Filtrar relatório operacional

A rota `/relatorios` MUST permitir filtros opcionais de data inicial, data final, tipo, Produto e Fornecedor e MUST combiná-los na listagem detalhada. Datas ausentes MUST permanecer ausentes, sem período padrão oculto. A data inicial MUST representar o início do dia e a final o fim do dia no fuso `America/Sao_Paulo`. Uma data inicial posterior à final MUST ser rejeitada antes da requisição.

#### Scenario: Aplicar filtros combinados

- **WHEN** o usuário aplicar período, tipo, Produto e Fornecedor
- **THEN** a tabela mostra somente movimentações que atendem a todos os filtros informados
- **AND** a tabela retorna à primeira página.

#### Scenario: Omitir período

- **WHEN** ambas as datas estiverem vazias
- **THEN** a consulta não envia filtro temporal e apresenta o conjunto geral disponível.

### Requirement: Exibir indicadores corretos

Os cards MUST mostrar total de registros de movimentação, soma da quantidade de entradas, soma da quantidade de saídas, contagem atual de produtos abaixo do mínimo e contagem atual de produtos sem estoque. Totais de movimento MUST considerar todo o conjunto dos filtros temporais, Produto e Fornecedor e MUST NOT depender da página da tabela. O filtro de tipo MUST afetar a tabela, mas não remover uma das duas somas dos cards. Situação do estoque MUST vir de `GET /stock_summary`.

#### Scenario: Paginar tabela sem alterar totais

- **WHEN** a tabela mudar de página
- **THEN** os indicadores continuam representando o conjunto filtrado completo.

#### Scenario: Fornecedor limita agregado

- **WHEN** um Fornecedor for selecionado
- **THEN** tabela e totais de movimento incluem somente registros com o `supplier_id` selecionado.

### Requirement: Exibir movimentos reais paginados

A tabela MUST usar os dados enriquecidos de `GET /movements`, manter paginação real e exibir Data/Hora, Tipo, Código, Produto, Quantidade, Usuário, Fornecedor e Motivo. Fornecedor ausente MUST ser mostrado como `—`. O carregamento MUST NOT realizar uma chamada por movimentação.

#### Scenario: Lista vazia

- **WHEN** não houver movimentações para os filtros selecionados
- **THEN** o sistema apresenta uma mensagem de estado vazio sem tratar a resposta como erro.

### Requirement: Resumo de movimentações autorizado

O Xano MUST expor resumo agregado em endpoint autenticado protegido por `stock.read`, com total de registros e somas das quantidades de entrada e saída, aplicando data inicial, data final, Produto e Fornecedor ao conjunto completo. O resumo MUST NOT ser calculado apenas com a página atual. Nenhuma permissão de escrita ou grant novo será introduzido.

#### Scenario: Agregar conjunto filtrado

- **WHEN** um usuário autenticado com `stock.read` consulta o resumo
- **THEN** recebe totais de ambos os tipos de movimentação para todos os registros correspondentes aos filtros.

### Requirement: Tratar sessão e erros

Relatórios MUST reutilizar a sessão atual. 401 MUST seguir o fluxo de login, 403 MUST exibir falta de permissão, entradas inválidas MUST receber mensagem específica e falhas inesperadas MUST exibir mensagem genérica sem traceback.

#### Scenario: Erro de autorização

- **WHEN** o backend responde 401 ou 403
- **THEN** o sistema redireciona para login no caso 401 e informa falta de permissão no caso 403.

### Requirement: Manter exportação futura fora desta versão

A primeira versão MUST NOT implementar exportação PDF, Excel ou CSV.

#### Scenario: Ações da tela

- **WHEN** a tela de Relatórios é exibida
- **THEN** não são apresentados controles de exportação PDF, Excel ou CSV.
