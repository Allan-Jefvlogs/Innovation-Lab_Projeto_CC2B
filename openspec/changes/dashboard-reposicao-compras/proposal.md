# Evoluir o Dashboard e criar a Reposição de Estoque

## Por que

O Dashboard real ainda reserva cards para Categorias e Fornecedores e mostra a situação de saldo positivo abaixo do mínimo separada de estoque zerado. O NexStock também não oferece uma fila que diferencie Produtos elegíveis para pedir de Produtos já cobertos por solicitação ativa.

## O que muda

- Usar na sidebar a mesma marca geométrica hoje desenhada na tela de Login.
- Manter Produtos ativos, Movimentações recentes e Alertas; retirar apenas os cards de Categorias e Fornecedores.
- Tornar clicável o indicador de estoque insuficiente, incluindo Produtos ativos zerados e abaixo do mínimo.
- Exibir contagem real de solicitações abertas.
- Criar página de Reposição com as seções “A solicitar” e “Compra já solicitada”.
- Criar formulário de solicitação com Produto, quantidade sugerida/editável e urgência.
- Capturar e-mail do destinatário comercial e habilitar seu envio ao backend somente após a migração do contrato.
- Manter a interface compatível durante a transição: campo opcional no contrato intermediário; exigência somente depois de o formulário atualizado estar funcionando.
- Atualizar telas e caches somente após respostas confirmadas do Xano; nenhuma operação de compra usa cache como autoridade.

## Dependência

Depende dos contratos de `backend-solicitacoes-compras` para elegibilidade, contagem, criação, acompanhamento e cancelamento. A Change `integracao-dashboard-real` permanece separada até validação manual; esta Change não altera seus arquivos nem antecipa sua conclusão.

## Fora do escopo

- Envio de e-mail, integração com fornecedor, pagamento ou emissão de ordem de compra externa.
- Alteração de saldo por solicitação; somente Entrada confirmada pelo Xano altera estoque.
- Publicação de endpoint sem autorização independente.
- Cache como validação de elegibilidade ou duplicidade.
