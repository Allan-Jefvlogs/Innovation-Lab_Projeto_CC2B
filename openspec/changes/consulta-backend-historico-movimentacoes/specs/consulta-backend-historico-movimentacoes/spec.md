# Specification: Consulta backend do histórico de movimentações

## ADDED Requirements

### Requirement: Consultar movimentações reais de forma paginada e enriquecida

O backend MUST expor `GET /movements` no grupo autenticado `Inventory Stock` (`api:estoque`). O endpoint MUST exigir autenticação e a permissão existente `stock.read`; MUST NOT criar ou alterar grants. Líder, Almoxarife e Auxiliar com a matriz atual podem ler o histórico.

A resposta paginada MUST fornecer em cada item `movement_id`, `product_id`, `product_code`, `product_name`, `tipo`, `quantidade`, `data_hora`, `user_id`, `user_name`, `supplier_id`, `supplier_name`, `motivo` e `observacao`. `tipo` MUST preservar `entrada` ou `saida`. Usuário MUST ser projetado apenas com o nome amigável, sem campos sensíveis.

Produto, usuário e Fornecedor MUST ser resolvidos dentro da consulta do endpoint, sem requisição adicional do cliente por movimentação. A consulta MUST preservar movimentos ligados a Produtos ou Fornecedores inativos e MUST manter movimentos cujo Fornecedor é nulo.

Os parâmetros `page` e `per_page` MUST paginar resultados; `page` MUST ser pelo menos 1, `per_page` MUST ser pelo menos 1 e MUST NOT exceder 100. A ordenação MUST ser `data_hora` decrescente, com `id` decrescente como desempate. O metadata de paginação MUST seguir o envelope paginado nativo usado pelo projeto.

O parâmetro opcional `tipo` MUST aceitar somente `entrada` ou `saida`; outro valor MUST retornar `INVALID_INPUT`. O parâmetro opcional `product_id` MUST filtrar pelo Produto persistido. O parâmetro opcional `user_id` MUST ser um inteiro positivo e filtrar por `inventory_movement.user_id`; se não houver movimentações correspondentes, o endpoint MUST retornar lista vazia. Os filtros MUST poder ser combinados na mesma consulta. A ausência dos filtros MUST retornar os dois tipos, todos os Produtos e todos os usuários.

O backend MUST expor `GET /movement_users` no grupo autenticado `Inventory Stock`, protegido por `stock.read`, para prover opções ao filtro de Histórico. A resposta MUST listar usuários da tabela de autenticação independentemente de `inventory_profile_id` ser nulo, MUST ser paginada, ordenada por nome e ID e conter somente `id` e `name`, sem dados sensíveis. Isso MUST permitir filtrar responsáveis históricos resolvidos por `inventory_movement.user_id` mesmo que o perfil atual esteja ausente. O endpoint MUST aceitar `page` e `per_page` limitado a 100.

#### Scenario: Consultar movimentos enriquecidos

- **WHEN** um usuário autorizado consulta `GET /movements`
- **THEN** cada item inclui os dados da movimentação e os nomes/códigos relacionados obtidos na consulta paginada

#### Scenario: Filtrar por tipo e Produto

- **WHEN** a consulta informa `tipo=saida` e um `product_id`
- **THEN** só são retornadas saídas daquele Produto

#### Scenario: Combinar filtro de usuário com os demais filtros

- **WHEN** a consulta informa `tipo=saida`, `product_id=1` e `user_id=5`
- **THEN** só são retornadas saídas do Produto 1 registradas pelo usuário 5, na mesma consulta paginada e enriquecida

#### Scenario: Validar identificador de usuário

- **WHEN** `user_id` é zero ou negativo
- **THEN** o endpoint rejeita o valor inválido

- **WHEN** `user_id` é positivo, mas não possui movimentações
- **THEN** o endpoint retorna lista vazia sem erro

#### Scenario: Rejeitar tipo inválido

- **WHEN** `tipo` tem valor diferente de `entrada` e `saida`
- **THEN** o endpoint retorna `INVALID_INPUT`

#### Scenario: Preservar histórico de cadastros inativos e Fornecedor nulo

- **WHEN** uma movimentação pertence a Produto ou Fornecedor inativo ou não tem Fornecedor
- **THEN** ela continua na listagem, com os dados disponíveis e os campos do Fornecedor nulos quando não houver vínculo

#### Scenario: Restringir acesso

- **WHEN** uma requisição não está autenticada ou não possui `stock.read`
- **THEN** o Xano aplica autenticação ou autorização e não retorna dados do histórico
