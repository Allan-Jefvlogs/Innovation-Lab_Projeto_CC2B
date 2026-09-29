# Tasks: Integração Reflex de Produto

## 1. Contratos e OpenSpec

- [x] 1.1 Inspecionar endpoints, schemas, permissões, relação Produto–Categoria e fluxos atuais do formulário.
- [x] 1.2 Registrar escopo, contratos, requisitos e tarefas desta integração, fora da change de autenticação.

## 2. Cliente Xano

- [x] 2.1 Implementar chamadas autenticadas para listar Categorias, criar, consultar, atualizar, ativar e inativar Produto.
- [x] 2.2 Mapear respostas de autorização, validação, unicidade, regra de negócio e não encontrado.
- [x] 2.3 Interpretar códigos funcionais em envelopes Xano, diferenciar duplicidade, Categoria inválida/inativa e erros de input na criação, mantendo fallback genérico para códigos desconhecidos.

## 3. Listagem e rotas

- [x] 3.1 Adicionar ação Editar usando o ID real do Xano.
- [x] 3.2 Registrar e proteger a rota dinâmica `/produtos/[product_route_id]/editar` e manter a criação acessível conforme perfil.
- [x] 3.3 Exibir ações de UX pela matriz inicial e manter autorização efetiva no Xano.

## 4. Criação

- [x] 4.1 Carregar Categorias ativas e ligar campos do formulário a State.
- [x] 4.2 Validar obrigatórios, evitar submissão duplicada, persistir por POST e retornar à listagem.
- [x] 4.3 Exibir loading, sucesso/erro e remover comportamento sem ação do botão atual.

## 5. Edição e status

- [x] 5.1 Buscar o Produto por ID e preencher os campos permitidos.
- [x] 5.2 Enviar PATCH parcial conforme contrato, incluindo limpeza explícita de descrição.
- [x] 5.3 Adicionar endpoint Xano local de ativação protegido por `product.update`; manter inativação existente protegida por `product.inactivate`.
- [x] 5.4 Manter status original e status escolhido separados; Ativar/Inativar apenas alterna o estado local at? Salvar altera??es.
- [x] 5.5 Após PATCH de edição bem-sucedido, redirecionar para `/produtos` para recarregar a lista; em falha, manter o formulário e os valores informados.
- [x] 5.6 Ap?s salvar a edi??o, redirecionar para `/produtos` somente quando todos os PATCHes necess?rios tiverem sucesso.
- [x] 5.7 Executar PATCH cadastral antes do PATCH de status e reconciliar a base original via GET quando houver falha parcial, mantendo os valores editados.
- [ ] 5.8 Publicar isoladamente no Xano remoto o endpoint de ativa??o ap?s dry-run aprovado; atualmente o endpoint existe somente no snapshot local.

## 6. Validação

- [x] 6.1 Validar XanoScript do endpoint local de ativação pelo Xano Developer MCP.
- [ ] 6.2 Executar `reflex compile`, validação OpenSpec strict e `git diff --check`.
- [ ] 6.3 Testar manualmente criação, leitura, atualização, duplicidade, categoria inativa, ativação/inativação e permissões com perfis diferentes.
- [x] 6.4 Revisar os arquivos desta change; não sincronizar o endpoint de ativação sem revisão/autorização.
