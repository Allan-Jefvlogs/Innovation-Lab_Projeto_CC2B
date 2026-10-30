# Introduzir o backend de Solicitações de Compras

## Por que

O NexStock identifica Produtos com estoque insuficiente, mas ainda não registra uma solicitação de compra associada ao Produto. Sem uma regra autoritativa no backend, duas pessoas ou duas requisições repetidas poderiam abrir solicitações duplicadas.

## O que muda

- Criar contratos Xano para consultar elegibilidade, registrar e acompanhar solicitações, cancelar, moderar estados e reconciliar recebimentos.
- Definir a entidade `purchase_request` e um histórico auditável de alterações.
- Revalidar Produto, saldo, estado da solicitação e grants no Xano em toda operação de escrita.
- Introduzir idempotência para repetição de POST após clique duplo, timeout ou reenvio.
- Persistir o endereço comercial informado pelo usuário autorizado, mantendo NULL em pedidos históricos.
- Fazer a transição em duas etapas: primeiro aceitar endereço opcional/anulável no POST publicado; exigir o endereço somente depois que o formulário novo estiver funcionando.
- Investigar uma restrição de unicidade no banco para impedir simultaneamente mais de uma solicitação ativa por Produto.
- Relacionar recebimentos a movimentações de Entrada já confirmadas, sem alterar saldo por meio da Solicitação de Compra.
- Manter o envio de e-mail fora da primeira fase; a solicitação deve comunicar explicitamente que o e-mail está pendente.

## Escopo

Esta Change cobre o contrato, a modelagem e a implementação backend de Solicitações de Compras. A interface e os indicadores ficam em `dashboard-reposicao-compras`, que depende deste backend. A Change `integracao-dashboard-real` permanece separada até concluir sua validação manual.

O Xano continua como fonte oficial. Nenhum cache do Reflex autoriza a criação ou o encerramento. O backend deve conferir novamente o estado atual.

## Fora do escopo

- Envio automático de e-mail, até que o usuário defina destinatário e serviço.
- Alteração automática do saldo ou criação de movimentação pelo módulo de Solicitações.
- Garantia de concorrência presumida apenas por `db.transaction` ou por validação frontend.
- Publicação, migração, seed ou alteração de grants sem revisão e autorização próprias.

## Dependências e limitação

A interface depende dos contratos backend e da validação funcional dos endpoints publicados. O Xano permanece obrigatório e será usado como backend e banco de dados.

## Decisão de escopo acadêmico (2026-10-25)

Por decisão do projeto, testes avançados de concorrência simultânea, isolamento serializável, ambiente Xano separado e rollback induzido não são pré-requisitos para concluir a funcionalidade acadêmica. Essa decisão reduz o critério de aceite acadêmico dos testes; ela não declara concorrência, isolamento ou rollback comprovados. Os riscos técnicos não demonstrados permanecem registrados em `design.md` para trabalho futuro. A publicação continua seletiva e exige validação funcional controlada, sem usar produtos reais como dados de teste.

## Fase 2 de e-mail transacional — preparacao local

A fase local prepara uma outbox separada por evento, templates em portugues e um dispatcher interno para a API HTTP do Resend. O POST e o PATCH apenas gravam a intencao na transacao existente; nenhum deles chama o provedor. A funcao de envio nao e invocada nesta entrega. Publicacao, credenciais, verificacao de dominio, envio e validacao runtime permanecem pendentes.
