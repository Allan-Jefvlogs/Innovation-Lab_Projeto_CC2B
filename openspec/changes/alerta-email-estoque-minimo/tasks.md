# Tasks: Alerta por e-mail de estoque abaixo do mínimo

## 1. Inspeção e contrato

- [x] 1.1 Confirmar com o grupo o destinatário, a regra de disparo e o tratamento do saldo zerado. Decididos em 2026-11-04 e registrados em `proposal.md`: usuário logado, toda Saída abaixo do mínimo, saldo zerado como abaixo do mínimo.
- [x] 1.2 Confirmar qual endpoint de leitura existente fornece `estoque_minimo`, código e nome do Produto à página de Saída, sem criar endpoint novo. `GET /stock` (`list_stock`), já consultado pela página de Saída, retorna `estoque_minimo`, `codigo` e `nome`; não retorna a unidade, que ficou fora do e-mail.
- [x] 1.3 Confirmar no `exits_post.xs` local que a resposta contém `movement_id`, `saldo_atual` e `data_hora`.

## 2. Implementação

- [x] 2.1 Criar `Meu_projeto/services/stock_alert.py` com a regra `saldo_atual < estoque_minimo` em `Decimal`, ignorando dados ausentes ou não numéricos.
- [x] 2.2 Montar o assunto e o corpo do alerta em HTML e texto, escapando os dados do Produto.
- [x] 2.3 Enviar pelo `enviar_email` ao e-mail do usuário logado, com `chave_idempotencia = "alerta-estoque-<movement_id>"`, retornando o status do alerta.
- [x] 2.4 Guardar `estoque_minimo` em `stock_by_product` na página de Saída.
- [x] 2.5 Chamar o alerta em `register_exit` somente após a confirmação da Saída e exibir o resultado em mensagem separada, sem alterar a mensagem de sucesso da Saída.

## 3. Validação

- [x] 3.1 Criar `tests/test_stock_alert.py` com `enviar_email` em mock para os cenários da spec.
- [x] 3.2 Executar a suíte de testes do projeto na imagem Docker e confirmar que os testes existentes continuam passando (278 testes OK em 2026-11-04, incluindo os 16 de `test_stock_alert`; a página `saida()` também foi montada sem erro).
- [ ] 3.3 Executar `openspec validate alerta-email-estoque-minimo --strict`, se o CLI estiver disponível.
- [x] 3.4 Executar `git diff --check`.
- [ ] 3.5 Com autorização do grupo, registrar uma Saída em Produto fictício que deixe o saldo abaixo do mínimo, logado com o usuário cujo e-mail é o dono da conta Resend, e confirmar o recebimento do alerta; não usar Produtos reais.

## 4. Fronteiras

- [x] 4.1 Não alterar `POST /exits`, o dispatcher de e-mail do Xano nem as Changes de Solicitações de Compras.
- [x] 4.2 Não alterar `enviar_email` nem adicionar dependências.
- [x] 4.3 Não fazer commit, push ou publicação sem autorização.
