# Proposal: Operação backend de Entrada de Estoque

## Problema

O NexStock já possui saldo oficial por Produto em `inventory_stock` e uma tela Reflex preparada para entrada, mas não existe uma operação backend que registre a movimentação e atualize o saldo em conjunto. Habilitar a interface sem esse contrato deixaria a integridade e a rastreabilidade incompletas.

## Objetivo

Implementar no Xano a persistência comum de movimentações e o endpoint autenticado de Entrada. A confirmação deve registrar o usuário autenticado, preservar o histórico e somar a quantidade ao saldo oficial em uma operação atômica.

## Escopo

- Criar `inventory_movement` com referências a Produto e usuário, tipo, quantidade, data/hora, motivo, observação opcional e Fornecedor opcional.
- Criar `POST /entries` no grupo `Inventory Stock` (`api:estoque`).
- Autorizar a operação por `stock.entry`, com acesso implícito do Administrador/Líder, grant inicial para Almoxarife e sem grant inicial para Auxiliar.
- Validar Produto ativo, quantidade positiva, motivo e, se enviado, Fornecedor existente e ativo.
- Usar a data/hora recebida ou o horário do backend no processamento da entrada.
- Atualizar `inventory_stock` sem reconstruir o saldo pelo histórico e manter movimento e saldo na mesma transação.
- Usar incremento atômico do saldo para evitar atualizações perdidas quando entradas concorrentes atingirem o mesmo Produto.
- Definir contratos de erro, retorno e validações verificáveis.

## Fora do escopo

- Registrar Saídas ou alterar o saldo por qualquer outro fluxo.
- Alterar Reflex, habilitar o botão de Entrada ou fazer chamadas de escrita pelo frontend.
- Criar endpoint de consulta do histórico, edição, cancelamento ou exclusão de movimentações.
- Publicar/sincronizar artefatos no Xano remoto, fazer commit ou push.

## Dependências

Depende de `product`, `supplier`, `inventory_stock`, autenticação por `user`, autorização `Inventory/authorize_permission` e do grupo `Inventory Stock` já definido pela fundação técnica de estoque. A inicialização de saldos existentes deve estar concluída antes de habilitar a operação no workspace remoto.
