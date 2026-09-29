# Specification: Integração Reflex de Produto

## ADDED Requirements

### Requirement: Leitura de Produtos do Xano

O Reflex MUST carregar a listagem e o detalhe de Produto pelo Xano usando o token Bearer da sessão. O Xano MUST exigir `product.read`. A interface MUST exibir loading e erro sem substituir falhas por dados mockados. A listagem MUST usar o ID Xano para ações e respeitar o envelope paginado.

#### Scenario: Listagem carregada
- **WHEN** usuário autenticado abre `/produtos`
- **THEN** Reflex consulta `GET /products` com Bearer e mostra os itens reais retornados

#### Scenario: Leitura recusada
- **WHEN** Xano responde que a sessão ou permissão não autoriza leitura
- **THEN** a interface mostra erro amigável e não apresenta dados mockados como fallback

### Requirement: Criação de Produto

O Reflex MUST enviar `POST /products` com `codigo`, `nome`, `categoria_id`, `unidade_medida`, `estoque_minimo` e `descricao` somente quando preenchida. A criação MUST validar os campos obrigatórios e MUST NOT permitir múltiplos envios enquanto estiver em andamento. O backend MUST exigir `product.create`, Categoria existente e ativa e unicidade de `codigo`.

#### Scenario: Criação válida
- **WHEN** usuário autorizado envia os campos obrigatórios válidos
- **THEN** o produto é persistido pelo Xano e a interface retorna à listagem atualizada

#### Scenario: Erro de validação, duplicidade ou autorização
- **WHEN** Xano rejeita a criação
- **THEN** a interface mostra mensagem amigável e mantém o formulário sem exibir sucesso

#### Scenario: Erros específicos de criação
- **WHEN** Xano retorna `DUPLICATE_VALUE`, `BUSINESS_RULE_VIOLATION` ou um erro de input para `POST /products`
- **THEN** Reflex informa respectivamente que o código enviado já existe, que a Categoria não existe ou está inativa, ou que os campos/estoque mínimo devem ser revisados; um HTTP 400 sem código reconhecido usa mensagem genérica e nunca é classificado automaticamente como duplicidade

### Requirement: Atualização de Produto

O Reflex MUST carregar `/produtos/{id}/editar` pelo ID real e consultar `GET /products/by_id/{product_id}`. A edição MUST enviar somente campos aceitos por `PATCH /products/by_id/{product_id}`; status e ID MUST NOT ser enviados nesse PATCH. O backend MUST exigir `product.update` e validar unicidade e nova associação de Categoria.

#### Scenario: Editar Produto existente
- **WHEN** usuário autorizado altera campos permitidos
- **THEN** Reflex envia PATCH ao Xano e, somente após sucesso, redireciona para `/produtos`, que busca novamente a lista real

#### Scenario: Falha ao editar Produto
- **WHEN** Xano ou a conexão rejeita o PATCH
- **THEN** Reflex permanece no formulário de edição, preserva os campos e mostra o erro

#### Scenario: ID inexistente ou atualização recusada
- **WHEN** Xano responde `NOT_FOUND`, `PERMISSION_DENIED`, `DUPLICATE_VALUE`, `INVALID_INPUT` ou regra de negócio
- **THEN** Reflex exibe feedback adequado e não informa sucesso

### Requirement: Ativação e Inativação lógica

Produto MUST permanecer persistido e MUST usar `status` `ativo` ou `inativo`; exclusão física MUST NOT ser oferecida. O formulário MUST manter `original_product_status` separado do status escolhido atualmente. Clicar em Ativar/Inativar MUST alterar somente o estado local e MUST NOT chamar o Xano. Ao clicar em Salvar alterações, Reflex MUST enviar o PATCH cadastral quando houver diferenças e chamar `PATCH /products/by_id/{product_id}/inactivate` ou `PATCH /products/by_id/{product_id}/activate` somente quando o status escolhido diferir do original. A inativação exige `product.inactivate`; a ativação exige `product.update`. Reflex MUST redirecionar para `/produtos` somente depois que todas as operações necessárias retornarem sucesso.

#### Scenario: Alterar status sem salvar
- **WHEN** usuário alterna Ativar/Inativar no formulário
- **THEN** o status exibido e o rótulo do botão mudam, sem qualquer chamada ao Xano

#### Scenario: Salvar somente alteração de status
- **WHEN** usuário salva um status diferente do original
- **THEN** Reflex chama somente o endpoint correspondente à transição e redireciona para `/produtos` após sucesso

#### Scenario: Salvar campos e status juntos
- **WHEN** usuário altera campos cadastrais e status e clica em Salvar alterações
- **THEN** Reflex envia o PATCH cadastral e depois o PATCH de status necessário; redireciona somente após ambos terem sucesso

#### Scenario: Falha após salvar campos cadastrais
- **WHEN** o PATCH cadastral retorna sucesso, mas o PATCH de status falha
- **THEN** Reflex permanece na edição, informa a falha parcial, recarrega o produto do Xano para atualizar a base original e mantém os campos e status escolhido no formulário

#### Scenario: Falha sem alteração parcial
- **WHEN** qualquer operação necessária falha antes de uma atualização anterior ter sucesso
- **THEN** Reflex permanece na edição, preserva os valores e mostra o erro sem redirecionar

### Requirement: Proteção de rotas e ações

As rotas de criação e edição MUST reutilizar a autenticação e o guard de rota existente. O Auxiliar de almoxarifado MUST NOT receber ações de escrita na UX sob a matriz inicial. Toda escrita MUST ser autorizada pelo Xano pelos grants atuais; o perfil no frontend MUST NOT substituir essa validação.

#### Scenario: Acesso direto à edição sem perfil de escrita na UX
- **WHEN** usuário Auxiliar tenta abrir rota de edição pela URL
- **THEN** o guard redireciona para `/dashboard`

#### Scenario: Chamada sem grant de escrita
- **WHEN** usuário consegue acionar uma ação mas não possui grant atual
- **THEN** Xano rejeita a operação e Reflex apresenta o erro sem alterar dados
