# Tasks: Validacao avancada das operacoes de estoque

## 1. Escopo e seguranca

- [x] 1.1 Registrar a transferencia dos cenarios nao executados da tarefa 4.4 de `operacao-backend-saida-estoque`, mantendo o historico e sem declarar testes aprovados.
- [ ] 1.2 Obter ambiente isolado ou harness aprovado para falhas controladas e estado de saldo ausente; registrar que o plano Free nao oferece Sandbox nem Data Source adicional.
- [ ] 1.3 Definir e registrar os identificadores ficticios, snapshots antes/depois, aprovacao de escrita quando aplicavel e criterio de interrupcao.

## 2. Validacao de runtime

- [ ] 2.1 Testar rollback de POST /entries apos a primeira escrita e comprovar saldo e movimentos sem alteracao parcial.
- [ ] 2.2 Testar rollback de POST /exits apos a primeira escrita e comprovar saldo e movimentos sem alteracao parcial.
- [ ] 2.3 Testar Produto ativo sem linha `inventory_stock` em POST /entries e POST /exits; registrar respostas reais e ausencia de escrita.
- [ ] 2.4 Validar `data_hora` personalizada em Entrada e Saida, comparando resposta e movimento persistido.
- [ ] 2.5 Inspecionar todos os campos das respostas de Entrada e Saida contra movimento e saldo persistidos.
- [ ] 2.6 Verificar invariantes saldo/ledger depois de cada rejeicao, falha e operacao confirmada; nao inferir concorrencia.

## 3. Fechamento documental

- [ ] 3.1 Registrar por caso pre-condicoes, ambiente, request sem credenciais, resposta real, snapshots e resultado.
- [ ] 3.2 Manter rollback e demais casos sem ambiente seguro como pendentes; registrar que concorrencia e overselling foram adiados fora desta entrega e que nao ha garantia comprovada.
- [ ] 3.3 Executar OpenSpec strict das Changes afetadas e `git diff --check`.
