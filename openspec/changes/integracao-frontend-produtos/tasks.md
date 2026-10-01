# Tasks: Integração Reflex de Produto

## 1. Contratos e OpenSpec

- [x] 1.1 Inspecionar endpoints, schemas, permissões, relação Produto–Categoria e fluxos atuais do formulário.
- [x] 1.2 Registrar escopo, contratos, requisitos e tarefas desta integração, fora da change de autenticação.

## 2. Cliente Xano

- [x] 2.1 Implementar chamadas autenticadas para listar Categorias, criar, consultar, atualizar, ativar e inativar Produto.
- [x] 2.2 Mapear respostas de autorização, validação, unicidade, regra de negócio e não encontrado.
- [x] 2.3 Interpretar códigos funcionais em envelopes Xano, diferenciar duplicidade, Categoria inválida/inativa e erros de input na criação, mantendo fallback genérico para códigos desconhecidos.

## 3. Listagem e rotas

- [x] 3.6 Filtrar em memória a listagem por substring case-insensitive e accent-insensitive em código, nome e Categoria, com resultados reativos e mensagens distintas para lista vazia e busca sem correspondência.
- [x] 3.1 Adicionar ação Editar usando o ID real do Xano.
- [x] 3.2 Registrar e proteger a rota dinâmica `/produtos/[product_route_id]/editar` e manter a criação acessível conforme perfil.
- [x] 3.3 Exibir ações de UX pela matriz inicial e manter autorização efetiva no Xano.
- [x] 3.4 Buscar Categorias sem filtro de status e paginar em blocos de at? 100 quando necess?rio; mapear `categoria_id` para `nome` em mem?ria e exibir fallback para refer?ncia ausente/inv?lida.
- [x] 3.5 Consultar as páginas de `GET /stock` com `stock.read`, associar por `product_id`, exibir quantidade e situação do Xano e manter o status cadastral separado.

## 4. Criação

- [x] 4.1 Carregar Categorias ativas e ligar campos do formulário a State.
- [x] 4.2 Validar obrigatórios, evitar submissão duplicada, persistir por POST e retornar à listagem.
- [x] 4.3 Exibir loading, sucesso/erro e remover comportamento sem ação do botão atual.
- [x] 4.4 Usar select compartilhado de unidades permitidas na criação e enviar somente o código canônico em maiúsculas.
- [x] 4.5 Carregar Fornecedores ativos pelo Xano e permitir salvar Produto sem Fornecedor padrão ou com o ID selecionado.
- [x] 4.6 Usar seletores pesquisáveis para Categoria e Fornecedor padrão, com busca local parcial sem acentos, IDs como valores e paginação incremental explícita.
- [x] 4.7 Extrair o seletor pesquisável para helper compartilhado, reutilizável pelas relações da Entrada e futuras relações.

## 5. Edição e status

- [x] 5.1 Buscar o Produto por ID e preencher os campos permitidos.
- [x] 5.2 Enviar PATCH parcial conforme contrato, incluindo limpeza explícita de descrição.
- [x] 5.3 Adicionar endpoint Xano local de ativação protegido por `product.update`; manter inativação existente protegida por `product.inactivate`.
- [x] 5.4 Manter status original e status escolhido separados; Ativar/Inativar apenas alterna o estado local at? Salvar altera??es.
- [x] 5.5 Após PATCH de edição bem-sucedido, redirecionar para `/produtos` para recarregar a lista; em falha, manter o formulário e os valores informados.
- [x] 5.6 Ap?s salvar a edi??o, redirecionar para `/produtos` somente quando todos os PATCHes necess?rios tiverem sucesso.
- [x] 5.7 Executar PATCH cadastral antes do PATCH de status e reconciliar a base original via GET quando houver falha parcial, mantendo os valores editados.
- [x] 5.9 Reutilizar o select de unidades permitidas na edição e normalizar unidades históricas reconhecidas para maiúsculas.
- [x] 5.10 Carregar vínculo padrão existente, preservar Fornecedor inativo como opção atual e permitir limpeza/alteração para Fornecedor ativo.
- [ ] 5.8 Publicar isoladamente no Xano remoto o endpoint de ativa??o ap?s dry-run aprovado; atualmente o endpoint existe somente no snapshot local.

## 6. Validação

- [x] 6.1 Validar XanoScript do endpoint local de ativação pelo Xano Developer MCP.
- [x] 6.2 Executar `reflex compile --dry`, validação OpenSpec strict e `git diff --check`.
- [ ] 6.3 Testar manualmente criação, leitura de produtos/categorias/estoque, paginação de saldos, saldo ausente, situações retornadas, atualização, duplicidade, categoria inativa, ativação/inativação e permissões com perfis diferentes.
- [ ] 6.5 Testar seleção sem fornecedor, fornecedor ativo, edição com vínculo atual inativo, limpeza explícita e rejeição backend de nova associação inválida.
- [x] 6.4 Revisar os arquivos desta change; não sincronizar o endpoint de ativação sem revisão/autorização.
- [ ] 6.6 Testar manualmente busca parcial, caixa/acentos, seleção pelo rótulo com envio de ID, carregamento de página adicional e preservação de relações inativas.
