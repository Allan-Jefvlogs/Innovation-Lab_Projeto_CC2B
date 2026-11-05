# Design: Envio de e-mail pelo frontend Reflex

## Estado local relevante

- `Meu_projeto/services/xano_client.py` já usa `httpx.AsyncClient`, lê configuração por `os.getenv` e define exceções próprias (`XanoError` e subclasses).
- `requirements.txt` já contém `httpx==0.28.1`; o SDK `resend` não está instalado.
- `.env` está no `.gitignore`; `.env.example` é versionado e hoje documenta apenas `XANO_API_BASE_URL`.
- O Xano possui uma versão local, não publicada, do envio pelo Resend em `xano/function/inventory/dispatch_purchase_request_email.xs`. Esta Change não a reutiliza nem a altera.

## Local da implementação

Novo módulo `Meu_projeto/services/email_service.py`, ao lado de `xano_client.py`. A função é chamada a partir de event handlers do Reflex.

Os event handlers do Reflex executam no processo Python do servidor da aplicação, não no navegador. Assim, a chave lida do ambiente não chega ao navegador, a menos que seja copiada para uma variável de `rx.State`, retornada para a página ou registrada em log. A função não faz nenhuma dessas operações.

## Contrato da função

```python
async def enviar_email(
    para: str | list[str],
    assunto: str,
    html: str | None = None,
    texto: str | None = None,
    remetente: str | None = None,
    responder_para: str | None = None,
    chave_idempotencia: str | None = None,
) -> str
```

| Parâmetro | Regra |
|---|---|
| `para` | Obrigatório. Um endereço ou lista de 1 a 50 endereços, sem vazios após trim. |
| `assunto` | Obrigatório e não vazio após trim. |
| `html`, `texto` | Ao menos um deve ser informado e não vazio. |
| `remetente` | Opcional. Se omitido, usa `RESEND_FROM_EMAIL`; se esta também faltar, usa `onboarding@resend.dev`. Aceita o formato `Nome <email>`. |
| `responder_para` | Opcional. Enviado como `reply_to`. |
| `chave_idempotencia` | Opcional. Enviada no cabeçalho `Idempotency-Key`. |

Retorno: o `id` da mensagem devolvido pelo Resend.

A função aceita ainda o argumento nomeado `transport`, usado somente pelos testes para injetar `httpx.MockTransport`.

A validação de formato de endereço é básica (presença de `@` e domínio); a validação definitiva fica com o provedor.

## Chamada ao provedor

- `POST https://api.resend.com/emails`.
- Cabeçalhos: `Authorization: Bearer <EMAIL_TOKEN>`, `Content-Type: application/json` e, quando houver, `Idempotency-Key`.
- Corpo: `from`, `to`, `subject`, e `html` e/ou `text`, e `reply_to` quando informado.
- Timeout configurável por `RESEND_TIMEOUT_SECONDS`, padrão de 10 segundos.
- Uma única tentativa por chamada; não há retry automático.

## Erros

A função levanta `EmailEnvioError` com um atributo `codigo`:

| Código | Situação |
|---|---|
| `EMAIL_CONFIGURATION_MISSING` | `EMAIL_TOKEN` ausente ou vazia. Nenhuma requisição é feita. |
| `INVALID_INPUT` | Parâmetro obrigatório ausente, vazio ou fora das regras acima. Nenhuma requisição é feita. |
| `EMAIL_PROVIDER_REJECTED` | Resposta 4xx diferente de 429 (por exemplo, 403 de destinatário não permitido em modo de teste, 422 de validação). |
| `EMAIL_RATE_LIMITED` | Resposta 429. |
| `EMAIL_PROVIDER_UNAVAILABLE` | Resposta 5xx, timeout ou falha de transporte. |

A mensagem do erro pode incluir a mensagem devolvida pelo Resend, mas nunca a chave.

## Configuração

Novas entradas em `.env.example`, sem valor real:

```
EMAIL_TOKEN=
RESEND_FROM_EMAIL=onboarding@resend.dev
RESEND_TIMEOUT_SECONDS=10
```

## Riscos aceitos pelo grupo

- A chave do Resend fica no ambiente do servidor Reflex e não no Xano; qualquer pessoa com acesso ao `.env` ou ao host da aplicação pode usá-la.
- Se a chave for copiada para o `State`, uma página ou um log, ela passa a ser visível no navegador. A função não faz isso, mas código futuro pode fazer.
- O envio não é autorizado pelo backend: qualquer código Reflex que chamar a função envia o e-mail. O controle de quem pode disparar envios depende de onde a função for integrada, o que está fora do escopo.
- Sem outbox persistida, não há registro auditável no Xano de e-mails enviados por este caminho.
- Com `onboarding@resend.dev`, o Resend só entrega ao e-mail dono da conta; outros destinatários resultam em `EMAIL_PROVIDER_REJECTED`.

## Testes

- Testes automatizados em `tests/test_email_service.py`, com `httpx.MockTransport`, sem chamada real ao Resend: corpo e cabeçalhos enviados, remetente padrão, `reply_to`, idempotência, cada código de erro e ausência da chave nas mensagens de erro.
- Teste manual controlado: um envio real para o e-mail dono da conta Resend, registrando o `id` retornado e o recebimento. Esse teste só deve ser executado com autorização do grupo e não comprova entrega a outros destinatários.

### Conferência da documentação do Resend (2026-11-04)

Foram consultadas as páginas `api-reference/emails/send-email`, `api-reference/errors` e `dashboard/emails/idempotency-keys` da documentação do Resend. Elas confirmam o contrato implementado:

- `POST https://api.resend.com/emails` com `Authorization: Bearer`; campos `from` (aceita `Nome <email>`), `to` (texto ou lista, máximo de 50), `subject`, `html` e `text`. O nome `reply_to` é o usado nos exemplos da documentação, mas o título do campo não pôde ser lido diretamente na página.
- Resposta de sucesso `{"id": "..."}`.
- Cabeçalho `Idempotency-Key` com 1 a 256 caracteres e validade de 24 horas; reutilizar a chave com outro corpo retorna 409. A função não valida o tamanho da chave; o 400 do provedor resulta em `EMAIL_PROVIDER_REJECTED`.
- 400, 401, 403, 409 e 422 são rejeições (`EMAIL_PROVIDER_REJECTED`); o 403 inclui a restrição de teste do `onboarding@resend.dev`, que só envia ao e-mail da própria conta. 429 cobre limite por segundo e cotas diária e mensal (`EMAIL_RATE_LIMITED`). 500 e 503 resultam em `EMAIL_PROVIDER_UNAVAILABLE`.

### Evidências dos testes automatizados (2026-11-04)

Os testes foram executados na imagem Docker construída a partir do `dockerfile` do projeto (Python 3.13, `httpx` 0.28.1), pois o ambiente Windows do grupo não possui Python instalado. `tests/test_email_service.py` passou com 9 testes, e a suíte completa passou com 262 testes. Esses testes usam `httpx.MockTransport` e não comprovam entrega real.

Para o build funcionar, foi removida do `requirements.txt` uma linha final `reflex==0.9.12` gravada em UTF-8 num arquivo UTF-16, que impedia a conversão feita pelo `dockerfile`. A linha era duplicada; a dependência continua declarada no arquivo. Essa correção é anterior a esta Change e não altera dependências.

### Evidência do envio real informada pelo usuário (2026-11-04)

O usuário executou o envio real pelo script `scripts/enviar_email_teste.py`, dentro da imagem Docker do projeto, com `docker run --rm --env-file .env <imagem> python scripts/enviar_email_teste.py --para <e-mail dono da conta Resend>`, e informou que o disparo do e-mail está funcionando.

Isso constitui evidência reportada de envio real pela função `enviar_email`, com o remetente `onboarding@resend.dev` e o destinatário dono da conta Resend. O `id` da mensagem retornado pelo Resend não foi registrado nesta documentação, e não houve inspeção independente da resposta do provedor ou do painel do Resend. A evidência não comprova entrega a outros destinatários, uso de remetente com domínio próprio, nem o comportamento real dos códigos de erro, que permanecem cobertos apenas pelos testes simulados.

O script `scripts/enviar_email_teste.py` fica fora de `tests/` e não segue o padrão `test_*`, para que a suíte automatizada não dispare e-mails reais.
