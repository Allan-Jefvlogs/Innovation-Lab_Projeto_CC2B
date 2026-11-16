# Aprimorar o visual do Dashboard

## Problema

O Dashboard possui os dados e as ações necessários, mas sua apresentação ainda não acompanha a hierarquia visual da referência fornecida pelo grupo.

## Objetivo

Aproximar a apresentação do Dashboard da referência usando os dados já disponíveis e preservando carregamento, permissões, estados de erro, cache e navegação existentes.

## Escopo

- Melhorar a hierarquia do cabeçalho e a apresentação dos cards de indicadores.
- Apresentar movimentações recentes e alertas em painéis brancos, com indicadores e barras suaves da paleta, mantendo suas informações e estados atuais.
- Manter a adaptação para telas menores.
- Preservar o painel “Movimentação do estoque” com séries alimentadas por dados reais e seleção de 7 dias, 30 dias e 12 meses, sem alterar os indicadores nem os registros exibidos.
- Harmonizar os estilos compartilhados das páginas existentes com a paleta, preservando Auditoria e todas as rotas atuais.

## Fora do escopo

- Criar novas consultas ou indicadores nesta change; a integração de dados reais do gráfico é documentada em `dashboard-funcional` e `integracao-dashboard-real`.
- Alterar contratos Xano, permissões, regras de negócio, rotas ou comportamento das ações existentes.
- Alterar permissões, regras de negócio, rotas ou comportamento das ações existentes.
