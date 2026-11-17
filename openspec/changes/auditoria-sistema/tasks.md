# Tarefas

- [x] 1.1 Auditar a rota antiga, as dependências de movimentação, a autorização e as alterações já presentes no worktree.
- [x] 1.2 Definir acesso inicial administrativo sem criar grants ou alterar perfis.
- [x] 2.1 Criar localmente o schema, a função de gravação e o GET paginado de auditoria.
- [x] 2.2 Instrumentar cadastros e alterações de Produtos, Categorias, Fornecedores, Usuários e Perfis/Permissões, sem instrumentar entradas ou saídas de estoque.
- [x] 2.3 Manter solicitações de compra e eventos de e-mail fora do escopo desta entrega, conforme decisão de escopo.
- [ ] 2.4 Atomicidade revisada estruturalmente. O teste de rollback em runtime foi dispensado e não foi executado; rollback não comprovado.
- [x] 3.1 Implementar a página Reflex com filtros, paginação, estados de carregamento, erro e vazio, sem ações de edição ou exclusão.
- [x] 3.2 Trocar o item de menu e a rota sem remover as páginas e rotas de Entrada e Saída nem o GET `/movements`.
- [x] 3.3 Apresentar eventos com rótulos legíveis, resolver IDs de perfil por uma única consulta opcional e omitir valores pessoais ou campos desconhecidos.
- [x] 3.4 Exportar todas as páginas filtradas em PDF A4 paisagem, em memória, com limite total de 500 eventos e falha fechada diante de inconsistências.
- [x] 3.5 Cobrir formatação, privacidade, paginação, limites, erros e integridade estrutural do PDF com testes locais.
- [x] 4.1 Validar XanoScript, compilação Reflex, OpenSpec strict e diff.
- [ ] 4.2 Publicar seletivamente os componentes da Auditoria e confirmar a consulta como administrador; não há evidência local suficiente para confirmar esses critérios.
- [ ] 4.3 Confirmar que um usuário sem perfil administrativo não consegue consultar a Auditoria; não há evidência local suficiente para confirmar esse critério.
