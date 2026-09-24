# Proposal

## Why

A fundação do domínio do Sistema de Gerenciamento de Estoque já consolidou os conceitos centrais de Categoria, Produto, Fornecedor, Estoque e Movimentação de Estoque, além do contrato de autenticação e autorização que define que o backend é a autoridade para acesso e regras de negócio.

Apesar disso, o sistema ainda precisa estabelecer de forma explícita o contrato funcional dos cadastros básicos que sustentam as operações de estoque e o histórico do sistema. Sem esse alinhamento, o cadastro de categorias, produtos e fornecedores pode evoluir com regras divergentes, relacionamentos inconsistentes e impactos sobre estoque e movimentações que não sejam claramente previstos.

Esta change resolve a necessidade de definir um contrato funcional para os cadastros básicos do sistema, preservando a arquitetura definida pelo projeto: Reflex como frontend de apresentação e interação, Xano como autoridade para integridade e regras de negócio, e a autenticação/autorização conforme a capability já consolidada.

## What Changes

- Definir o contrato funcional para os cadastros básicos do sistema: categorias, produtos e fornecedores.
- Reforçar o relacionamento já consolidado entre Produto e Categoria.
- Definir a relação entre Produto, Estoque e Movimentação de Estoque.
- Definir a relação entre Fornecedor e entradas de estoque, quando aplicável.
- Estabelecer regras mínimas de criação, consulta, alteração e inativação dos cadastros.
- Definir critérios para a preservação da integridade dos registros já utilizados por estoque e movimentações, evitando remoção destrutiva sem regra de negócio explicitamente definida.
- Deixar explícito que a exclusão definitiva dos cadastros é uma decisão de regra de negócio a ser definida posteriormente, e não parte do contrato funcional desta change.
- Garantir que as regras de autonomia de acesso continuem sendo tratadas pela capability de autenticação e autorização já consolidada.
- Delimitar o escopo do cadastro básico para evitar mistura com regra de movimentação, dashboard, relatórios e demais capabilities futuras.

## Scope

### Incluído

- Contrato funcional de categorias.
- Contrato funcional de produtos.
- Contrato funcional de fornecedores.
- Relacionamento entre Produto e Categoria.
- Relacionamento entre Produto e Estoque.
- Relacionamento entre Produto e Movimentação de Estoque.
- Relacionamento contextual entre Fornecedor e entradas de estoque, quando aplicável.
- Regras mínimas de criação, consulta, alteração e inativação dos cadastros.
- Conservação da integridade dos registros quando houver uso em estoque e movimentações, sem remoção destrutiva sem regra de negócio definida.
- Dependência funcional com as regras de autenticação e autorização já consolidadas.
- Clarificação de que a exclusão definitiva dos registros permanece uma decisão de regra de negócio a ser definida posteriormente.

### Fora do escopo

- Implementação de código.
- Criação de tabelas, schemas físicos ou estruturas de banco.
- Definição de endpoints ou APIs concretas.
- Criação de telas, componentes ou fluxos de interface.
- Implementação de login, sessão, token ou regras específicas de autenticação.
- Definição detalhada da matriz final de permissões por perfil.
- Regras de movimentação de estoque em si, como entrada, saída, cálculo de saldo e histórico operacional detalhado.
- Dashboard, relatórios, importação em massa, integrações externas e demais capabilities não diretamente relacionadas aos cadastros básicos.
- Criação de novos perfis sem justificativa e revisão do grupo.

## Impact

- **Categoria:** passa a ser o eixo de organização dos produtos do sistema, com regras de uso e manutenção que preservem a integridade do catálogo.
- **Produto:** passa a ser o centro de relacionamento entre catálogo, estoque e movimentações, exigindo consistência na categoria, status e uso em operações de negócio. Um produto depende de uma Categoria válida para operação normal.
- **Fornecedor:** passa a ser o ponto de referência para a origem de produtos nas entradas de estoque, quando aplicável, e não é um requisito universal para todos os produtos ou movimentações.
- **Estoque e movimentações:** continuam dependentes dos cadastros básicos, pois o produto e o fornecedor são fundamentais para a integridade e a rastreabilidade das operações. Produto inativo ou desabilitado não deve ser utilizado normalmente em operações de estoque, sem antecipar aqui a lógica operacional detalhada dessas operações.
- **Xano:** continua como autoridade para validar as regras de integridade e garantir que o estado dos cadastros não comprometa o estoque ou o histórico.
- **Reflex:** deve consumir os contratos do backend sem duplicar regras de negócio na camada de apresentação.
- **Próximas changes:** o contrato desta capability serve de base para a próxima etapa funcional de movimentações de estoque e para as capacidades de dashboard e relatórios.

## Dependências

### Dependências com a fundação do domínio

- **Produto** depende de **Categoria**.
- **Produto** está associado a **Estoque** e a **Movimentação de Estoque**.
- **Fornecedor** participa das **entradas de estoque**.
- **Usuário** e **Perfil** já consolidados continuam sendo os atores que autorizam e auditam as operações.

### Dependências com a capability de autenticação e autorização

- Qualquer operação de cadastro, alteração, inativação ou consulta deve respeitar a identidade do usuário e as regras de acesso já definidas.
- O backend continua sendo o responsável pela aplicação da autorização.
- O frontend deve consumir o resultado da autorização sem tentar decidir a regra de negócio por si.
- Esta change não redefine a matriz detalhada de permissões; ela apenas reconhece que os cadastros básicos devem obedecer ao contrato já consolidado de autenticação e autorização.

### Dependências com o restante do sistema

- Os cadastros básicos sustentam a operação do estoque, o histórico de movimentações, os relatórios e futuras capacidades de consulta gerencial.
- Alterações em cadastro podem impactar a consistência do estoque e a rastreabilidade das movimentações.
- A regra operacional de entrada e saída de estoque continua sendo uma questão separada deste contrato funcional, e não deve ser incorporada como parte desta change.

## Riscos

- **Cadastros sem integridade:** um produto sem categoria válida, um fornecedor incompleto ou uma categoria vinculada indevidamente pode comprometer o funcionamento do estoque.
- **Desacoplamento entre domínio e acesso:** sem a regra de autorização correta, o cadastro pode ser alterado por usuários indevidos.
- **Vínculos não previstos:** a remoção destrutiva de registros já utilizados em movimentações pode gerar inconsistência histórica e de estoque; por isso, a regra de negócio deve ser explicitamente definida antes de qualquer exclusão definitiva.
- **Escopo ampliado demais:** misturar cadastros básicos com movimentação de estoque, dashboard, relatórios ou gestão de usuários pode diluir o objetivo da change.
- **Decisões prematuras:** definir uma matriz detalhada de permissões ou regras técnicas demais nesta fase pode congelar o escopo antes da revisão do grupo.
- **Ambiguidade na manutenção:** sem definir claramente criação, consulta, alteração e inativação, o sistema pode evoluir com comportamentos diferentes entre cadastros.

## Decisões de escopo a serem revisadas pelo grupo

As seguintes decisões permanecem pendentes e devem ser revisadas pelo grupo quando necessário, sem transformar a proposta em regra definitiva nesta fase:

- critérios exatos de unicidade e validação para categoria, produto e fornecedor;
- política de inativação versus exclusão lógica e remoção destrutiva, quando houver registros já utilizados por estoque ou movimentações;
- regras específicas de acesso por perfil para cada operação de manutenção;
- profundidade da matriz de permissões e sua relação com as futuras changes de estoque e relatórios.

Essas decisões não devem ser convertidas em regras definitivas antes da revisão do grupo, mas precisam ser reconhecidas como parte do contrato funcional a ser discutido na mudança correspondente. O caráter funcional desta change permanece centrado em cadastros básicos, não em regras operacionais de estoque nem em autenticação e autorização como tema principal de implementação.

## Status

Proposta de change revisada e ajustada conforme o Review, sem implementação de código, sem criação de tabelas, endpoints, componentes ou Apply
