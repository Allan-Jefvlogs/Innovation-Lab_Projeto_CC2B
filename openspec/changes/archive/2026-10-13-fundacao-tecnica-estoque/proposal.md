# Proposal: Fundação técnica de Estoque

## Problema

O cadastro de Produto possui `estoque_minimo`, mas não há persistência do saldo disponível nem endpoint que permita consultá-lo. Assim, o NexStock não pode exibir quantidade oficial sem reconstruí-la no frontend ou inventar dados.

## Objetivo

Criar no Xano a persistência de um saldo por Produto, inicializado em zero, e uma listagem autenticada e paginada que retorne saldo, estoque mínimo e situação derivada. O Xano permanece como fonte de verdade.

## Escopo

- Tabela `inventory_stock`, com referência única para Produto e quantidade não negativa.
- Inicialização idempotente dos Produtos existentes sem saldo.
- Criação atômica do Produto e de seu saldo inicial zero.
- Permissão `stock.read` e grants iniciais documentados para Almoxarife e Auxiliar de almoxarifado; Administrador conserva o bypass integral já existente.
- Endpoint paginado `GET /stock` no grupo `Inventory Stock`.
- Derivação de `sem_estoque`, `abaixo_minimo` ou `normal` no backend.
- Validação estática dos arquivos XanoScript e OpenSpec.

## Fora do escopo

Entradas, saídas, alteração de saldo por movimentação, histórico, dashboard, relatórios, integração Reflex e publicação remota.

## Dependências

Depende das tabelas `product`, dos perfis/permissões existentes e da autorização central `Inventory/authorize_permission`. A operação deve ser publicada e a inicialização dos saldos existentes executada antes de habilitar a consulta no ambiente remoto.
