# Dashboard e Reposição de Estoque

## ADDED Requirements

### Requirement: Exibir identidade compartilhada e indicadores de compra

A sidebar MUST reutilizar exatamente a marca geométrica exibida na tela Login. O Dashboard MUST manter Produtos ativos, Estoque insuficiente, Alertas de estoque e Movimentações recentes; MUST NOT exibir cards de Categorias ou Fornecedores. MUST apresentar solicitações abertas com contagem real e autorização de leitura.

#### Scenario: Usuário com permissões de leitura abre o Dashboard

- **WHEN** a sessão validada possui os grants necessários
- **THEN** cada indicador mostra dados retornados pelo Xano
- **AND** a marca da sidebar corresponde à marca da tela de Login
- **AND** os cards de Categorias e Fornecedores não são renderizados

#### Scenario: Usuário sem grant de solicitações

- **WHEN** a sessão não possui `purchase_request.read`
- **THEN** a contagem privada de solicitações não é consultada nem substituída por zero fictício
- **AND** o estado sem acesso é apresentado sem ocultar os demais indicadores autorizados

### Requirement: Contar e alertar Produtos ativos insuficientes

O resumo de estoque do Dashboard MUST contar Produtos ativos com saldo zero ou saldo positivo menor que estoque mínimo. A contagem e os alertas MUST incluir Produtos com solicitação ativa. O card MUST navegar para a página de Reposição. Saldo ausente MUST ser erro explícito, não zero.

#### Scenario: Resumo do Dashboard sem permissão de compras

- **WHEN** uma sessão validada possui `stock.read` mas não possui `purchase_request.read`
- **THEN** o resumo de estoque insuficiente continua disponível com base somente em estoque e Produtos ativos
- **AND** Produtos com solicitação ativa continuam incluídos sem que o endpoint leia a tabela de solicitações
- **AND** a falha por saldo ausente continua explícita e não é convertida em saldo zero

#### Scenario: Produto tem saldo zero ou está abaixo do mínimo

- **WHEN** o Xano retorna Produto ativo com saldo zero ou abaixo do mínimo
- **THEN** ele conta no indicador e pode aparecer nos Alertas de estoque
- **AND** solicitação ativa não o remove desses indicadores

#### Scenario: Estoque é suficiente ou Produto está inativo

- **WHEN** Produto está inativo ou seu saldo é normal
- **THEN** ele não conta como necessidade de reposição

#### Scenario: Usuário abre a fila pelo card

- **WHEN** o usuário seleciona o card Estoque insuficiente
- **THEN** a aplicação navega para a página Reposição preservando a proteção de sessão e grants

### Requirement: Separar Produtos disponíveis dos já solicitados

A página Reposição MUST apresentar a seção “A solicitar” com Produtos ativos insuficientes sem solicitação ativa e a seção “Compra já solicitada” com Produtos ainda insuficientes que possuam solicitação ativa. As seções MUST ser distintas e não duplicar Produtos entre si.

#### Scenario: Criação confirmada de solicitação

- **WHEN** o backend confirma uma solicitação para um Produto
- **THEN** o Produto sai de “A solicitar” e aparece em “Compra já solicitada” se continuar insuficiente
- **AND** permanece no card e nos Alertas de estoque enquanto continuar insuficiente

#### Scenario: Solicitação foi cancelada ou rejeitada

- **WHEN** o Xano confirma estado terminal cancelado ou rejeitado e o saldo ainda é insuficiente
- **THEN** o Produto volta para “A solicitar” após revalidação

### Requirement: Criar pedido com formulário controlado pelo backend

A ação Solicitar compra MUST aparecer somente para usuário com `purchase_request.create` e elegibilidade atual reportada pelo backend. O formulário MUST preencher Produto, sugerir quantidade editável e oferecer urgência baixa, normal, alta ou crítica. O POST MUST ser revalidado pelo Xano e usar chave de idempotência.

#### Scenario: Quantidade sugerida

- **WHEN** saldo é menor que o mínimo
- **THEN** a sugestão inicial é a diferença entre mínimo e saldo
- **WHEN** saldo e mínimo são ambos zero
- **THEN** a sugestão inicial é uma unidade
- **AND** o usuário pode editar a quantidade, que permanece positiva

#### Scenario: Cancelar rascunho

- **WHEN** o usuário cancela o formulário antes do envio
- **THEN** o formulário fecha sem criar nem cancelar solicitação persistida

#### Scenario: POST confirmado ou de resultado ambíguo

- **WHEN** o Xano confirma o POST
- **THEN** o usuário vê confirmação de solicitação registrada e de e-mail não enviado nesta fase
- **WHEN** a resposta é ambígua por timeout ou indisponibilidade
- **THEN** a interface preserva a chave de idempotência e não inicia outra criação com chave nova

### Requirement: Preparar destinatário de e-mail com compatibilidade gradual

O formulário MUST conter Produto, quantidade, urgência e e-mail do destinatário. O e-mail MUST ser aparado e validado localmente. Durante a transição, a API MUST aceitar campo ausente/NULL para manter o cliente legado; se informado na API, o valor é validado, limitado a 254 caracteres e incluído na assinatura idempotente. Enquanto a flag Reflex estiver desabilitada, o cliente mantém o payload antigo sem o campo e bloqueia um endereço preenchido para não descartá-lo. O endereço só será obrigatório na API depois que o formulário atualizado estiver funcionando. Nenhuma fase local pode afirmar ou executar entrega de e-mail.

#### Scenario: Contrato de destinatário ainda desativado

- **WHEN** a integração gradual permanece desativada e o campo está vazio
- **THEN** o formulário pode continuar usando o payload legado sem destinatário
- **WHEN** um endereço é preenchido nessa versão
- **THEN** o envio é bloqueado com explicação de que o valor ainda não é persistido

#### Scenario: Contrato de destinatário habilitado

- **WHEN** o schema e o POST compatíveis foram publicados e o recurso local é habilitado
- **THEN** o formulário exige e envia endereço válido normalizado
- **AND** a chave idempotente da tentativa fica vinculada a esse destinatário
- **AND** o estado da solicitação permanece distinto do estado de entrega do e-mail

#### Scenario: Cliente legado durante o contrato de transição

- **WHEN** um cliente não envia `email_destinatario` ou envia NULL durante a transição
- **THEN** a solicitação continua compatível e armazena NULL
- **AND** o campo só poderá virar obrigatório após o formulário atualizado estar funcionando

### Requirement: Separar cancelamento persistido e preservar resultados em falha

A interface MUST exibir cancelamento persistido em ação separada do cancelamento de formulário e somente segundo grant e transição autorizada. Falhas/429 MUST NOT ser exibidas como lista vazia ou escrita concluída.

#### Scenario: Falha em leitura ou escrita

- **WHEN** uma consulta ou escrita retorna erro temporário
- **THEN** resultados anteriores podem permanecer visíveis identificados como potencialmente desatualizados
- **AND** nenhum dado de cache autoriza nova criação
- **AND** recuperação manual respeita cooldown e coordenador existentes
