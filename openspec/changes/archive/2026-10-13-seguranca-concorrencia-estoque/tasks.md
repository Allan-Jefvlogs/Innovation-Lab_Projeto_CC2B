# Tasks: Segurança de concorrência do estoque

## 1. Descoberta e contrato

> Registro de encerramento de escopo: as 13 tarefas desta Change não foram executadas e permanecem desmarcadas. O cancelamento/adiamento para esta entrega acadêmica decorre da dependência de recursos pagos do Xano. O risco técnico continua vigente; arquivar este registro não significa conclusão técnica.

- [ ] 1.1 Consultar documentação oficial e capacidades disponíveis na instância Xano.
- [ ] 1.2 Classificar mecanismos candidatos por evidência: documentação, aceitação do validador MCP e confirmação em runtime.
- [ ] 1.3 Definir invariantes de saldo e ledger para saídas simultâneas e concorrência entre Entrada e Saída.
- [ ] 1.4 Confirmar uma estratégia atômica suportada; se nenhuma existir, documentar o bloqueio sem inventar sintaxe ou garantia.

## 2. Implementação

- [ ] 2.1 Implementar a estratégia confirmada em POST /entries e POST /exits, preservando autorização e contratos existentes.
- [ ] 2.2 Manter saldo e movimento na mesma unidade transacional e tratar conflito/rejeição sem escrita parcial.
- [ ] 2.3 Validar pelo Xano Developer MCP todos os XanoScripts alterados.

## 3. Testes e validação

- [ ] 3.1 Obter ambiente isolado apropriado ou aprovação explícita para teste de escrita com Produto fictício dedicado no datasource compartilhado.
- [ ] 3.2 Executar duas saídas simultâneas cujo total excede o saldo e verificar saldo, respostas e movimentos.
- [ ] 3.3 Executar Entrada e Saída simultâneas para o mesmo Produto e verificar invariantes.
- [ ] 3.4 Comprovar rollback em falha posterior à primeira escrita em ambiente/harness aprovado.
- [ ] 3.5 Executar OpenSpec strict e git diff --check.
- [ ] 3.6 Revisar dry-run curado sem executar push real.
