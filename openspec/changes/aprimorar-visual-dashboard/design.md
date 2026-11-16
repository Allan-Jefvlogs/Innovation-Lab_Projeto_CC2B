# Design: Aprimorar o visual do Dashboard

## Referência e abordagem

A captura oficial (1200 × 750) e o HTML/CSS publicado de https://nextstock-interface-prototipo-2026.justcube2.chatgpt.site/ foram consultados. A composição acompanha essa referência, adaptada aos três indicadores reais e às páginas existentes, incluindo Auditoria. Números, usuários e registros demonstrativos do protótipo não são utilizados.

Sidebar sálvia de 252 px no desktop, cabeçalho claro de 78 px, conteúdo centralizado com largura máxima de 1440 px incluindo padding de 38 px. Cartões com altura mínima de 131 px, padding de 17 px por 18 px, cantos de 17 px e intervalos de 17 px. A marca lateral mostra NextStock e Gestão inteligente de estoque com a geometria compartilhada existente. Em larguras intermediárias a sidebar mede 210 px; em dispositivos móveis, um menu em diálogo conserva as rotas e permissões existentes.

A introdução usa o primeiro nome real da sessão. Por solicitação do usuário, o atalho Nova movimentação foi removido do Dashboard; as rotas e os acessos existentes de Entrada/Saída permanecem no menu. A busca sem função foi removida e o sino usa a central de notificações já integrada, sem alterar seu contrato nesta change.

## Painéis e dados

Gráfico e alertas usam painéis brancos, padding de 19 px e duas colunas na proporção 1,5:0,9, empilhadas abaixo de 1051 px. A tabela fica abaixo, com cabeçalho neutro claro e as mesmas cinco colunas proporcionais. Indicadores reais usam menta, rosa e pêssego. Alertas preservam situação, saldo e mínimo; a barra representa apenas a relação visual entre saldo e mínimo conhecido e positivo. Mínimo zero ou ausente não gera divisão inválida nem elimina o alerta.

O gráfico de linhas recebe a série real agregada pelo Dashboard e preserva a composição visual aprovada. A seleção oferece 7 dias (padrão), 30 dias e 12 meses; o estado do período não altera a lista de movimentações recentes. O componente Recharts existente mantém legenda, eixos, cores sálvia e pêssego, grade discreta e dimensões responsivas. A integração e os contratos de dados são detalhados em `dashboard-funcional` e `integracao-dashboard-real`.

## Correção do gráfico vazio

O objeto bruto height com chaves initial/md permanecia literal no JSX e gerava CSS inválido, deixando o ResponsiveContainer sem altura efetiva. Agora a altura numérica é 228 px: aproximadamente 204 px de desenho e 24 px para os dias. O pai possui altura e altura mínima explícitas. O wrapper instalado cria um único ResponsiveContainer. Breakpoints do layout são expressos por mecanismos Reflex que produzem media queries reais.

As duas linhas são contínuas, sálvia e pêssego, com grade discreta e legenda. Elas representam contagens reais de operações de entrada e saída, sem somar quantidades de unidades diferentes e sem alterar indicadores, alertas, relatórios ou saldos.

## Compatibilidade

DashboardState e os contratos de dados não foram alterados. Rotas, grants, recuperação de erro, cache e carregamento permanecem existentes. A identidade centralizada também beneficia componentes compartilhados das demais páginas. Não há publicação ou alteração de dados Xano.

## Validação e limites

Seis testes direcionados verificam marca compartilhada, colunas, espaçamentos, altura efetiva do gráfico, breakpoints e cálculo visual dos alertas com saldo fracionário e mínimo zero. A compilação Reflex, o build de produção e OpenSpec strict foram aprovados. O gráfico real e os três períodos foram posteriormente confirmados pelo usuário como funcionais; esse relato não substitui a comparação visual autenticada.

A referência foi obtida e conferida. A inspeção visual autenticada do Dashboard em desktop (1920 × 960) e em viewport estreito permanece pendente. Compilação, testes, execução funcional do gráfico e confirmação do bundle servido não comprovam fidelidade visual ou ausência de erros no navegador.

O git diff --check geral aponta espaço final preexistente em xano/api/inventory_catalog/users_by_id_inactivate_patch.xs:35, preservado fora do escopo. A verificação dos arquivos alterados nesta tarefa não aponta espaços finais. Os hashes de .env, profile.yaml, requirements.txt e dos dois arquivos de reflex.lock permaneceram iguais após o build.
