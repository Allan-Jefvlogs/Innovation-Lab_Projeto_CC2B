# Design: Fundação técnica de Estoque

## Decisões

### Um saldo por produto, com início em zero

`inventory_stock` terá `id`, `product_id` obrigatório e único, e `quantidade_disponivel` decimal obrigatório com mínimo zero. A referência única concretiza o relacionamento 1:1 do modelo de domínio. Decimal é coerente com `product.estoque_minimo`; regras de precisão operacional ficam para a change de movimentação.

Todo Produto terá um saldo. Produto recém-criado recebe saldo zero na mesma transação da criação cadastral. Produtos já existentes serão inicializados por `Inventory/initialize_stock_balances`, função interna idempotente e paginada (100 Produtos por chamada), que apenas cria saldo zero onde não há registro. O operador executará páginas em sequência até uma página retornar menos de 100 itens. Não existe tabela ou histórico de movimentações na implementação atual que permita inferir quantidade anterior; a função não deve ser executada em ambiente que possua saldos externos não reconciliados.

### Situação derivada

Não será persistida situação redundante. `GET /stock` calcula:

- `sem_estoque` quando quantidade é zero;
- `abaixo_minimo` quando quantidade é maior que zero e menor que `product.estoque_minimo`;
- `normal` quando quantidade é maior que zero e maior ou igual ao mínimo.

O caso de mínimo zero segue literalmente as condições: todo saldo positivo é `normal`.

### Autorização

O endpoint requer `auth = "user"` e `Inventory/authorize_permission` com `stock.read`. Administrador usa o bypass integral existente. `stock.read` será acrescentada ao catálogo; os grants iniciais de Almoxarife e Auxiliar serão acrescidos sem remover nem reescrever grants existentes. Permissões editadas manualmente permanecem sob a gestão já existente.

### Consulta

Novo grupo `Inventory Stock`, canonical `estoque`, com `GET /stock`, filtros de paginação no padrão do projeto (`page`, `per_page`, máximo 100) e resposta paginada `items`. A consulta parte de `inventory_stock`, associa Produto em uma consulta com JOIN e projeta `product_id`, `codigo`, `nome`, `quantidade_disponivel`, `estoque_minimo` e `situacao_estoque`. A situação é montada no backend para evitar cálculo de domínio no Reflex. Não há chamada por produto no frontend.

### Implantação e dados anteriores

Ordem: publicar tabela e função; publicar a criação transacional de Produto e a permissão; executar uma vez a inicialização idempotente dos Produtos existentes; publicar o grupo/endpoint. Nesta etapa não haverá push nem execução da função. O importador remoto deve ser verificado antes de publicar o endpoint, pois a validação local do MCP não garante aceitação remota.

## Arquivos Xano previstos

- Novo `xano/table/inventory_stock.xs`.
- Novo `xano/function/inventory/initialize_stock_balances.xs`.
- Novo `xano/api/inventory_stock/api_group.xs` e `stock_get.xs`.
- Alterados `xano/api/inventory_catalog/products_post.xs` e `xano/function/inventory/seed_initial_data.xs`.

## Riscos

- Produtos existentes sem saldo precisam ser inicializados antes da consulta remota; ausência inesperada após a migração causa omissão na listagem de saldos.
- Produto e saldo devem ser gravados na mesma transação para impedir cadastro sem saldo.
- JOINs são aceitos pela documentação/validador local, mas o histórico do workspace registra incompatibilidades no importador remoto; nenhum sucesso remoto é presumido.
- A inicialização com zero só é correta porque o backend local não possui movimentações/saldos anteriores. Ambientes com dados externos exigem reconciliação antes de executar a função.

## Limites

Nenhuma operação de entrada/saída, alteração de saldo após criação, histórico, UI Reflex, dashboard, relatório, sync, push ou commit é incluída.

## Evidência posterior da integração Reflex (tarefa 5.3)

A integração que estava fora do escopo original foi realizada em Changes próprias. A Change arquivada `integracao-frontend-estoque` documenta a tela `/estoque` consumindo `GET /stock`, o uso da permissão `stock.read`, paginação e filtros; também registra dry-runs isolados de `GET /stock` e `GET /stock_summary`, com preview somente de UPDATEs e sem publicação nessa revisão. A Change arquivada `integracao-frontend-movimentacoes` documenta que Entrada e Saída carregam saldos por `GET /stock` e usam o saldo retornado/consultado no fluxo Reflex.

As Changes arquivadas de operação de Entrada e Saída registram testes reais posteriores no NexStock: Entrada de `10,75 KG` e Saídas até saldo zero, com histórico confirmado. Isso demonstra uso runtime do fluxo integrado com saldos do backend. Em conjunto com a validação XanoScript registrada na tarefa 4.1 desta Change e os dry-runs posteriores dos endpoints de consulta, essa evidência satisfaz a tarefa 5.3, que pedia a integração em Change própria após publicação e validação do endpoint.

Essa conclusão limita-se à integração Reflex e ao uso runtime documentado. O registro anterior não comprovava a execução de `Inventory/initialize_stock_balances`; a auditoria posterior abaixo verificou que hoje não há saldos ausentes e concluiu a tarefa 5.2 sem executar a função. Isso não comprova rollback nem garantias contra lost update ou overselling; esses limites permanecem explícitos na tarefa 4.4 e nas Changes de validação avançada/concorrência correspondentes.

## Auditoria somente leitura do workspace Xano 152211 (tarefas 5.1 e 5.2)

Em 13/10/2026, foi consultado o workspace `152211` do perfil Xano `alan inovation` por operações GET da Meta API. Não foram executados endpoints de escrita, seed, inicializador, push ou alteração de grants. As definições consultadas retornaram `xanoscript.status = ok`; as consultas não incluíram versões draft.

### Comparação local e remota

| Componente | Evidência remota | Comparação e limite |
|---|---|---|
| Tabela `inventory_stock` (ID `901137`) | Campos `id`, `product_id` e `quantidade_disponivel`; índice primário em `id` e índice `unique` em `product_id` | Corresponde ao modelo local de um saldo por Produto. A diferença textual na declaração do nome da tabela é serialização/canonicalização do Xano. |
| `Inventory/initialize_stock_balances` (ID `349010`) | Função existente; pagina Produtos em lotes de 100, consulta saldo por `product_id` e só executa `db.add inventory_stock` com quantidade zero quando não encontra saldo | O comportamento de preenchimento idempotente corresponde ao contrato local. A função não foi executada nesta auditoria; a necessidade do backfill foi avaliada pelos registros atuais. |
| POST `/products` (API ID `4070897`) | Endpoint no grupo Inventory Catalog; autorização `product.create`; inclui `db.transaction`, criação de `product` e `db.add inventory_stock` com saldo zero | Os marcadores funcionais de criação transacional de saldo estão presentes tanto na versão local quanto na remota. `fornecedor_padrao_id` também aparece em ambas. A auditoria não provocou rollback nem repetiu cadastro. |
| Autorização `Inventory/authorize_permission` (função ID `347998`) | A versão remota inclui `permission_code`, `PERMISSION_DENIED`, `PERMISSION_CATALOG_INVALID`, verificação de `is_active` e `must_change_password`, além do bypass protegido de `administrator` | Os pontos de autorização examinados também estão na versão local. Os textos não são idênticos; a comparação funcional desta auditoria limitou-se aos controles citados. |
| Catálogo e grants `stock.read` | A permissão está no catálogo remoto (ID `13`). `stockkeeper` (Almoxarife) e `read_only` (Auxiliar de almoxarifado) possuem grant nas tabelas remotas | Os registros confirmam os grants atuais sem depender apenas do seed. O seed local/remoto contém diferenças de outras Changes, mas os registros e grants específicos de `stock.read` estão presentes; não há necessidade de executar seed para esta revisão. |
| GET `/stock` (API ID `4075336`, grupo `Inventory Stock`, canonical `estoque`) | O OpenAPI remoto lista `/stock` com `situacao`, `search`, `page` e `per_page`. A definição exige `auth = user`, chama o autorizador com `stock.read`, limita `per_page` a 100 e deriva `sem_estoque`, `abaixo_minimo` e `normal` | Os controles essenciais correspondem ao contrato local. A resposta remota também contém `categoria_id` e `fornecedor_padrao_id`, campos aditivos usados por integrações posteriores. A definição publicada confirma o contrato, mas não demonstra runtime de páginas além da primeira nem de cada filtro de situação. |

As diferenças textuais entre XanoScript local e remoto incluem canonicalização de nomes, espaçamento/estrutura serializada e metadados; o seed também incorpora permissões de Changes posteriores. Nos elementos específicos desta fundação, a auditoria encontrou a tabela, função, endpoint, regra `stock.read`, paginação e classificações esperadas. Nenhuma divergência funcional da fundação foi identificada que impeça a aprovação do escopo da tarefa 5.1. Isso não equivale a executar a matriz de testes isolados da tarefa 4.4.

### Reconciliação dos registros atuais (tarefa 5.2)

As consultas paginadas de conteúdo das tabelas remotas retornaram **7 Produtos**, **7 registros em `inventory_stock`** e **20 movimentações**. A conferência foi por existência do registro e referência `product_id`, não pelo valor da quantidade: saldo zero foi contado como registro existente.

- Produtos sem registro correspondente em `inventory_stock`: **0**.
- Registros de `inventory_stock` sem Produto correspondente: **0**.
- Referências `product_id` duplicadas em `inventory_stock`: **0**.
- Movimentações que referenciam Produto inexistente: **0**.
- Situação calculada a partir dos dados atuais: 1 `abaixo_minimo`, 6 `sem_estoque`, 0 `normal`.
- Para os Produtos com movimentações: Produto ID `1` tem saldo `2` e líquido de movimentos `+2` (14 movimentos); ID `2` tem saldo `0` e líquido `0` (2 movimentos); ID `6` tem saldo `0` e líquido `0` (4 movimentos). Em todos os três, saldo menos líquido de movimentos é zero. Os outros quatro Produtos têm saldo zero e nenhuma movimentação.

Como todos os Produtos atuais já possuem uma linha de saldo e não há saldo órfão ou diferença aritmética identificada nas movimentações existentes, o backfill não tem registros ausentes para criar. **`Inventory/initialize_stock_balances` não foi chamado e não é necessário nesta situação**; a tarefa 5.2 foi ajustada para registrar a verificação por leitura e exigir execução apenas se surgirem saldos ausentes. Executar a rotina sem necessidade não acrescentaria evidência. Se no futuro houver Produto sem saldo, deve-se reconciliar primeiro qualquer saldo externo não representado no ledger; a rotina cria zero para o ausente e não reconstrói saldo histórico.

Esta reconciliação cobre o retrato atual das três tabelas no workspace 152211. Ela não prova rollback, atomicidade sob falha provocada, consistência concorrente ou prevenção de lost update/overselling. A tarefa 4.4 permanece pendente para testes em datasource isolada, e a conta Free continua sem Sandbox/Data Source adicional.

## Decisão sobre a tarefa 4.4 e encerramento da Change

A tarefa 4.4 continua **pendente**. A auditoria separa evidência de contrato/publicação e funcionamento observado de testes controlados em datasource isolada; nenhuma dessas evidências foi promovida a aprovação dos cenários que não foram executados.

| Critério da 4.4 | Evidência disponível | Estado do teste isolado |
|---|---|---|
| Autorização de leitura `stock.read` | A função remota `Inventory/authorize_permission`, o endpoint `GET /stock`, o catálogo e os grants atuais de `stockkeeper` e `read_only` foram inspecionados. A rota foi usada nos fluxos integrados documentados em Changes posteriores. | Não comprovados em datasource isolada: matriz controlada de usuário autorizado, usuário sem grant e requisição não autenticada para esta tarefa. |
| Criação atômica de Produto e saldo | O `POST /products` remoto contém `db.transaction`, cria Produto e saldo zero; Produtos e saldos atuais foram reconciliados. | Não comprovado: provocar falha após uma escrita e observar rollback sem deixar dados residuais. A definição publicada e a consistência atual não provam rollback. |
| Idempotência de `Inventory/initialize_stock_balances` | A função remota foi inspecionada: pagina Produtos, verifica a existência do saldo e só adiciona linha quando ausente. | Não comprovado: executar repetidamente em ambiente controlado e verificar que não duplica linhas. A função não foi chamada; a reconciliação constatou zero Produtos sem saldo, portanto não havia backfill necessário. |
| Paginação de `GET /stock` | O contrato remoto declara `page`, `per_page` com máximo 100 e resposta paginada; a integração e seus filtros estão documentados em Changes posteriores. | Não comprovado nesta tarefa: consultar mais de uma página de forma controlada e verificar ausência de duplicatas/omissões entre páginas. A base atual tem apenas sete Produtos e não demonstra percurso de várias páginas. |
| Limites das situações `sem_estoque`, `abaixo_minimo` e `normal` | A lógica publicada deriva as três situações; a fotografia dos dados retornou seis saldos zero (`sem_estoque`) e um saldo positivo abaixo do mínimo (`abaixo_minimo`). | Parcial: há dados observados para duas classificações; não há caso atual `normal` nem matriz controlada dos limites, especialmente mínimo zero e saldo igual ao mínimo. |

### Limitação de ambiente e preservação do escopo

O plano Free utilizado nesta conta não disponibiliza Sandbox nem Data Source adicional. Por isso, testes que exigem falha induzida, repetição de inicialização ou massa de dados para várias páginas não devem ser realizados no datasource compartilhado de produção como substituto de isolamento. Nenhum teste pendente foi declarado aprovado e nenhuma operação de escrita adicional foi feita para esta revisão.

Os requisitos funcionais da Change permanecem implementados e documentados na spec delta: saldo único e não negativo por Produto, criação de saldo zero junto ao Produto, inicializador idempotente, classificação derivada e consulta paginada protegida por `stock.read`. A ausência de testes isolados não remove esses requisitos nem contradiz as evidências de implementação/publicação; ela limita a validação dos casos controlados. A tarefa 4.4 permanece desmarcada, preservando a contagem real de **15/16**.

### Estratégia de arquivamento

Quando o projeto decidir retirar esta Change da lista ativa, a estratégia apropriada é o arquivamento **normal, sem `--skip-specs`**, para consolidar a spec funcional desta fundação em `openspec/specs`. A inspeção da árvore atual não encontrou uma spec consolidada própria para `fundacao-tecnica-estoque`; pular a atualização deixaria os requisitos implementados apenas no histórico da Change. O arquivamento normal deve preservar o `tasks.md` com a 4.4 desmarcada, sem reescrever o teste pendente como concluído.

O OpenSpec 1.13.1 apresenta o arquivamento como operação para Change concluída e, ao detectar tarefas incompletas, solicita confirmação; em execução não interativa, bloqueia sem `--yes`. A implementação local confirma que `--yes` permite continuar apesar das tarefas incompletas. Portanto, se a equipe optar por arquivar mantendo 15/16, deve fazê-lo conscientemente com o mecanismo normal e confirmação explícita, sem `--skip-specs`; esta revisão não executou nem autorizou o arquivamento. A documentação de status deve continuar informando que os testes da 4.4 não foram realizados por falta de datasource isolada.
