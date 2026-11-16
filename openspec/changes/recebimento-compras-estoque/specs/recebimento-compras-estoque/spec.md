## ADDED Requirements

### Requirement: Vincular explicitamente a entrada ao pedido

O backend MUST atualizar compra somente para entrada com vínculo explícito persistido e validado. MUST NOT inferir vínculo pelo produto, texto livre ou saldo. Entradas avulsas MUST preservar seu comportamento sem alterar compras.

#### Scenario: Entrada sem vínculo
- **WHEN** uma entrada avulsa aumenta o saldo do produto
- **THEN** o saldo e movimento são registrados, mas nenhum pedido é recebido ou concluído por inferência

#### Scenario: Produto ou unidade incompatível
- **WHEN** o vínculo aponta para outro produto ou a unidade diverge do snapshot do pedido
- **THEN** a operação vinculada é rejeitada sem alterar saldo, pedido ou histórico

### Requirement: Acumular recebimentos confirmados

O backend MUST aceitar recebimentos em aguardando_recebimento e recebimento_parcial, somando somente entradas vinculadas confirmadas. Atualização do saldo, movimento, pedido e evento recebimento_registrado MUST compartilhar uma transação. O seletor manual MUST NOT permitir recebimento_parcial ou concluida.

#### Scenario: Parcial e entradas sucessivas
- **WHEN** um pedido de 15 KG recebe 5 KG e depois 4 KG por entradas distintas válidas
- **THEN** o acumulado é 9 KG, o status é recebimento_parcial e active_product_id permanece ativo

#### Scenario: Recebimento total
- **WHEN** o mesmo pedido recebe os 6 KG restantes
- **THEN** o acumulado é 15 KG, o status é concluida, a chave ativa é liberada e cada entrada tem seu evento com movimento identificável

#### Scenario: Pedido parcial fora da Reposição
- **WHEN** uma entrada parcial torna o estoque suficiente
- **THEN** o produto pode sair da Reposição, mas o pedido permanece consultável como recebimento_parcial em Compras

#### Scenario: Falha em gravação
- **WHEN** uma gravação necessária da entrada vinculada falha
- **THEN** a transação não retorna sucesso e deve reverter as gravações, sem declarar rollback comprovado antes de validação funcional

### Requirement: Impedir contagem repetida

Uma tentativa lógica MUST ter chave de recebimento persistida com restrição UNIQUE. Repetição compatível MUST reutilizar o movimento sem incrementar novamente estoque ou recebido; chave com payload diferente MUST ser rejeitada. Timeout MUST NOT gerar nova chave ou retry automático.

#### Scenario: Repetição após resposta perdida
- **WHEN** uma entrada confirmada é repetida com a mesma chave e payload
- **THEN** retorna referência ao movimento persistido, sem segundo movimento nem segundo evento de recebimento

#### Scenario: Pedido legado sem unidade
- **WHEN** um pedido anterior não possui unidade preservada confirmada
- **THEN** o recebimento exige conferência e procedimento autorizado, sem inferência retroativa

#### Scenario: Excesso de recebimento
- **WHEN** a entrada vinculada excede a quantidade restante
- **THEN** o backend rejeita integralmente a operação antes das gravações, sem truncar quantidades

### Requirement: Preservar autorização e ativação compatível

Entrada vinculada MUST exigir stock.entry e purchase_request.read, com acesso ao pedido limitado ao proprietário ou ao escopo global autorizado por manage/administrador. O perfil Compras MUST NOT receber stock.entry automaticamente. A interface MUST manter o vínculo desabilitado até schema/APIs publicados e validados e MUST NOT consultar pedidos automaticamente na carga da Entrada.

#### Scenario: Seleção manual e leitura isolada
- **WHEN** operador autorizado consulta compras do produto na Entrada
- **THEN** a consulta é explícita e paginada, sem selecionar pedido por inferência ou expor pedidos além do escopo da sessão

#### Scenario: Publicação ainda pendente
- **WHEN** a flag NEXSTOCK_PURCHASE_RECEIPTS_ENABLED está desligada
- **THEN** o formulário preserva o payload avulso anterior sem enviar os campos do contrato novo
