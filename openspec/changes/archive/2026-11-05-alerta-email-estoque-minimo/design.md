# Design: Alerta por e-mail de estoque abaixo do mínimo

## Estado local relevante

- `ExitState.load_exit_data` em `Meu_projeto/pages/movimentacoes.py` já consulta todas as páginas de `GET /stock` e guarda em `stock_by_product` o saldo, o código e o nome; `GET /stock` também retorna `estoque_minimo`, que hoje é descartado. A unidade de medida não é retornada por `GET /stock`.
- `ExitState.register_exit` chama `auth_client.create_stock_exit`. `exits_post.xs` retorna `movement_id`, `saldo_anterior`, `saldo_atual` e `data_hora`.
- `AuthState` guarda `user_name` e `user_email` carregados de `auth/me`.
- `enviar_email` levanta `EmailEnvioError` com `codigo` e retorna o `id` do Resend.

## Componentes

### `Meu_projeto/services/stock_alert.py`

Serviço novo, independente do Reflex, para que a regra possa ser testada sem montar o `State`:

- `deve_alertar(saldo_atual, estoque_minimo) -> bool`: converte os dois valores com `Decimal` e retorna `saldo_atual < estoque_minimo`. Valores ausentes, não numéricos ou não finitos retornam `False`.
- `montar_alerta(...) -> (assunto, html, texto)`: monta a mensagem com os dados do Produto escapados no HTML.
- `enviar_alerta_estoque_minimo(...) -> str`: aplica a regra, monta e envia o alerta, e retorna um status: `nao_aplicavel`, `sem_destinatario`, `enviado` ou `falhou`. Captura `EmailEnvioError` e registra o código em log, sem a chave.

### `ExitState`

- `load_exit_data` passa a guardar `estoque_minimo` em `stock_by_product`.
- Novos campos `alert_message` e `alert_error`, limpos no início de cada `register_exit`.
- Após o sucesso de `create_stock_exit`, o handler captura Produto, `estoque_minimo`, quantidade, `movement_id`, `saldo_atual`, `data_hora` e o usuário logado, antes de limpar o formulário.
- Depois do bloco da Saída, com `is_submitting` já falso, o handler faz `yield` para mostrar a Saída registrada e só então envia o alerta.

## Regra de disparo

Toda Saída confirmada com quantidade disponível após a Saída < `estoque_minimo` gera alerta. `saldo_anterior` não é usado. A quantidade disponível é o `saldo_atual` da resposta; sem ele, é `saldo_disponivel` carregado na página menos a quantidade da Saída. Se o mínimo ou o e-mail do usuário logado não puderem ser obtidos, o alerta é ignorado sem mensagem de erro.

- Saldo zerado conta como abaixo do mínimo sempre que o mínimo for maior que zero.
- Produto com `estoque_minimo` igual a zero nunca gera alerta, pois o saldo nunca fica negativo.
- O `estoque_minimo` usado é o carregado na abertura da página de Saída; uma alteração feita depois só vale ao recarregar a página.

## Conteúdo do e-mail

- Destinatário: `AuthState.user_email`. Se estiver vazio, o alerta não é enviado (`sem_destinatario`).
- Assunto: `[NexStock] Estoque abaixo do mínimo: <código> - <nome>`, ou `[NexStock] Sem estoque: <código> - <nome>` quando o saldo for zero.
- Corpo em HTML e texto: Produto, saldo atual, estoque mínimo, quantidade da Saída, usuário responsável e data/hora da Saída.
- `chave_idempotencia`: `alerta-estoque-<movement_id>`, para que um reenvio da mesma Saída não duplique o e-mail. Sem `movement_id`, o envio segue sem chave.

## Mensagens na tela

| Status | Mensagem |
|---|---|
| `enviado` | `alert_message`: "Alerta de estoque mínimo enviado para <e-mail>." |
| `falhou` | `alert_error`: "Saída registrada, mas o alerta por e-mail não foi enviado." |
| `nao_aplicavel`, `sem_destinatario` | Nenhuma mensagem. |

A mensagem de sucesso da Saída nunca é substituída.

## Configuração do envio

`email_service` lê o `.env` da raiz com um leitor próprio, sem `python-dotenv` (que não está no `requirements.txt`), sem sobrescrever variáveis já definidas no ambiente. Assim `EMAIL_TOKEN` fica disponível mesmo quando o container é iniciado sem `--env-file`, desde que o `.env` esteja na imagem ou montado em `/app`.

Causa da falha no primeiro teste manual: o import de `dotenv` falhava em silêncio, `EMAIL_TOKEN` ficava vazio e o envio terminava em `EMAIL_CONFIGURATION_MISSING`.

## Testes

- `tests/test_stock_alert.py`, com `enviar_email` em mock: saldo abaixo do mínimo, saldo zerado, Produto que já estava abaixo, saldo igual ao mínimo, mínimo zero, dados inválidos, destinatário vazio, falha de envio, chave de idempotência e escape do HTML.
- Teste manual, com autorização do grupo, usando um Produto fictício e o usuário cujo e-mail é o dono da conta Resend: Saída que deixa o saldo abaixo do mínimo e recebimento do alerta.
