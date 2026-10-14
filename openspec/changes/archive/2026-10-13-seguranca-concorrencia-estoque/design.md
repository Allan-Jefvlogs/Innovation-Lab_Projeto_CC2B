# Design: Segurança de concorrência do estoque

## Estado atual e motivação

As operações POST /entries e POST /exits leem inventory_stock, calculam um novo saldo e
gravam o valor calculado com db.edit dentro de db.transaction. A transação agrupa as
escritas de uma requisição; isso não comprova que duas requisições concorrentes serializem
a leitura, validação e gravação. A versão atual pode sofrer lost update ou overselling.

A Change original de Saída mantém esse risco documentado e transfere a solução para esta
Change. Não se presume que a Entrada esteja protegida por usar o mesmo padrão.

## Investigação do mecanismo

A implementação deve começar por consulta à documentação Xano atual e aos recursos
disponíveis na instância. Classificar cada candidato como documentado, aceito pelo
validador MCP, confirmado no runtime ou hipótese não testada. Não copiar sintaxe de uma
versão documental diferente sem validação na instância.

Um mecanismo candidato só será escolhido se conseguir condicionar a alteração do saldo ao
saldo/versão atual de forma atômica e se puder executar a gravação do movimento na mesma
fronteira transacional. Uma coluna de versão sem comparação-e-atualização atômica não
constitui controle otimista suficiente. db.transaction sozinho não constitui lock nem
garantia de serialização.

Se nenhum mecanismo compatível for comprovado, registrar explicitamente o bloqueio. Não
introduzir mecanismo hipotético nem declarar proteção. A alternativa será buscar suporte
de plataforma ou capacidade de ambiente/plano que permita validação segura.

## Invariantes de aceitação

- O saldo confirmado de um Produto nunca é negativo.
- Saídas confirmadas não excedem o saldo inicial somado às entradas confirmadas.
- Cada movimento confirmado corresponde à alteração de saldo da mesma operação.
- Uma operação rejeitada ou revertida não deixa alteração parcial no saldo nem movimento.
- As invariantes são verificadas após requisições simultâneas para o mesmo Produto.

## Plano de validação e limites de ambiente

O plano Free disponível não permite Sandbox nem Data Source adicional. A ausência de
isolamento não pode ser substituída por teste sequencial, validação estática ou chamada ao
frontend.

A prioridade é obter um ambiente isolado suportado antes de testar concorrência com escrita.
Se isso não estiver disponível, qualquer teste no datasource atual depende de aprovação
explícita, usa exclusivamente Produto fictício dedicado e registra que os dados são
compartilhados e persistentes. A criação de Produto/saldo, POST /entries, POST /exits e os
registros de movimentação necessários precisam estar cobertos pela autorização. Movimentos
de auditoria não devem ser removidos como limpeza. Não injetar falha pós-escrita em dados
compartilhados; rollback requer ambiente ou harness aprovado.

O teste simultâneo deve sincronizar duas saídas para saldo insuficiente para ambas e
verificar as invariantes de aceitação. Incluir também concorrência entre Entrada e Saída
sobre o mesmo Produto. Se não for possível executar estes testes com segurança, mantê-los
pendentes e não declarar proteção comprovada.

## Decisao de cancelamento e limitacao remanescente

Por orientacao do professor, a protecao concorrente foi retirada do escopo da entrega academica. A conta utiliza o plano Free do Xano, sem Sandbox nem Data Source adicional, e a solucao considerada exigiria recursos pagos. Nenhuma das 13 tarefas foi executada; todas permanecem desmarcadas em tasks.md.

O comportamento atual de Entrada e Saida pode sofrer lost update ou overselling quando requisicoes simultaneas leem e gravam o saldo. db.transaction agrupa escritas de uma requisicao, mas nao oferece garantia comprovada de serializacao entre requisicoes. Esta Change registra uma proposta cancelada/adiada, nao uma protecao implementada.
