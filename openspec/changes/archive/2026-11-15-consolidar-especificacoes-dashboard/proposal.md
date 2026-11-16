# Proposta: consolidar especificações do Dashboard

## Por quê

Os requisitos atuais do Dashboard estão distribuídos em changes de integração, funcionamento e apresentação. A capability ainda não existe em `openspec/specs`, enquanto as mudanças de senha voluntária e identidade visual pertencem a capacidades distintas. Uma change documental temporária permite preparar contratos coesos e evitar que requisitos do protótipo inicial sejam interpretados como comportamento atual.

## O que muda

- Reunir os requisitos permanentes da experiência e dos dados do Dashboard em uma capability `dashboard`, sem restaurar cartões antigos ou dados de demonstração.
- Manter a paleta e o tema global em uma capability separada `identidade-visual`.
- Acrescentar à capability existente `integracao-usuarios` apenas o contrato de alteração voluntária da própria senha, referenciando os mecanismos gerais de autenticação já especificados.
- Restringir a capability `criar-projeto-inicial` ao escopo histórico do protótipo, para que seus indicadores e dados fictícios não sejam tratados como requisito do Dashboard integrado.
- Registrar a origem dos requisitos, evidências reportadas e validações ainda pendentes, sem modificar as changes de origem nem as specs oficiais nesta etapa.

## Capacidades

### Novas capacidades

- `dashboard`: dados reais, contagens atuais, grants, isolamento por sessão, cache, estados de falha, invalidação após escrita, gráfico de movimentações, notificações e composição específica do Dashboard.
- `identidade-visual`: tokens de tema e regras globais de legibilidade/responsividade, separados da apresentação específica do Dashboard.

### Capacidades modificadas

- `integracao-usuarios`: adicionar o requisito de troca voluntária da própria senha, sem duplicar autenticação geral, sessão, logout ou administração de usuários.
- `criar-projeto-inicial`: delimitar o requisito de indicadores estáticos como contrato da change de protótipo inicial, não como comportamento do produto integrado.

## Impacto

Esta change altera somente documentos OpenSpec. Os deltas serão aplicados futuramente a `openspec/specs` pelo fluxo de arquivamento do OpenSpec, após revisão e atendimento dos critérios de conclusão. As changes `integracao-dashboard-real`, `dashboard-funcional`, `aprimorar-visual-dashboard` e `identidade-visual-paleta-natural` permanecem abertas e intactas nesta etapa. Não haverá alteração de código, endpoint, dados, e-mail ou configuração.
