# Tarefas

- [x] Verificar ausência de status no schema `user` e preparar `is_active` com padrão ativo.
- [x] Preparar endpoints explícitos de ativação/inativação, login, `/auth/me` e autorização central.
- [x] Adicionar status, confirmação e ações separadas na administração de usuários.
- [x] Publicar somente após revisão e executar cenários de inativação, sessão existente, reativação e preservação de histórico.

- [x] Investigar schema, autenticação, autorização e fluxos de usuários existentes.
- [x] Preparar schema, endpoints separados e bloqueio central das APIs de estoque.
- [x] Preparar UI de cadastro, edição, reset e troca obrigatória.
- [x] Atualizar cliente, sessão e proteção de rotas.
- [x] Validar XanoScripts, Reflex, OpenSpec e diff; executar dry-runs isolados.
- [x] Após publicação autorizada, verificar os cenários runtime de primeiro login, troca, reset, edição, acesso às rotas e aos endpoints.
- [x] Corrigir as comparações de `is_active` para recusar `false` estritamente e preservar `null` legado.
- [x] Validar no Xano publicado o bloqueio de usuários inativos, incluindo novo login, sessão existente, acesso protegido e reativação.