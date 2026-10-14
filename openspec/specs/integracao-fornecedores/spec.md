# integracao-fornecedores Specification

## Purpose
TBD - created by archiving change integracao-fornecedores. Update Purpose after archive.

## Requirements

### Requirement: Listagem real e busca de Fornecedores

A página `/fornecedores` MUST consultar `GET /suppliers` autenticado e percorrer a paginação real. MUST NOT exibir dados mockados ou valores fictícios. A tabela MUST exibir `ID`, `Nome / Razão social`, `Documento`, `Contato` e `Ações`, sem status ou exclusão. A busca MUST filtrar localmente por substring em nome/razão social e documento, sem diferenciar caixa ou acentos, sem chamadas por tecla.

#### Scenario: Abrir listagem
- **WHEN** usuário autenticado abre `/fornecedores`
- **THEN** Reflex carrega fornecedores do Xano e apresenta os campos reais sem status

#### Scenario: Buscar por nome ou documento
- **WHEN** usuário digita parte do nome/razão social ou documento
- **THEN** os resultados correspondentes são filtrados localmente, sem diferenciar caixa/acentos e sem request por caractere

### Requirement: Criar Fornecedor

Usuários com grant `supplier.create` MUST poder criar Fornecedor por `POST /suppliers`. Nome/razão social, tipo de documento CPF/CNPJ e documento MUST ser enviados conforme o modelo real; campos textuais MUST ser aparados. Nome e documento vazios MUST ser rejeitados e documento duplicado MUST produzir mensagem específica. A criação MUST bloquear envio duplicado e, após sucesso, fechar/limpar o formulário, atualizar a listagem e informar `Fornecedor cadastrado com sucesso.`.

#### Scenario: Criação válida
- **WHEN** usuário autorizado envia dados válidos
- **THEN** Xano persiste o Fornecedor, Reflex atualiza a listagem e mostra sucesso

#### Scenario: Entrada inválida ou documento duplicado
- **WHEN** nome/documento está vazio ou o documento já pertence a outro Fornecedor
- **THEN** a operação é rejeitada e a interface mostra a mensagem específica sem declarar sucesso

### Requirement: Editar Fornecedor

Usuários com grant `supplier.update` MUST poder carregar `GET /suppliers/by_id/{supplier_id}` e atualizar os dados cadastrais via `PATCH /suppliers/by_id/{supplier_id}`. A interface MUST manter o formulário aberto e preservar valores em caso de erro. Documento único MUST continuar protegido no backend. ID de Fornecedor usado em movimentações MUST permanecer estável.

#### Scenario: Atualização confirmada
- **WHEN** usuário autorizado salva alterações válidas
- **THEN** Reflex atualiza a listagem após confirmação e mostra `Fornecedor atualizado com sucesso.`

#### Scenario: Documento duplicado ou falha
- **WHEN** PATCH é recusado ou falha
- **THEN** formulário permanece aberto, sem informar sucesso, com mensagem amigável

### Requirement: Fornecedor sem gestão de status ou exclusão

A UX deste módulo MUST NOT exibir status, ativar, inativar ou excluir. Fornecedores permanecem disponíveis no seletor de Entrada; listagem do seletor MUST NOT filtrar pelo campo legado `status`. A edição cadastral MUST NOT alterar status nem remover IDs referenciados em movimentações.

#### Scenario: Selecionar Fornecedor em Entrada
- **WHEN** usuário autenticado carrega as opções da Entrada
- **THEN** fornecedores são carregados paginados sem filtro por status e o ID selecionado é enviado ao endpoint de Entrada

#### Scenario: Histórico existente
- **WHEN** um Fornecedor é editado
- **THEN** movimentações anteriores continuam referenciando o mesmo `supplier_id`; novos carregamentos mostram o nome atualizado do cadastro

### Requirement: Autorização

Leitura da página MUST exigir `supplier.read`. A interface MUST usar os `permission_codes` dinâmicos carregados pelo `AuthState` de `/auth/me`: exibir o cadastro somente com `supplier.create` e a edição somente com `supplier.update`. Os eventos que abrem e salvam o formulário MUST verificar novamente o grant correspondente; uma chamada direta ao evento de edição sem `supplier.update` MUST NOT carregar o detalhe nem abrir o formulário. A interface MUST NOT conceder ou alterar grants. A autorização definitiva MUST permanecer nos endpoints Xano.

#### Scenario: Usuário sem leitura tenta abrir a página
- **WHEN** um usuário sem `supplier.read` abre `/fornecedores` diretamente
- **THEN** a proteção da rota redireciona o usuário sem carregar a listagem

#### Scenario: Usuário com apenas leitura
- **WHEN** um usuário com `supplier.read` e sem `supplier.create` ou `supplier.update` abre `/fornecedores`
- **THEN** pode consultar e buscar, mas não vê os botões de cadastro ou edição

#### Scenario: Grants de cadastro e edição independentes
- **WHEN** os `permission_codes` retornados por `/auth/me` contêm somente `supplier.create` entre os grants de escrita de Fornecedor
- **THEN** a interface exibe o cadastro e oculta a edição
- **WHEN** contêm somente `supplier.update`
- **THEN** a interface exibe a edição e oculta o cadastro

#### Scenario: Tentativa direta de editar sem grant
- **WHEN** um usuário sem `supplier.update` invoca diretamente o evento de edição ou tenta salvar um formulário em modo de edição
- **THEN** o frontend bloqueia a operação sem carregar o detalhe ou chamar o PATCH
- **AND** o Xano continua sendo a autoridade final de autorização
