# integracao-relatorios Specification

## Purpose
TBD - created by archiving change integracao-relatorios. Update Purpose after archive.

## Requirements

### Requirement: Filtrar relatório operacional

A rota `/relatorios` MUST permitir filtros opcionais de data inicial, data final, tipo, Produto e Fornecedor, combinados na listagem detalhada. Datas ausentes MUST permanecer ausentes, sem período padrão oculto. A data inicial MUST representar o início do dia e a final o fim do dia no fuso `America/Sao_Paulo`. Uma data inicial posterior à final MUST ser rejeitada antes da requisição. Os filtros editáveis somente são aplicados ao acionar Aplicar filtros.

#### Scenario: Aplicar filtros combinados

- **WHEN** o usuário aplica período, tipo, Produto e Fornecedor
- **THEN** tabela e indicadores mostram somente movimentações que atendem a todos os filtros
- **AND** a tabela retorna à primeira página.

#### Scenario: Omitir período

- **WHEN** ambas as datas estiverem vazias
- **THEN** a consulta não envia filtro temporal e apresenta o conjunto geral disponível.

### Requirement: Exibir indicadores corretos

A tela MUST mostrar somente os cards não clicáveis Movimentações, Entradas e Saídas. Movimentações conta registros; Entradas e Saídas somam quantidades. Todos refletem o mesmo conjunto filtrado aplicado à tabela, incluindo datas, tipo, Produto e Fornecedor, e não dependem da página atual.

#### Scenario: Filtrar por um tipo

- **WHEN** o filtro Tipo for Entrada ou Saída
- **THEN** tabela e indicadores consideram somente esse tipo
- **AND** a soma do tipo oposto é zero.

#### Scenario: Paginar tabela sem alterar totais

- **WHEN** a tabela mudar de página
- **THEN** os indicadores continuam representando o conjunto filtrado completo.

#### Scenario: Fornecedor limita agregado

- **WHEN** um Fornecedor for selecionado
- **THEN** tabela e totais incluem somente registros com o `supplier_id` selecionado.

### Requirement: Exibir movimentos reais paginados

A tabela MUST usar os dados enriquecidos de `GET /movements`, manter paginação real e exibir Data/Hora, Tipo, Código, Produto, Quantidade, Usuário, Fornecedor e Motivo. O endpoint compartilhado MUST aceitar `movement.read` ou `report.read`, permitindo que o Relatório carregue os movimentos sem exigir acesso ao módulo Histórico. Fornecedor ausente MUST ser mostrado como `—`. O carregamento MUST NOT realizar uma chamada por movimentação.

#### Scenario: Lista vazia

- **WHEN** não houver movimentações para os filtros selecionados
- **THEN** o sistema apresenta uma mensagem de estado vazio sem tratar a resposta como erro.

#### Scenario: Relatório sem acesso ao Histórico

- **WHEN** um usuário possui `report.read`, mas não possui `movement.read`
- **THEN** consegue carregar a tabela de movimentos do Relatório.

### Requirement: Resumo de movimentações autorizado

O Xano MUST expor resumo agregado em endpoint autenticado protegido por `report.read`, com total de registros e somas das quantidades de entrada e saída, aplicando data inicial, data final, tipo, Produto e Fornecedor ao conjunto completo. O resumo MUST NOT ser calculado apenas sobre a página atual. Nenhuma permissão de escrita será introduzida.

#### Scenario: Agregar conjunto filtrado

- **WHEN** um usuário autenticado com `report.read` consulta o resumo
- **THEN** recebe totais para todos os registros correspondentes aos filtros aplicados.

### Requirement: Opções de filtro de relatório autorizadas

O Xano MUST fornecer as opções mínimas de Produto e Fornecedor usadas nos filtros por meio de `GET /report_options`, protegido por `report.read`. A consulta dessas opções MUST NOT exigir `product.read` nem `supplier.read`.

#### Scenario: Carregar filtros sem permissões operacionais
- **WHEN** um usuário possui `report.read`, mas não possui `product.read` nem `supplier.read`
- **THEN** consegue carregar as opções de Produto e Fornecedor necessárias ao Relatório.

### Requirement: Exportar relatório completo

A tela MUST oferecer exportação PDF em paisagem e XLSX dos dados completos correspondentes aos filtros aplicados, independentemente da página visível. Os arquivos MUST incluir filtros, resumo e tabela com Data/Hora, Tipo, Código, Produto, Quantidade, Usuário, Fornecedor e Motivo. A exportação MUST percorrer as páginas de `GET /movements` e respeitar um limite de segurança, sem solicitar uma página arbitrariamente grande.

#### Scenario: Exportar conjunto com várias páginas

- **WHEN** os filtros retornarem mais registros do que cabem na página atual
- **THEN** os arquivos contêm todas as páginas do conjunto filtrado.

### Requirement: Tratar sessão e erros

Relatórios MUST reutilizar a sessão atual. 401 MUST seguir o fluxo de login, 403 MUST exibir falta de permissão, entradas inválidas MUST receber mensagem específica e falhas inesperadas MUST exibir mensagem genérica sem traceback. Logs diagnósticos MUST incluir endpoint, status e detalhes do erro sem incluir token de autenticação.

#### Scenario: Erro de autorização

- **WHEN** o backend responde 401 ou 403
- **THEN** o sistema redireciona para login no caso 401 e informa falta de permissão no caso 403.
