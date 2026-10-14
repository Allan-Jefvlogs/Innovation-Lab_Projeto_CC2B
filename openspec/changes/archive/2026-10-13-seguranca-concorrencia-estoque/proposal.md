# Proposal: Segurança de concorrência do estoque

## Problema

As operações backend de Entrada e Saída atualizam o saldo por leitura, cálculo e gravação.
Sem mecanismo atômico comprovado, requisições concorrentes para o mesmo Produto podem
perder atualizações ou confirmar movimentos incompatíveis com o saldo final.

## Objetivo

Investigar, implementar e validar um mecanismo suportado pela instância Xano que preserve
o saldo e o ledger de movimentações durante operações concorrentes de Entrada e Saída.
Nenhuma proteção será declarada antes de passar por validação sintática e testes simultâneos
de runtime.

## Decisão de escopo da entrega acadêmica

Por orientação do professor, esta Change foi cancelada/adiada para a entrega acadêmica atual. A solução considerada exigiria recursos de plano pago do Xano, enquanto o projeto utiliza o plano Free, sem Sandbox ou Data Source adicional. Esta funcionalidade não será implementada nesta entrega.

As 13 tarefas de `tasks.md` permanecem desmarcadas e não foram executadas. A specification nesta Change é uma proposta de trabalho futuro e não deve ser aplicada às specs consolidadas ao retirar este item da lista ativa. Uma retomada exigirá nova decisão de escopo, mecanismo suportado e ambiente de validação seguro.

## Escopo

- Investigar mecanismos suportados pela instância e seus limites.
- Definir invariantes de saldo e movimentações para operações concorrentes.
- Implementar mecanismo atômico suportado para Entrada e Saída, se houver.
- Validar simultaneidade, rejeição por saldo insuficiente e rollback.

## Fora do escopo

- Alterar grants, perfis ou autorização funcional.
- Alterar a interface Reflex.
- Tratar db.transaction, isoladamente, como prova de serialização.
- Declarar proteção com base apenas em validação estática ou execução sequencial.
- Fazer publicação no workspace sem revisão e autorização próprias.

## Dependências e restrições

A Change operacao-backend-saida-estoque documenta o comportamento atual e transfere para
esta Change o trabalho de proteção concorrente. A Change operacao-backend-entrada-estoque
usa padrão de atualização de saldo semelhante e também está no escopo desta investigação.

A conta Xano disponível está no plano Free e não permite Sandbox nem Data Source adicional.
Não há evidência de ambiente de dados isolado disponível. Testes simultâneos com escrita no
datasource existente exigem aprovação explícita, Produto fictício dedicado e registro dos
dados persistentes. Sem ambiente isolado ou aprovação adequada, os testes de runtime ficam
pendentes e a proteção não pode ser declarada comprovada.
