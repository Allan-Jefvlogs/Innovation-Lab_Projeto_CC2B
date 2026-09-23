# Tasks

## 1. Revisar o contexto e a base de negócio

- [ ] 1.1 Revisar o contrato da fundação do domínio e confirmar que os conceitos de usuário, perfil, movimentação e estoque continuam consistentes com esta change.

- [ ] 1.2 Verificar que os perfis iniciais do projeto — Administrador, Estoquista e Usuário de consulta — estão representados no escopo desta change sem criar novos perfis não justificados.

## 2. Definir o contrato de autenticação

- [ ] 2.1 Documentar o requisito mínimo de autenticação para operações protegidas, distinguindo usuário autenticado de usuário não autenticado.

- [ ] 2.2 Definir a identidade do usuário como base do acesso e registrar que autenticação e autorização são responsabilidades distintas.

- [ ] 2.3 Confirmar que o contrato de autenticação permanece genérico e não fixa uma tecnologia específica de sessão, token ou mecanismo de autenticação.

## 3. Definir o contrato de autorização

- [ ] 3.1 Registrar a relação entre perfil e permissão como base da autorização do sistema, sem definir uma matriz final detalhada como decisão definitiva.

- [ ] 3.2 Identificar as operações protegidas que exigem autorização, incluindo gerenciamento de usuários e perfis, manutenção de dados de domínio, movimentações de estoque, consultas protegidas e informações gerenciais.

- [ ] 3.3 Confirmar que a autorização deve ser aplicada no backend Xano e não depender somente da interface Reflex.

## 4. Definir o contrato de respostas e rastreabilidade

- [ ] 4.1 Estabelecer que as respostas de autenticação e autorização devem ser distinguíveis por categoria de erro.

- [ ] 4.2 Definir que a identidade do usuário autenticado e autorizado deve ser preservada em toda entrada ou saída de estoque e permanecer rastreável na movimentação correspondente.

- [ ] 4.3 Confirmar que o frontend deve consumir essas respostas e apresentar feedback ao usuário sem reproduzir as regras de negócio ou autorização do backend.

## 5. Consolidar as decisões da change

- [ ] 5.1 Registrar as decisões arquiteturais que estabelecem o Xano como autoridade de autenticação, autorização, integridade e regras de negócio.

- [ ] 5.2 Registrar as responsabilidades do Reflex como camada de apresentação, interação, navegação e feedback, sem substituir as validações do backend.

- [ ] 5.3 Registrar como decisões pendentes os pontos que não devem ser definidos nesta change: método específico de autenticação, formato de sessão ou token e matriz detalhada de permissões.

## 6. Verificar a consistência interna da change

- [ ] 6.1 Verificar que os requisitos, cenários e decisões de design estão coerentes entre `proposal.md`, `spec.md`, `design.md` e `tasks.md`.

- [ ] 6.2 Verificar que nenhuma tarefa introduz implementação física, criação de endpoints, tabelas, componentes ou código fora do escopo definido para esta change.