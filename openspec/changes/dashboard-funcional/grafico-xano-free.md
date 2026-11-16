# Gráfico nativo — preparação local

Arquivo: xano/api/inventory_stock/movements_dashboard_get.xs.

O frontend e o contrato de resposta não foram alterados. O período enviado atualmente pelo Reflex já corresponde a sete dias civis completos em America/Sao_Paulo. A versão anterior admitia intervalos menores, mas esses intervalos não produziam as sete datas exigidas pelo cliente. A nova versão rejeita esses casos explicitamente.

## Fluxo

1. Exigir autenticação e movement.read ou report.read.
2. Validar início/fim e a fronteira do primeiro dia com format_timestamp/parse_timestamp no timezone de São Paulo.
3. Inicializar sete datas com zero; avançar por dias civis com transform_timestamp e exigir que date_to corresponda à fronteira final.
4. Consultar somente tipo/data_hora no intervalo [date_from, date_to), sem paginação truncada. Consumir o retorno stream em foreach, sem novas consultas dentro do loop.
5. Incrementar entradas ou saídas em um por operação e emitir as sete datas ordenadas.
6. Preservar a consulta separada das cinco últimas movimentações com seus campos públicos.

São duas declarações db.query de dados, além da autorização já existente, e um GET HTTP do frontend. Os filtros aproveitam o índice local por data_hora sem alterar schema. A agregação é O(N + 7), com sete objetos de contagem; o buffering interno do stream depende do Xano e não foi medido. O custo cresce com o número de operações da semana; não há limite artificial que reduza silenciosamente o total. Nenhum dado demonstrativo foi introduzido na interface.

## Validação e limites de evidência

Os testes locais verificam o script (ausência de SQL, filtros, projeção, stream, contadores e consultas fora de loops), usam um oráculo Python independente com Counter/ZoneInfo para os cenários de calendário e testam o envelope no cliente Reflex com mocks. O oráculo não é um interpretador XanoScript e não comprova a execução dos filtros/cursor no workspace.

Casos cobertos: período vazio; inclusão no início; exclusão no fim; meia-noite UTC versus São Paulo; fração de milissegundo nos limites; intervalo curto/longo/invertido; uma transição histórica de horário de verão; contagem maior que uma página; operações com unidades diferentes; cinco registros recentes e consumo pelo cliente existente.

Resultado local: nove testes novos e 60 testes direcionados do Dashboard aprovados; sintaxe final aceita pelo MCP; Reflex compile --dry aprovado; OpenSpec strict de dashboard-funcional e perfil-compras-solicitacoes aprovados. A suíte completa não foi repetida nesta etapa.

Publicação e execução no workspace permanecem pendentes. Conferir por leitura datas/contagens com registros já existentes autorizados, inclusive semana vazia e registros em limites de dia quando disponíveis. Não fabricar movimentos no live para completar testes.

## Publicação futura

Após autorização e revisão do preview, publicar somente esse endpoint; não precisa de tabela, helper novo, segredo ou migração. Antes de habilitar NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED, confirmar retorno com sete datas, até cinco recentes, permissões e custo no Free. Nenhuma flag foi alterada nesta etapa.

Comando de preview preparado, não executado:

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/inventory_stock/movements_dashboard_get.xs" --dry-run
```

Fontes: https://docs.xano.com/xanoscript/filter-reference/timestamp e https://docs.xano.com/the-function-stack/functions/database-requests/query-all-records.
