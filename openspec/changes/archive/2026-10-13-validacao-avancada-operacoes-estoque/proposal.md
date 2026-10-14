# Proposal: Validacao avancada das operacoes de estoque

## Problema

A Change `operacao-backend-saida-estoque` possui evidencias funcionais de runtime, mas
alguns criterios avancados nao puderam ser exercitados com seguranca no datasource
compartilhado. A conta Xano utilizada esta no plano Free e nao disponibiliza Sandbox nem
Data Source adicional.

## Objetivo

Planejar e executar, quando houver ambiente ou harness apropriado, validacoes avancadas das
operacoes POST /entries e POST /exits. Esta Change separa esses testes da cobertura funcional
ja documentada e nao declara nenhum dos cenarios como aprovado antes de evidencias de runtime.

## Decisao de adiamento para a entrega academica

Por decisao do projeto, esta Change sai do escopo da entrega academica atual. A conta utiliza o plano gratuito do Xano e nao oferece Sandbox, Data Source adicional ou harness isolado aprovado para rollback e integridade. Os testes funcionais de Entrada e Saida ja realizados permanecem documentados nas Changes anteriores; os cenarios avancados desta proposta continuam como evolucao futura e nao como funcionalidades concluidas.

## Escopo

- Comprovar rollback apos uma escrita parcial em ambiente isolado ou harness aprovado.
- Validar a rejeicao quando nao existe linha de saldo para um Produto ativo.
- Validar `data_hora` personalizada nas respostas e movimentos persistidos de Entrada e Saida.
- Inspecionar os campos completos das respostas de Entrada e Saida e compara-los com os
  registros persistidos.
- Verificar invariantes entre saldo e movimentos apos falhas e rejeicoes.
- Registrar pre-condicoes, evidencias, resultados e riscos de cada caso.

## Fora do escopo

- Implementar ou alterar endpoints, tabelas, grants ou frontend.
- Executar testes no datasource compartilhado sem autorizacao explicita e plano de seguranca.
- Testes simultaneos, serializacao, lost update ou prevencao de overselling; esses temas
  foram adiados para fora da entrega academica na Change `seguranca-concorrencia-estoque`
  por dependerem de recursos pagos do Xano. O risco segue sem solucao comprovada.
- Publicar no Xano, fazer commit ou push; arquivar esta Change somente com `--skip-specs`, sem aplicar os requisitos ainda nao implementados.

## Restricoes e dependencia

A conta Free atual nao permite Sandbox nem Data Source adicional. Os testes de rollback e
ausencia de saldo dependem de ambiente isolado ou harness que permita controlar o estado e
induzir a falha sem risco para dados compartilhados. Qualquer chamada de escrita no datasource
atual exige autorizacao explicita para cada operacao e deve usar exclusivamente dados
ficticios identificados. Se os pre-requisitos nao forem atendidos, as tarefas permanecem
pendentes; nao se substitui isolamento por teste sequencial ou validacao estatica.
