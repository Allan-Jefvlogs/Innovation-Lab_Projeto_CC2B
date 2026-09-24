# Tasks

## 1. Consolidar contexto e limites

- [x] 1.1 Confirmar que a fundação do domínio sustenta os conceitos de Produto, Estoque e Movimentação usados nesta change.
- [x] 1.2 Confirmar que autenticação/autorização e cadastros básicos são dependências e não serão redefinidos.
- [x] 1.3 Confirmar que a change permanece contratual e não inclui código, tabelas, schemas, endpoints, APIs, telas ou alterações em Xano e Reflex.

## 2. Definir o contrato comum da movimentação

- [x] 2.1 Registrar que toda movimentação possui exatamente um tipo: entrada ou saída.
- [x] 2.2 Registrar que toda movimentação confirmada possui Produto relacionado e usuário responsável.
- [x] 2.3 Registrar que a movimentação confirmada preserva quantidade positiva, motivo, data e hora e dados contextuais aplicáveis.
- [x] 2.4 Registrar observação como dado contextual sem fixar sua obrigatoriedade.

## 3. Definir o contrato de entrada

- [x] 3.1 Definir o comportamento observável de uma entrada confirmada.
- [x] 3.2 Registrar que uma entrada aumenta conceitualmente o saldo disponível do Produto.
- [x] 3.3 Registrar que Fornecedor pode contextualizar a entrada quando aplicável, sem requisito universal.
- [x] 3.4 Preservar como pendentes a exigência de Fornecedor em tipos específicos e o uso de Fornecedor inativo.

## 4. Definir o contrato de saída

- [x] 4.1 Definir o comportamento observável de uma saída confirmada.
- [x] 4.2 Registrar que uma saída reduz conceitualmente o saldo disponível do Produto.
- [x] 4.3 Registrar que uma saída não exige Fornecedor.
- [x] 4.4 Registrar que uma saída acima do saldo disponível deve ser rejeitada e não pode produzir saldo negativo.
- [x] 4.5 Preservar como pendente a decisão sobre aceitar saída exatamente igual ao saldo disponível.

## 5. Definir quantidade, Produto e dependências de cadastro

- [x] 5.1 Definir que quantidade menor ou igual a zero rejeita a operação.
- [x] 5.2 Registrar que unidade e precisão da quantidade permanecem pendentes.
- [x] 5.3 Manter a relação com Produto e Categoria válida conforme os contratos consolidados.
- [x] 5.4 Registrar que Produto inativo ou desabilitado não deve ser utilizado normalmente, mantendo pendentes os critérios exatos.
- [x] 5.5 Preservar como pendentes o efeito de Categoria inativa e os critérios adicionais de Categoria válida.

## 6. Definir usuário e autorização

- [x] 6.1 Registrar que a operação exige usuário autenticado e autorizado.
- [x] 6.2 Preservar a identidade do usuário responsável na movimentação confirmada e no histórico.
- [x] 6.3 Manter Xano como autoridade de autenticação/autorização da operação.
- [x] 6.4 Não definir matriz detalhada de permissões nem criar novos perfis.

## 7. Definir saldo e situação do estoque

- [x] 7.1 Definir a atualização conceitual do saldo somente após confirmação.
- [x] 7.2 Registrar a relação entre saldo disponível e estoque mínimo.
- [x] 7.3 Definir os estados conceituais de estoque normal, abaixo do mínimo e sem estoque conforme a fundação do domínio.
- [x] 7.4 Preservar como pendente o tratamento detalhado de estoque mínimo igual a zero e demais classificações futuras.
- [x] 7.5 Manter dashboard e relatórios fora desta capability.

## 8. Definir histórico, rejeição e integridade

- [x] 8.1 Definir os dados conceituais identificáveis de uma movimentação confirmada no histórico.
- [x] 8.2 Garantir que rejeição não confirme alteração no saldo.
- [x] 8.3 Garantir que rejeição não crie movimentação confirmada no histórico.
- [x] 8.4 Preservar movimentações confirmadas e a integridade histórica.
- [x] 8.5 Registrar que imutabilidade, correção, cancelamento, estorno e auditoria separada permanecem pendentes.

## 9. Definir responsabilidades arquiteturais

- [x] 9.1 Registrar Xano como autoridade de validação, integridade, confirmação/rejeição e estado do estoque.
- [x] 9.2 Registrar Reflex como apresentação, interação, envio e exibição de resultados, sem autonomia de segurança.
- [x] 9.3 Registrar OpenSpec como contrato funcional e Git como versionamento.
- [x] 9.4 Manter fora desta change transação, persistência, concorrência e estruturas físicas.

## 10. Garantir rastreabilidade entre artefatos

- [x] 10.1 Mapear cada requisito da Specification para uma ou mais tarefas verificáveis.
- [x] 10.2 Conferir que nenhuma tarefa introduz regra ausente da Proposal, Explore ou specifications consolidadas.
- [x] 10.3 Conferir que as decisões pendentes da Proposal permanecem pendentes na Specification, Design e Tasks.

## 11. Revisar limites e preparar etapas futuras

- [x] 11.1 Verificar a separação entre contrato da movimentação, implementação futura no Xano, integração futura no Reflex e consultas posteriores.
- [x] 11.2 Verificar que dashboard, relatórios, gestão de usuários, autenticação como implementação, integrações externas e funcionalidades financeiras permanecem fora do escopo.
- [x] 11.3 Revisar a coerência final entre Proposal, Specification, Design e Tasks.
- [x] 11.4 Confirmar que esta change está preparada para Review sem executar Apply ou Archive.
