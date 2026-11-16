# Tarefas

## 1. Preparar a consolidação documental

- [x] 1.1 Inventariar as specs oficiais existentes e ler as quatro specs de origem; confirmar que ainda não há capability oficial `dashboard`.
- [x] 1.2 Mapear requisitos repetidos e exclusivos, mantendo `identidade-visual` separada e a alteração de senha em `integracao-usuarios`.
- [x] 1.3 Criar proposal, design e deltas sem editar changes de origem ou `openspec/specs`; conferir os caminhos com o CLI.
- [x] 1.4 Validar a change com `openspec.cmd validate consolidar-especificacoes-dashboard --strict` e corrigir somente problemas documentais desta change.

## 2. Rastreamento e reconciliação documental

As verificações abaixo permanecem abertas e são acompanhadas nas changes de origem. Esta seção é um mapa de rastreabilidade, não uma lista de tarefas concluídas ou transferidas.

- QA visual autenticado em desktop e viewport estreito: `aprimorar-visual-dashboard` tarefas 2.2, 2.5 e 2.7; `identidade-visual-paleta-natural` tarefa 5. A validação visual geral do Dashboard também permanece em `dashboard-funcional` tarefa 3.7.
- Estados de erro, ausência de permissão e isolamento de sessão: `integracao-dashboard-real` tarefa 3.3; `dashboard-funcional` tarefas 4.3 e 4.7, além das verificações de runtime relacionadas listadas em seu `tasks.md`.
- Revogação de JWTs antigos: `dashboard-funcional` tarefas 4.4, 4.7 e 178. O logout local não comprova revogação remota.
- Proteção de Error Logs, debugger e demais superfícies: `dashboard-funcional` tarefas 4.8 e 176. Request History desabilitado e inputs sensíveis não comprovam mascaramento abrangente.
- Decisão sobre ativação permanente da alteração de senha: `dashboard-funcional` tarefa 4.8 e tarefas 176–178. A flag permanece desligada por padrão fora do launcher local explícito.

- [x] 2.7 Antes de considerar esta change concluída, verificar e registrar numa matriz que: cada requisito dos três deltas está mapeado à origem, à classificação compartilhado/exclusivo/obsoleto, à spec oficial de destino e ao tipo/estado da evidência; `dashboard` e `identidade-visual` não existem previamente e a adição a `integracao-usuarios` não duplica nem contradiz requisito oficial; as quatro changes de origem têm seus deltas repetidos, requisitos exclusivos e reconciliações futuras identificados; e todas as pendências técnicas, visuais e de segurança continuam abertas nas origens. Distinguir inspeção de código, teste local, relato do usuário, validação remota e pendente, sem tratar relato/teste local como prova de runtime. Verificar referências, executar `openspec.cmd validate consolidar-especificacoes-dashboard --strict` e `git diff --check` nos documentos alterados; anexar a matriz/documentar resultados sem arquivar changes.
