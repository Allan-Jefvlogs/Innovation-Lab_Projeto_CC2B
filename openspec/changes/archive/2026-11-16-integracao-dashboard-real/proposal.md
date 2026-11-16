# Integrar o Dashboard com dados reais do Xano

## Por que

A página `/dashboard` ainda apresenta contagens, movimentações e alertas fixos de protótipo. Esses valores não refletem os dados atuais do NexStock e podem induzir decisões incorretas durante o uso e a apresentação acadêmica.

## O que muda

- Substituir os valores fixos pelas fontes do Dashboard atual: Produtos ativos, estoque abaixo do mínimo, solicitações de compra em andamento e movimentações reais. Não criar cartões de Categorias ou Fornecedores, que pertenciam ao escopo inicial e não correspondem ao layout atual.
- Respeitar os grants atuais de leitura; o backend continuará sendo a autoridade de cada consulta.
- Reutilizar o cache em memória por sessão e o coordenador de requisições já existentes.
- Mostrar carregamento, erro, indisponibilidade, ausência de dados e valores em cache explicitamente desatualizados.
- Atualizar as métricas após qualquer escrita Xano bem-sucedida.

## Escopo

Esta Change cobre somente a integração local da página Dashboard. Não cria nem publica endpoints Xano, não altera dados ou grants e não adiciona polling, gráficos decorativos ou um mecanismo de cache independente.

## Critérios de aceitação

- Nenhum valor de protótipo é apresentado como dado real.
- Com todos os grants aplicáveis, a primeira carga solicita no máximo cinco recursos do Dashboard: Produtos ativos, Categorias, Fornecedores, saldos abaixo do mínimo e movimentações recentes.
- Cada recurso só é consultado quando a sessão validada possui o grant correspondente.
- Resultados são isolados por sessão, têm TTL limitado e são invalidados após escrita bem-sucedida.
- Erros não são convertidos em contagens zero; falhas temporárias podem preservar dados anteriores identificados como potencialmente desatualizados.
- A atualização é manual após falha e não inicia retries automáticos.
