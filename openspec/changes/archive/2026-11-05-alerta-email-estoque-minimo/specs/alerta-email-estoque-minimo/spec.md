# Specification: Alerta por e-mail de estoque abaixo do mínimo

## ADDED Requirements

### Requirement: Toda Saída que deixa o saldo abaixo do mínimo MUST disparar um alerta por e-mail

Após uma Saída confirmada pelo Xano na página de Saída, o frontend MUST comparar a quantidade disponível após a Saída com o `estoque_minimo` do Produto. A quantidade disponível MUST ser o `saldo_atual` da resposta ou, quando ele não vier, a quantidade disponível carregada na página menos a quantidade da Saída. Quando essa quantidade for menor que o `estoque_minimo`, o frontend MUST enviar um alerta pela função `enviar_email`, inclusive se o Produto já estava abaixo do mínimo antes da Saída. O alerta MUST NOT ser enviado antes da confirmação da Saída pelo Xano.

#### Scenario: Saída deixa o saldo abaixo do mínimo
- **WHEN** o estoque mínimo é 10, o saldo anterior é 12 e a Saída de 4 é confirmada
- **THEN** o frontend MUST enviar um alerta identificando o Produto, o saldo atual 8 e o mínimo 10

#### Scenario: Produto já abaixo do mínimo
- **WHEN** o estoque mínimo é 10, o saldo anterior é 8 e a Saída de 2 é confirmada
- **THEN** o frontend MUST enviar novo alerta com o saldo atual 6

#### Scenario: Resposta sem saldo_atual
- **WHEN** o estoque mínimo é 10, a quantidade disponível carregada é 12, a Saída de 4 é confirmada e a resposta não traz `saldo_atual`
- **THEN** o frontend MUST usar 8 como quantidade disponível e enviar o alerta

#### Scenario: Saída zera o estoque
- **WHEN** o estoque mínimo é 10 e a Saída confirmada deixa o saldo em 0
- **THEN** o frontend MUST enviar um alerta com assunto identificando "Sem estoque"

#### Scenario: Saldo igual ou acima do mínimo
- **WHEN** o saldo atual após a Saída é maior ou igual ao estoque mínimo
- **THEN** o frontend MUST NOT enviar alerta

#### Scenario: Saída rejeitada
- **WHEN** o Xano rejeita a Saída
- **THEN** o frontend MUST NOT enviar alerta

### Requirement: O alerta MUST ser enviado ao usuário logado

O destinatário MUST ser o e-mail do usuário logado que registrou a Saída, lido de `AuthState`. Quando o e-mail estiver vazio, o alerta MUST NOT ser enviado e a Saída MUST ser concluída normalmente.

#### Scenario: Usuário com e-mail
- **WHEN** o usuário logado com e-mail `almoxarife@exemplo.com` registra uma Saída que deixa o saldo abaixo do mínimo
- **THEN** `enviar_email` MUST receber `almoxarife@exemplo.com` como destinatário

#### Scenario: Usuário sem e-mail carregado
- **WHEN** o e-mail do usuário logado está vazio
- **THEN** nenhum e-mail MUST ser enviado e nenhuma mensagem de erro MUST ser exibida

### Requirement: O alerta MUST NOT afetar a Saída registrada

Falhas do alerta MUST NOT desfazer a Saída, MUST NOT substituir a mensagem de sucesso da Saída e MUST ser informadas em mensagem separada.

#### Scenario: Falha no envio
- **WHEN** `enviar_email` levanta `EmailEnvioError`
- **THEN** a tela MUST manter a mensagem de Saída registrada
- **AND** MUST informar que o alerta por e-mail não foi enviado

#### Scenario: Dados insuficientes
- **WHEN** a quantidade disponível após a Saída ou o `estoque_minimo` não podem ser determinados ou não são numéricos
- **THEN** o frontend MUST NOT enviar alerta e MUST NOT tratar a Saída como erro

### Requirement: O alerta MUST ser idempotente por Saída

O envio MUST usar a chave de idempotência `alerta-estoque-<movement_id>`, para que a mesma Saída não gere mais de um e-mail em caso de reenvio.

#### Scenario: Chave de idempotência
- **WHEN** o alerta de uma Saída com `movement_id` 42 é enviado
- **THEN** `enviar_email` MUST receber `chave_idempotencia = "alerta-estoque-42"`
