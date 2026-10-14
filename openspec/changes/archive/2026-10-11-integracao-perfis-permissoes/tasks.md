# Tarefas

- [x] Inspecionar página, contrato Xano, tabelas, auditoria e guarda de rota.
- [x] Implementar cliente, estado e interface com dados reais.
- [x] Validar compile, OpenSpec strict e diff.
- [x] Retornar em `/auth/me` o perfil e os códigos efetivos do próprio usuário autenticado.
- [x] Condicionar sidebar e guarda de navegação aos grants efetivos e ao perfil administrator.
- [x] Documentar no design as permissões por item e a atualização dos grants na próxima restauração de sessão.
- [x] Adicionar `movement.read` e `report.read` ao catálogo e atualizar os grants default para preservar o acesso atual associado a `stock.read`.
- [x] Separar a sidebar e a guarda frontend para estoque, histórico e relatórios.
- [x] Exigir `movement.read` em `/movement_users`; permitir `movement.read` ou `report.read` em `/movements`; exigir `report.read` em resumo e opções de relatório.
- [x] Substituir filtros de relatório por endpoint mínimo de opções protegido por `report.read`.
- [x] Registrar estratégia de migração e não executar seed nem atualizar dados.
- [x] Executar e validar a migração controlada de movement.read/report.read, sem restaurar grants removidos manualmente nem alterar permissões não relacionadas.
- [x] Revisar os previews/dry-runs disponíveis das alterações Xano e confirmar somente CREATE/UPDATE esperados antes das publicações.
- [x] Validar com sessão runtime os grants independentes e acesso manual recusado pelo backend.
- [x] Após disponibilizar o frontend, verificar os cenários runtime com Líder, Almoxarife e Auxiliar.
- [x] Validar no Xano runtime que `/auth/me` retorna grants atuais próprios e que endpoints recusam rotas sem grants.
