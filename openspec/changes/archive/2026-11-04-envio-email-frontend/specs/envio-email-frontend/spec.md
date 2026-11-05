# Specification: Envio de e-mail pelo frontend Reflex

## ADDED Requirements

### Requirement: O frontend MUST oferecer uma função única de envio de e-mail

O serviço `Meu_projeto/services/email_service.py` MUST expor a função assíncrona `enviar_email`, que recebe destinatários, assunto, conteúdo HTML e/ou texto, e opcionalmente remetente, endereço de resposta e chave de idempotência. A função MUST enviar a mensagem pela API HTTP do Resend usando `httpx` e MUST retornar o identificador da mensagem devolvido pelo provedor.

#### Scenario: Envio aceito pelo provedor
- **WHEN** `enviar_email` é chamada com destinatário, assunto e conteúdo válidos e a chave está configurada
- **THEN** a função MUST fazer `POST https://api.resend.com/emails` com `Authorization: Bearer` e os campos `from`, `to`, `subject` e o conteúdo informado
- **AND** MUST retornar o `id` da resposta do Resend

#### Scenario: Remetente omitido
- **WHEN** `remetente` não é informado
- **THEN** a função MUST usar `RESEND_FROM_EMAIL`
- **AND** MUST usar `onboarding@resend.dev` quando `RESEND_FROM_EMAIL` também não estiver definida

#### Scenario: Endereço de resposta e idempotência
- **WHEN** `responder_para` e `chave_idempotencia` são informados
- **THEN** a requisição MUST conter `reply_to` no corpo e o cabeçalho `Idempotency-Key`

### Requirement: A função MUST validar os parâmetros antes de chamar o provedor

A função MUST rejeitar com `INVALID_INPUT`, sem fazer requisição, quando não houver destinatário, quando houver mais de 50 destinatários ou algum vazio, quando o assunto estiver vazio após trim ou quando nem `html` nem `texto` tiverem conteúdo.

#### Scenario: Conteúdo ausente
- **WHEN** `enviar_email` é chamada sem `html` e sem `texto`
- **THEN** a função MUST levantar `EmailEnvioError` com código `INVALID_INPUT`
- **AND** MUST NOT chamar o Resend

#### Scenario: Destinatário inválido
- **WHEN** `para` está vazio ou contém endereço sem `@`
- **THEN** a função MUST levantar `EmailEnvioError` com código `INVALID_INPUT`
- **AND** MUST NOT chamar o Resend

### Requirement: A chave MUST vir do ambiente e MUST NOT aparecer em erros

A chave MUST ser lida de `EMAIL_TOKEN` no momento da chamada. Quando ausente ou vazia, a função MUST levantar `EMAIL_CONFIGURATION_MISSING` sem fazer requisição. Mensagens de erro e logs produzidos pela função MUST NOT conter a chave. `.env.example` MUST documentar as variáveis sem valor real de chave.

#### Scenario: Chave ausente
- **WHEN** `EMAIL_TOKEN` não está definida
- **THEN** a função MUST levantar `EmailEnvioError` com código `EMAIL_CONFIGURATION_MISSING`
- **AND** MUST NOT chamar o Resend

#### Scenario: Erro do provedor não expõe a chave
- **WHEN** o Resend rejeita a requisição
- **THEN** a mensagem do erro levantado MUST NOT conter o valor de `EMAIL_TOKEN`

### Requirement: Falhas do provedor MUST resultar em erros identificáveis

A função MUST mapear respostas e falhas do Resend para `EmailEnvioError` com códigos distintos e MUST fazer uma única tentativa por chamada, sem retry automático.

#### Scenario: Rejeição do provedor
- **WHEN** o Resend responde com status 4xx diferente de 429
- **THEN** a função MUST levantar `EMAIL_PROVIDER_REJECTED`

#### Scenario: Limite de envio
- **WHEN** o Resend responde com status 429
- **THEN** a função MUST levantar `EMAIL_RATE_LIMITED`

#### Scenario: Provedor indisponível
- **WHEN** o Resend responde com status 5xx, ocorre timeout ou falha de transporte
- **THEN** a função MUST levantar `EMAIL_PROVIDER_UNAVAILABLE`
- **AND** MUST NOT repetir a requisição automaticamente

#### Scenario: Destinatário não permitido em modo de teste
- **WHEN** o remetente é `onboarding@resend.dev` e o destinatário não é o dono da conta Resend
- **THEN** a rejeição do provedor MUST resultar em `EMAIL_PROVIDER_REJECTED`
