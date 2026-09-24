# Tasks

## 1. Consolidar a base de negócio e o escopo da change

- [x] 1.1 Confirmar que a fundação do domínio continua coerente com os conceitos de Categoria, Produto, Fornecedor, Estoque e Movimentação de Estoque.
- [x] 1.2 Confirmar que esta change não redefine a operação de movimentação de estoque e permanece focada no contrato dos cadastros básicos.
- [x] 1.3 Confirmar que a autenticação e autorização continuam sendo dependências do sistema e não parte do escopo funcional do cadastro básico.

## 2. Definir o contrato funcional de Categoria

- [x] 2.1 Registrar que Categoria é um registro base do sistema e deve permanecer coerente com o catálogo de produtos.
- [x] 2.2 Definir que a categoria deve ser reconhecida como suporte organizacional do Produto.
- [x] 2.3 Definir que alterações em categoria devem preservar a integridade do catálogo e evitar impactos não previstos em produtos ativos.
- [x] 2.4 Registrar que a categoria deve poder ser consultada, alterada e inativada sem conflitar com o contrato do domínio.

## 3. Definir o contrato funcional de Produto

- [x] 3.1 Registrar que Produto deve manter vínculo explícito com Categoria para operação normal.
- [x] 3.2 Definir que Produto deve permanecer relacionável ao estoque e às movimentações quando esses registros existirem, conforme o domínio já consolidado.
- [x] 3.3 Definir que Produto deve admitir criação, consulta, alteração e inativação como ciclo funcional mínimo.
- [x] 3.4 Registrar que Produto inativo ou desabilitado não deve ser utilizado normalmente em operações de estoque, sem definir a lógica operacional detalhada das movimentações.
- [x] 3.5 Definir que registros de Produto já utilizados em estoque ou movimentações não devem sofrer remoção destrutiva sem regra de negócio explicitamente definida.

## 4. Definir o contrato funcional de Fornecedor

- [x] 4.1 Registrar que Fornecedor é uma referência contextual ao domínio de entradas de estoque quando aplicável.
- [x] 4.2 Definir que Fornecedor não deve ser tratado como requisito universal para todos os produtos ou movimentações.
- [x] 4.3 Definir que a relação entre Fornecedor e entradas de estoque deve ser reconhecida sem incorporar a regra operacional detalhada das entradas em si.
- [x] 4.4 Registrar que o cadastro de fornecedor deve admitir criação, consulta, alteração e inativação conforme o ciclo de domínio.

## 5. Definir os relacionamentos entre registros e integridade histórica

- [x] 5.1 Registrar o relacionamento Produto–Categoria como base do catálogo funcional do sistema.
- [x] 5.2 Registrar o relacionamento Produto–Estoque como referência de uso do produto no estado atual do inventário.
- [x] 5.3 Registrar o relacionamento Produto–Movimentação como base de rastreabilidade e histórico do sistema.
- [x] 5.4 Registrar o relacionamento Fornecedor–entrada de estoque como contexto aplicável e não universal.
- [x] 5.5 Definir que Categoria e Produto já utilizados em estoque ou movimentações devem preservar sua integridade histórica, e que Fornecedor deve preservá-la quando estiver associado a uma entrada de estoque, sem tratar Fornecedor como requisito universal de movimentação.
- [x] 5.6 Definir que a exclusão definitiva dos registros permanece uma decisão pendente e não parte deste contrato funcional.

## 6. Validar a separação de responsabilidades da change

- [x] 6.1 Verificar que os requisitos de cadastro básico não incorporam regras de operação de movimentação de estoque.
- [x] 6.2 Verificar que os requisitos de cadastro básico não redefinem a matriz detalhada de permissões por perfil.
- [x] 6.3 Verificar que a dependência com autenticação e autorização permanece clara e consistente com a capability já consolidada.
- [x] 6.4 Verificar que o design mantém o Xano como autoridade de integridade e regras de negócio e o Reflex como camada de apresentação.

## 7. Preparar a mudança para revisão e implementação futura

- [x] 7.1 Garantir que os requisitos, cenários, design e tarefas estejam coerentes entre si.
- [x] 7.2 Garantir que os artefatos desta change expressem claramente o escopo, os limites e as decisões ainda pendentes de revisão do grupo.
- [x] 7.3 Garantir que nenhum passo desta change execute implementação, criação de tabelas, endpoints, telas ou trabalho de Apply.
