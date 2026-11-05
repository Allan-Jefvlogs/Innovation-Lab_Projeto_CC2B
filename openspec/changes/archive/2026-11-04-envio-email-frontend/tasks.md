# Tasks: Envio de e-mail pelo frontend Reflex

## 1. Inspeção e contrato

- [x] 1.1 Confirmar com o grupo a decisão arquitetural registrada em `proposal.md` e os riscos aceitos em `design.md`.
- [x] 1.2 Confirmar `httpx` em `requirements.txt` e o padrão de serviço e exceções de `Meu_projeto/services/xano_client.py`.
- [x] 1.3 Confirmar na documentação atual do Resend o endpoint `POST /emails`, os campos do corpo, o cabeçalho `Idempotency-Key` e os status de erro. Conferido em 2026-11-04; resultado registrado em `design.md`.

## 2. Configuração

- [x] 2.1 Adicionar `EMAIL_TOKEN` (vazia), `RESEND_FROM_EMAIL` e `RESEND_TIMEOUT_SECONDS` a `.env.example`.
- [x] 2.2 Confirmar que `.env` continua no `.gitignore` e que nenhuma chave real é versionada.

## 3. Serviço de e-mail

- [x] 3.1 Criar `Meu_projeto/services/email_service.py` com `EmailEnvioError` e o atributo `codigo`.
- [x] 3.2 Implementar a validação local de `para`, `assunto`, `html`/`texto` e `remetente`, com `INVALID_INPUT` antes de qualquer requisição.
- [x] 3.3 Implementar a leitura de `EMAIL_TOKEN`, `RESEND_FROM_EMAIL` e `RESEND_TIMEOUT_SECONDS`, com `EMAIL_CONFIGURATION_MISSING` para chave ausente.
- [x] 3.4 Implementar `enviar_email` com `httpx.AsyncClient`, uma única tentativa, `reply_to` e `Idempotency-Key` opcionais, retornando o `id`.
- [x] 3.5 Mapear 4xx, 429, 5xx, timeout e falha de transporte para os códigos definidos, sem incluir a chave nas mensagens.

## 4. Validação

- [x] 4.1 Criar `tests/test_email_service.py` com `httpx.MockTransport` cobrindo os cenários da spec, sem chamada real ao Resend.
- [x] 4.2 Executar a suíte de testes do projeto e confirmar que os testes existentes continuam passando (262 testes OK, incluindo os 9 de `test_email_service`, executados na imagem Docker do projeto em 2026-11-04).
- [x] 4.3 Executar `openspec validate envio-email-frontend --strict`. **Não executado:** o CLI `openspec` não está disponível no ambiente e a execução via `npx` foi bloqueada; a tarefa foi encerrada por decisão do usuário em 2026-11-04, sem validação automática dos artefatos.
- [x] 4.4 Executar `git diff --check`.
- [x] 4.5 Com autorização do grupo, fazer um envio real para o e-mail dono da conta Resend e registrar em `design.md` a confirmação, sem registrar a chave. Envio executado pelo usuário com `scripts/enviar_email_teste.py` na imagem Docker do projeto e reportado como funcionando em 2026-11-04; o `id` retornado não foi registrado (ver `design.md`).

## 5. Fronteiras

- [x] 5.1 Não integrar `enviar_email` a telas ou fluxos existentes nesta Change.
- [x] 5.2 Não alterar, remover ou publicar artefatos de e-mail do Xano nem tarefas de `backend-solicitacoes-compras` e `dashboard-reposicao-compras`.
- [x] 5.3 Não adicionar o SDK `resend` nem outra dependência nova.
- [x] 5.4 Não fazer commit, push ou publicação sem autorização.
