# Design: Dashboard com dados reais

## Contratos atuais e autorização

- `GET /products` usa `status=ativo`, `page=1`, `per_page=1` e `itemsTotal` para contar Produtos ativos sem percorrer o catálogo.
- O indicador de estoque abaixo do mínimo usa o resumo autorizado ou a listagem paginada existente, com metadados para a contagem e uma amostra limitada de alertas.
- `GET /movements/dashboard` fornece a série real do gráfico e as cinco movimentações recentes; o período selecionado não limita a seção recente.
- `GET /purchase_requests/summary` alimenta o indicador de solicitações em andamento.
- A interface verifica `product.read`, `stock.read`, `movement.read` ou `report.read`, e `purchase_request.read` antes de cada fonte; o Xano permanece responsável por autorizar as chamadas.

As consultas iniciais atuais correspondem a Produtos, Estoque, Movimentações e Solicitações de compras. As referências históricas a métricas de Categorias e Fornecedores não descrevem cartões atuais e não devem ser reaplicadas.

## Requisições e cache

O carregamento é coordenado pelo `XanoRequestCoordinator` e reutiliza `SessionReadCache`, com chaves isoladas pela identidade/sessão e parâmetros relevantes. O cache não armazena token, grants ou dados de autenticação. TTLs configuráveis: Produtos 30 s por padrão e fontes operacionais 15 s por padrão. Escritas Xano bem-sucedidas invalidam as entradas afetadas da sessão; falhas não atualizam o cache como se a escrita tivesse sido concluída.

## Falhas e autorização

Sem grant, o carregador não consulta a fonte e apresenta indisponibilidade por permissão. Falhas não são convertidas em zero nem em lista vazia legítima. Dados anteriores eventualmente preservados após falha são identificados como potencialmente desatualizados. A recuperação é manual e respeita o coordenador e o cooldown; não há polling nem retry automático. O Dashboard não confirma operações de estoque nem substitui autorização ou saldo do backend.

## Evidências e limitações

Os testes simulados verificam projeção, contagem, grants, isolamento, expiração, invalidação por escrita, 429 e timeout. A compilação Reflex é validação local. Estes resultados não comprovam publicação dos contratos locais nem comportamento atual no workspace remoto.

## Reconciliação com a spec oficial

Os contratos permanentes desta change foram consolidados em `openspec/specs/dashboard/spec.md`: uso de dados reais, grants e autorização efetiva do Xano, isolamento de cache por sessão, invalidação após escrita confirmada, distinção entre falha e ausência de dados, estados de cache possivelmente desatualizado, limites de requisições e ausência de polling/retry automático. Os indicadores atuais são Produtos ativos, estoque abaixo do mínimo e solicitações de compra abertas; Movimentações recentes permanece como seção própria.

As referências históricas a cartões/contagens de Categorias e Fornecedores não descrevem o Dashboard atual e não devem ser reaplicadas no layout nem em specs futuras. O delta `dashboard-real` foi removido por duplicar a capability oficial `dashboard`; não há requisito exclusivo desta change que precise criar uma capability paralela.

`skip_specs: true` declara que o arquivamento desta change não deve reaplicar deltas: os contratos permanentes já estão consolidados na capability oficial `dashboard`.

## Registro de QA — 2026-11-16

- Origem: conferência manual informada pelo usuário.
- Grupos confirmados: Dashboard com dados reais e Dashboard com restrições de acesso e falhas.
- Critérios cobertos pela aceitação informada: apresentação de dados reais do Dashboard e revisão dos estados relacionados a acesso e falhas.
- Limites: não foram fornecidas capturas, medições, logs independentes ou detalhes por cenário; o registro não substitui evidência automatizada ou uma nova validação no Xano publicado.
