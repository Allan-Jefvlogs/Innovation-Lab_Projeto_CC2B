# Proposal: Alerta por e-mail de estoque abaixo do mínimo

## Problema

O NexStock identifica Produtos abaixo do estoque mínimo no Dashboard, na página de Estoque e na Reposição, mas só quem abre essas telas percebe a situação. Uma Saída que deixa o Produto abaixo do mínimo não gera nenhum aviso ativo, e a reposição pode atrasar.

A função `enviar_email`, entregue pela change arquivada `envio-email-frontend`, permite enviar e-mails pelo Resend a partir do Reflex, mas ainda não está ligada a nenhum fluxo.

## Objetivo

Enviar automaticamente um e-mail de alerta ao usuário logado sempre que uma Saída registrada pelo NexStock deixar o saldo de um Produto abaixo do estoque mínimo, usando a função `enviar_email` existente.

## Decisões do grupo (2026-11-04)

- **Destinatário:** o e-mail do usuário logado que registrou a Saída (`AuthState.user_email`).
- **Regra de disparo:** toda Saída confirmada cujo `saldo_atual` fique abaixo do `estoque_minimo` gera alerta, inclusive quando o Produto já estava abaixo do mínimo antes da Saída.
- **Saldo zerado:** tratado como abaixo do mínimo, com o assunto identificando "Sem estoque".

## Escopo

- Carregar o `estoque_minimo` dos Produtos na página de Saída a partir do `GET /stock` já consultado.
- Após uma Saída confirmada pelo Xano, comparar o `saldo_atual` retornado com o `estoque_minimo` do Produto.
- Enviar o alerta ao e-mail do usuário logado quando `saldo_atual < estoque_minimo`.
- Informar na tela se o alerta foi enviado ou se falhou, sem afetar a Saída já registrada.
- Testes automatizados com o envio simulado.

## Fora do escopo

- Alertas para Saídas registradas fora da página de Saída do NexStock (chamadas diretas à API, painel do Xano).
- Alertas por Entrada, edição do estoque mínimo ou varredura periódica dos saldos.
- Persistência ou histórico dos alertas enviados no Xano.
- Destinatários por perfil, por Fornecedor, por Produto ou configurados no ambiente.
- Alterar o endpoint `POST /exits`, o dispatcher de e-mail do Xano ou as Changes `backend-solicitacoes-compras` e `dashboard-reposicao-compras`.
- Verificar domínio próprio no Resend.
- Commit, push ou publicação no Xano.

## Dependências

- `Meu_projeto/services/email_service.py` (`enviar_email`), arquivada em `2026-11-04-envio-email-frontend`.
- Resposta de `POST /exits` com `movement_id` e `saldo_atual`, conforme a spec `operacao-backend-saida-estoque`.
- `estoque_minimo` retornado por `GET /stock`.
- E-mail do usuário carregado por `AuthState` a partir de `auth/me`.

## Riscos

- O alerta herda a decisão arquitetural da change `envio-email-frontend`: o envio é feito pelo Reflex, sem autorização nem registro no backend.
- Como a regra roda no event handler do Reflex depois da resposta do Xano, uma falha ou interrupção nesse ponto pode impedir o alerta, e não há reenvio automático.
- Enquanto o remetente for `onboarding@resend.dev`, o Resend só entrega ao e-mail dono da conta. Para os demais usuários logados, o envio é recusado (`EMAIL_PROVIDER_REJECTED`) e a tela informa a falha do alerta. Entregar a qualquer usuário exige verificar um domínio no Resend, fora do escopo.
- Como toda Saída abaixo do mínimo gera alerta, várias Saídas do mesmo Produto geram vários e-mails, consumindo a cota do Resend.
