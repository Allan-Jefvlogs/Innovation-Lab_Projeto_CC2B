# Proposal: Envio de e-mail pelo frontend Reflex

## Problema

O envio de e-mail transacional foi preparado no Xano (`dispatch_purchase_request_email`, outbox `purchase_request_email_delivery` e variáveis de ambiente do provedor), mas essa preparação ainda não foi publicada nem validada em runtime. O caminho atual depende de publicação, configuração de variáveis no workspace e testes de backend antes que qualquer e-mail possa ser enviado.

O grupo precisa de uma forma direta e reutilizável de enviar e-mails pelo Resend a partir do NexStock.

## Objetivo

Criar no frontend Reflex uma função única `enviar_email`, que recebe os parâmetros necessários de uma mensagem e a envia pela API HTTP do Resend, retornando o identificador da mensagem ou um erro identificável.

## Decisão arquitetural (2026-11-04)

Por decisão do grupo, o envio de e-mail passa a ser feito pelo Reflex, e não pelo Xano. Essa decisão é uma exceção explícita à diretriz de `openspec/config.yaml`, segundo a qual o Xano concentra a lógica de negócio. A exceção vale somente para a chamada ao provedor de e-mail; autorização, persistência e regras de estoque continuam no Xano.

O grupo aceitou o risco de a chave do Resend ficar acessível no ambiente do frontend. Os riscos aceitos estão registrados em `design.md`.

## Escopo

- Criar o serviço `Meu_projeto/services/email_service.py` com a função assíncrona `enviar_email`.
- Ler a chave e o remetente padrão de variáveis de ambiente (`EMAIL_TOKEN`, `RESEND_FROM_EMAIL`).
- Documentar as variáveis em `.env.example`, sem valor real de chave.
- Validar os parâmetros localmente antes de chamar o provedor.
- Mapear as respostas do Resend para erros identificáveis.
- Usar `httpx`, já presente em `requirements.txt`, sem adicionar o SDK `resend`.
- Adicionar testes automatizados com transporte HTTP simulado.
- Adicionar o script manual `scripts/enviar_email_teste.py` para um envio real controlado.

## Fora do escopo

- Integrar a função a telas ou fluxos existentes (Reposição, Solicitações de Compras, cadastro de usuário, redefinição de senha).
- Remover, alterar ou despublicar o dispatcher, a outbox ou as funções de e-mail do Xano.
- Atualizar a fase 2 de e-mail de `backend-solicitacoes-compras`; o destino desses artefatos será decidido em Change própria.
- Verificar domínio próprio no Resend ou usar o domínio institucional como remetente.
- Templates HTML, anexos, CC/BCC, filas, reenvio automático e agendamento.
- Commit, push ou publicação no Xano.

## Dependências

- Conta Resend com API key criada pelo grupo.
- Sem domínio verificado, o remetente `onboarding@resend.dev` só entrega ao e-mail dono da conta Resend.
- Biblioteca `httpx` já instalada no ambiente do projeto.

## Impacto em outras Changes

`backend-solicitacoes-compras` e `dashboard-reposicao-compras` preveem envio de e-mail pelo Xano. Esta Change não altera esses artefatos nem conclui suas tarefas. A sobreposição entre os dois caminhos permanece registrada até que o grupo decida, em Change própria, se o envio pelo Xano será descontinuado.
