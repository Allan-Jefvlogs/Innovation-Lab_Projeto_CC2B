# experiencia-usuario Specification

## Purpose
Define a experiência de confirmação, apresentação de formulários e linguagem operacional do NextStock, incluindo a recuperação de senha exclusivamente demonstrativa.

## Requirements

### Requirement: Confirmação visual após sucesso
O sistema MUST exibir uma confirmação visual consistente e contextual somente depois que a operação existente retornar uma resposta válida de sucesso. Falhas, respostas inválidas e resultados ambíguos MUST permanecer como erro ou estado pendente, sem confirmação positiva.

#### Scenario: Operação confirmada
- **WHEN** uma criação, edição, mudança de status ou cancelamento é confirmada pelo serviço existente
- **THEN** o sistema apresenta um modal acessível com ícone de sucesso, título específico, mensagem curta e ação para fechar

#### Scenario: Operação falha ou não pode ser confirmada
- **WHEN** a chamada falha, a resposta é inválida ou o resultado permanece ambíguo
- **THEN** o sistema preserva o tratamento atual de erro/reconciliação e não apresenta sucesso

### Requirement: Formulários e justificativas claros
O sistema MUST apresentar formulários e diálogos de justificativa com hierarquia visual consistente, linguagem de negócio, dimensões adequadas e adaptação a telas estreitas, preservando campos, validações, bindings, autorizações e payloads existentes.

#### Scenario: Justificativa necessária
- **WHEN** uma operação exige justificativa
- **THEN** o diálogo explica claramente a ação, destaca o campo obrigatório e mantém a confirmação bloqueada enquanto a justificativa for inválida ou a operação estiver em andamento

### Requirement: Resumo de movimentação confirmado
O sistema MUST apresentar após uma entrada ou saída confirmada o tipo, produto, quantidade e unidade da operação. O saldo final só pode ser apresentado quando recebido em campo confiável do servidor ou obtido por consulta atualizada.

#### Scenario: Saldo final disponível na resposta
- **WHEN** a resposta validada da operação inclui o saldo atualizado
- **THEN** o resumo pode exibir esse saldo retornado

#### Scenario: Saldo final não disponível
- **WHEN** a resposta validada não inclui saldo atualizado
- **THEN** o resumo não calcula nem presume um saldo final

### Requirement: Linguagem voltada ao usuário
Mensagens visíveis MUST usar linguagem clara e contextualizada, sem referências de implementação desnecessárias. O sistema MUST preservar detalhes úteis de segurança, validação e falha, mantendo diagnósticos técnicos somente em logs internos apropriados.

#### Scenario: Mensagem de operação
- **WHEN** o sistema comunica sucesso, falha ou validação
- **THEN** a mensagem descreve a ação e o próximo passo em termos compreensíveis, sem ocultar falha nem alegar resultado não confirmado

### Requirement: Recuperação de senha demonstrativa
A rota `/recuperar-senha` MUST oferecer uma demonstração visual de recuperação de senha, validar localmente que o e-mail foi preenchido em formato válido e apresentar uma confirmação com retorno explícito à tela de login. Essa demonstração MUST NOT consultar a existência de usuários, enviar o e-mail a Xano ou a um serviço de e-mail, gerar tokens, persistir o e-mail ou a solicitação, nem alterar senhas.

#### Scenario: E-mail válido na demonstração
- **WHEN** o usuário informa um e-mail em formato válido e solicita a recuperação
- **THEN** a página apresenta uma confirmação visual genérica e permite retornar ao login por uma ação explícita
- **AND** o e-mail é usado transitoriamente somente para validação local no handler Reflex, sem envio a serviço externo ou persistência, e nenhuma recuperação real é iniciada.

#### Scenario: E-mail vazio ou malformado
- **WHEN** o campo não está preenchido ou o formato é inválido
- **THEN** a página apresenta a validação local e não abre a confirmação.
