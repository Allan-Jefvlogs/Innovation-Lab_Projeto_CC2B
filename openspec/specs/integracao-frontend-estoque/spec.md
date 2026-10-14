# integracao-frontend-estoque Specification

## Purpose
TBD - created by archiving change integracao-frontend-estoque. Update Purpose after archive.

## Requirements

### Requirement: Consultar saldos reais

O sistema MUST apresentar linhas obtidas de `GET /stock`, sem dados estáticos ou mockados, mostrando código, produto, saldo atual, mínimo e situação.

#### Scenario: Abrir Estoque

- **WHEN** um usuário autenticado com `stock.read` abrir `/estoque`
- **THEN** o sistema busca uma página de saldos e o resumo agregado do backend
- **AND** os contadores representam produtos, não unidades em saldo.

### Requirement: Classificar situação no backend

O backend MUST preservar as regras existentes: zero é `sem_estoque`; saldo positivo menor que o mínimo é `abaixo_minimo`; saldo positivo maior ou igual ao mínimo é `normal`.

#### Scenario: Filtrar lista por situação

- **WHEN** `GET /stock` for consultado com um filtro opcional `situacao` válido
- **THEN** a filtragem ocorre antes da paginação e a resposta conserva o contrato paginado atual
- **AND** valores inválidos são rejeitados como entrada inválida.

### Requirement: Exibir resumo de estoque

O backend MUST fornecer totais de itens monitorados e das três situações, sem retornar todos os saldos ao cliente.

#### Scenario: Calcular totais

- **WHEN** o resumo autenticado for consultado
- **THEN** cada produto de estoque é contado uma única vez na respectiva situação
- **AND** o acesso exige `stock.read`.

### Requirement: Navegar por situação

Os cards Abaixo do mínimo e Sem estoque MUST filtrar a tabela da própria rota `/estoque`, usando somente valores canônicos (`abaixo_minimo` e `sem_estoque`). Clicar novamente no card selecionado MUST limpar a situação; clicar em outro card MUST substituir o filtro.

#### Scenario: Abrir lista de situação

- **WHEN** um usuário autorizado selecionar um card de situação
- **THEN** a tabela paginada mostra somente produtos da situação escolhida
- **AND** a rota continua `/estoque`.

### Requirement: Buscar produtos no estoque

A busca MUST procurar por código e nome no backend antes da paginação e combinar com a situação selecionada. Termo vazio não deve filtrar resultados.

#### Scenario: Buscar em conjunto com situação

- **WHEN** o usuário aplicar um termo com uma situação selecionada
- **THEN** `GET /stock` recebe ambos os filtros e retorna somente correspondências daquela situação.

### Requirement: Respeitar autorização existente

As novas consultas MUST usar a permissão existente `stock.read`, sem modificar grants ou a arquitetura de autorização.

#### Scenario: Acesso de perfis permitidos

- **WHEN** um perfil que já pode acessar Estoque abrir `/estoque`
- **THEN** ele pode consultar os saldos pela mesma autorização `stock.read`.
