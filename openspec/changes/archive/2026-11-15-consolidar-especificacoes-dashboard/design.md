# Design

## Contexto

As specs oficiais não possuem uma capability de Dashboard. A change `integracao-relatorios` cobre relatórios e consultas operacionais, enquanto `integracao-usuarios` já cobre autenticação, troca obrigatória de senha, reset administrativo e proteção geral de credenciais. As quatro changes de origem permanecem ativas e não serão alteradas nesta change.

A proposta cria a capability `dashboard` para o comportamento integrado atual, mantém tokens de paleta em `identidade-visual` e acrescenta somente a troca voluntária da própria senha à capability existente `integracao-usuarios`. A descrição do Dashboard está limitada aos indicadores atuais: Produtos ativos, estoque abaixo do mínimo e solicitações abertas, além de alertas e movimentações recentes. Não são reintroduzidos cartões de Categorias/Fornecedores.

## Objetivos e não objetivos

**Objetivos:**

- Criar deltas verificáveis que possam ser incorporados pelo fluxo OpenSpec depois de revisão.
- Manter requisitos do Dashboard separados de regras gerais de autenticação, de relatório e de identidade visual.
- Distinguir contratos normativos, confirmação do usuário e verificações ainda pendentes.

**Não objetivos:**

- Alterar `openspec/specs` nesta etapa; o CLI reserva a consolidação oficial à operação `archive`.
- Implementar, ajustar ou publicar funcionalidades, código, endpoints, dados ou configurações.
- Arquivar ou excluir changes de origem.
- Declarar QA visual, revogação de tokens ou proteção abrangente de logs concluídos.

## Decisões

### Uma capability operacional de Dashboard

Os requisitos de dados, métricas, cache, falhas, gráfico, notificações e composição da página ficarão em `dashboard`. Isso evita produzir várias specs concorrentes sobre o mesmo painel. A capability `integracao-relatorios` permanece separada porque define filtros, exportações e agregados do relatório, e não o resumo da página Dashboard.

Foram consideradas capabilities distintas para gráfico, notificações e layout. Foram rejeitadas porque essas funções são partes da mesma experiência e compartilham sessão, orçamento de chamadas e apresentação.

### A identidade visual continua global

Os tokens de cor, semântica e legibilidade ficam em `identidade-visual`. `dashboard` descreve apenas a composição do painel e referencia a capability global, sem repetir códigos de cores. A change `identidade-visual-paleta-natural` não é alterada.

### Alteração voluntária de senha pertence a usuários

A regra específica de alteração da própria senha será adicionada como requisito a `integracao-usuarios`. Os requisitos existentes de login, sessão, perfis, troca obrigatória e reset continuam sendo a fonte geral; o delta novo cobre validação da senha atual, identidade `$auth.id`, proteção dos valores e efeito de sessão local.

O requisito não afirma revogação de tokens de outras sessões. A flag permanece desligada por padrão; o launcher local explícito não equivale à ativação permanente.

### Requisitos antigos de protótipo não são copiados

`criar-projeto-inicial` declara seu escopo como protótipo inicial. Seus dados fictícios e cartões estáticos não serão copiados para `dashboard`; a capability operacional aplica-se ao sistema integrado atual. `integracao-relatorios` e `autenticacao-autorizacao` mantêm suas responsabilidades próprias.

### Mudanças de origem e arquivamento

Os requisitos foram mapeados sem editar as quatro changes de origem. Depois de revisar e incorporar esta change às specs oficiais, será necessário reconciliar os deltas originais antes de arquivá-los, evitando aplicar requisitos repetidos ou contraditórios duas vezes. Arquivamento futuro depende da conclusão das tarefas aplicáveis e de evidência suficiente; não será usado como substituto de validação funcional.

| Change de origem | Requisitos compartilhados ou exclusivos | Destino preparado | Situação depois desta etapa |
| --- | --- | --- | --- |
| `integracao-dashboard-real` | Dados reais, métricas baseadas em paginação, grants, cache por sessão, falhas sem zero fictício e invalidação após escrita | `dashboard` | Continua aberta; invalidação após escrita e estados por fonte precisam permanecer no contrato canônico |
| `dashboard-funcional` | Cabeçalho, notificações persistidas, leitura individual, abertura do pedido, carregamento incremental, gráfico real e períodos; senha voluntária é requisito de usuário | `dashboard` e `integracao-usuarios` | Continua aberta; matriz completa de autorização/erro e limitações de segurança permanecem pendentes |
| `aprimorar-visual-dashboard` | Composição, dimensões, cartões, painéis, gráfico, alertas, tabela e responsividade; o requisito de gráfico ilustrativo foi substituído para o Dashboard atual | `dashboard` | Continua aberta até QA visual autenticado em desktop e viewport estreito |
| `identidade-visual-paleta-natural` | Tokens globais, semântica de estados, contraste e responsividade | `identidade-visual` | Continua independente e aberta até QA visual global |

Requisitos compartilhados de dados reais, autorização, isolamento e distinção de erros ficam uma só vez em `dashboard`. A contagem de operações do gráfico não soma unidades. As cores globais ficam somente em `identidade-visual`. Dados e indicadores estáticos descritos por `criar-projeto-inicial` pertencem à geração do protótipo, conforme o propósito dessa capability, e não são trazidos para o contrato do Dashboard integrado. O gráfico ilustrativo da change visual foi substituído pelo gráfico real e pelos três períodos no contrato preparado.

## Evidências e pendências

| Item | Evidência disponível | Estado nesta change |
| --- | --- | --- |
| Gráfico real e períodos 7 dias, 30 dias e 12 meses | Funcionamento reportado pelo usuário | Confirmado como relato; não repetido nesta etapa |
| Notificações, leitura e navegação | Funcionamento reportado pelo usuário | Confirmado como relato; validação completa de estados e autorização permanece pendente |
| Alteração de senha | Teste controlado reportado pelo usuário, incluindo logout, nova senha aceita e senha anterior rejeitada | Confirmado como relato; não comprova revogação remota ou proteção abrangente de logs |
| Launcher local | Validação reportada pelo usuário | Não implica ativação fora do processo local |
| Fidelidade visual em desktop e viewport estreito | Sem QA autenticado concluído | Pendente |
| Matriz completa de erros e autorização | Testes e confirmações parciais das changes de origem | Pendente de fechamento/evidência consolidada |
| Revogação de tokens antigos | Não há mecanismo global comprovado | Pendente; tokens podem permanecer válidos até expirar |
| Proteção de logs | `Request History` Disabled e campos sensíveis confirmados pelo usuário para o endpoint de senha | Pendente em Error Logs, debugger e demais superfícies |
| Ativação permanente da alteração de senha | Flag usada somente em desenvolvimento explícito | Pendente de decisão operacional |

## Riscos e compensações

- [Risco] As changes de origem continuam abertas com conteúdo sobreposto → Não arquivá-las agora; após revisão canônica, reconciliar seus deltas para impedir duplicação.
- [Risco] A capability inicial ainda descreve dados estáticos de protótipo → Preservar a delimitação de seu propósito e não importar esses comportamentos para a capability operacional.
- [Risco] Confirmação de runtime do usuário pode ser confundida com QA independente → Identificar a fonte da evidência e manter abertas as matrizes visual, de autorização e de erro.
- [Risco] Logout local pode ser interpretado como revogação de todos os tokens → Declarar explicitamente que revogação remota não foi demonstrada.

## Plano de consolidação futura

1. Revisar a change e validar seus deltas em strict.
2. Obter evidência visual autenticada em desktop e viewport estreito e fechar as verificações de autorização/erro aplicáveis.
3. Revisar a segurança da troca de senha; manter a flag permanente desativada enquanto revogação e observabilidade não estiverem resolvidas ou formalmente aceitas.
4. Com autorização futura, executar o fluxo de arquivamento desta change para incorporar os deltas às specs oficiais.
5. Reconciliar cada change de origem com as specs oficiais antes de seu eventual arquivamento, preservando requisitos exclusivos e removendo apenas deltas já consolidados.
