# Recebimento de compras por entradas explicitamente vinculadas

## Why

Entradas reais aumentam o saldo, mas não identificam solicitações de compra. A Reposição filtra estoque insuficiente; um aumento de saldo pode ocultar o produto sem concluir a compra. Não é seguro inferir recebimento pelo produto ou pelo saldo.

## What Changes

- Propor vínculo explícito e opcional entre entrada e solicitação, preservando entradas avulsas.
- Registrar recebimentos sucessivos, quantidade acumulada e evento recebimento_registrado na mesma transação de saldo e movimento.
- Liberar active_product_id somente no recebimento total; manter pedidos parciais identificáveis em Compras mesmo com saldo suficiente.
- Propor rastreamento de unidade e idempotência para não duplicar estoque, histórico ou quantidade recebida após repetição.
- Estrutura aprovada e implementada localmente; migração e publicação do schema e do fluxo dependem de autorização separada. Não houve operação remota.

## Impact

Xano permanece backend e banco. Uso acadêmico sequencial, sem SQL direto, novas tabelas ou arquitetura avançada de concorrência. Alterações aditivas propostas em inventory_movement e purchase_request e evolução de POST /entries. Não instrumentar Auditoria nem enviar e-mails. Ajustes visuais do detalhe permanecem na change perfil-compras-solicitacoes.
