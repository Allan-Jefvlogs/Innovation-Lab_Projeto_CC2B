# Diagnóstico de HTTP 200 rejeitado e limitação local

## Evidência disponível

O usuário informou `Dashboard notifications unavailable: exception_type=XanoServerError status=200`, depois de uma página inicialmente vazia e da criação/alteração de uma compra. Não forneceu o contrato da resposta com eventos. Não há exportação atual posterior às últimas publicações entre as cópias locais disponíveis. Nenhuma chamada remota foi realizada nesta revisão.

O método `XanoAuthClient.get_purchase_request_notifications` rejeita explicitamente respostas HTTP 200 com campos ausentes, tipos incompatíveis, contadores inválidos ou eventos inválidos. Antes desta revisão, três exceções genéricas ocultavam o campo. O transporte também pode rejeitar JSON inválido ou resposta raiz sem objeto; nesses casos há logs próprios de decodificação/estrutura. O status 200 informado sozinho não identifica qual ramo falhou.

## Alteração local restrita

O cliente agora identifica cada violação com `origin=response_contract`, `contract_field`, `contract_expected` e `contract_found_type`. O estado inclui esses metadados no log já existente. Os caminhos são constantes (por exemplo, `items[].lida`), sem IDs, valores de campos, payloads, destinatários, tokens ou headers. A validação mantém os mesmos critérios, sem coerção de tipos, valores padrão ou substituição de total por zero. Uma resposta inválida não é tratada como lista vazia válida nem provoca retry automático.

Não houve alteração de endpoint, query, projeção, cache, coordenador, limites, marcador, Compras, recebimentos, gráfico ou movimentações recentes. Nenhuma publicação é necessária para este diagnóstico local. A autorização para publicar foi registrada, mas não será utilizada para uma correção especulativa sem conhecer o campo inválido.

## Contrato esperado

- Raiz: objeto com `items` array; `itemsTotal` e `unreadTotal` inteiros não negativos; `curPage` e `perPage` inteiros positivos; total compatível com quantidade de itens.
- Item: objeto com `history_id` e `purchase_request_id` inteiros; `evento` e `descricao` texto; `data_evento` timestamp numérico em milissegundos; `lida` booleano. `status_novo` opcional/nulo ou texto com um status conhecido.
- Booleanos não substituem inteiros. Strings numéricas e strings `true`/`false` continuam inválidas. Metadados corretos com array vazio são aceitos.

O GET local projeta os campos nativos e o ID auxiliar de recibo, constrói os itens por foreach/array.push e devolve os cinco campos de raiz esperados. Isso descreve o contrato pretendido; não comprova o formato efetivamente devolvido pelo endpoint publicado.

## Elegibilidade e isolamento revisados

O GET inclui somente `criada`, `status_alterado`, `cancelada`, `rejeitada` e `recebimento_registrado`, com `data_evento >= activation_at`. Não cria eventos, não inclui `email_status_alterado` e não infere conclusão sem histórico persistido. Exige `purchase_request.read`; a função de escopo permite todos os pedidos ao administrador ou a quem tem manage, após read validado. Os demais usuários recebem somente pedidos próprios. O recibo é vinculado a history_id e auth.id.

Criação e atualização de status têm escritores locais dos eventos correspondentes, mas os novos registros e as versões publicadas não foram lidos nesta revisão. A página vazia anterior não comprova que os novos eventos sejam inelegíveis. Se a resposta com eventos contém um campo inválido, o cliente descarta a página inteira; é necessário identificar o campo antes de concluir por filtro/marco ou corrigir o backend.

## Limitação local

`XanoRateLimitError` com `origin=local_coordinator` ocorre antes do HTTP, ao esgotar as reservas na janela ou durante cooldown compartilhado após um 429 remoto. O padrão local é 7 reservas por 20 segundos (configuração pode reduzir o orçamento ou ampliar a janela). A instância é compartilhada pelo processo, incluindo autenticação e consultas de outras telas/sessões. A proteção compartilha GETs idênticos em andamento; o Dashboard reutiliza cache e troca de período consulta somente movements. O sino carrega via cache/controle loading e não faz polling.

O log fornecido comprova bloqueio local, não um 429 retornado por esses dois endpoints nem duplicação de chamadas. Não há histórico suficiente para atribuir o consumo da janela a uma sequência exata. Nenhum limite ou TTL foi alterado. Depois de respeitar o cooldown, a recuperação permanece explícita.

## Próxima verificação segura

1. Reiniciar o processo Reflex para carregar o diagnóstico local, seguindo o modo de execução atual e preservando flags/segredos. Não alterar configuração no Xano.
2. Esperar o cooldown indicado e deixar terminar as leituras de outras telas.
3. Abrir o sino; se a falha estiver preservada em estado, acionar uma vez Tentar novamente. Isso executa somente GET; não marcar como lida.
4. Informar apenas a linha sanitizada com endpoint, status, origin, contract_field, expected e found_type. Não copiar corpos, tokens ou valores dos eventos.
5. Alternativamente, abrir a resposta já existente no Request History e informar somente nomes/tipos dos campos e se os itens são objetos ou null, sem reexecutar Debug.
6. Se o contrato estiver correto, conferir por leitura no painel os eventos já existentes, comparação com o marco original e vínculo ao solicitante. Não criar pedidos nem alterar status para este diagnóstico.

## Evidência posterior e correção de status_novo

O usuário inspecionou uma resposta HTTP 200 existente: items contém objetos; os IDs são inteiros, descricao/evento são texto, data_evento é timestamp numérico em milissegundos e lida é booleano. Porém status_novo contém um objeto de metadados, incluindo status_anterior/status_novo, em vez de string ou null. Isso identifica uma violação concreta da validação do cliente. Os tipos dos metadados de paginação ainda não foram fornecidos; não é possível excluir uma segunda violação.

O GET local foi corrigido em uma única linha: `status_novo: $notification.dados|get:"status_novo"` passou a `status_novo: $notification.dados.status_novo`. O acesso direto seleciona a propriedade do objeto, seguindo o contrato gravado pelo escritor de status (`dados: {status_anterior: ..., status_novo: ...}`). Não serializa o objeto como texto, não relaxa a validação e não altera dados persistidos. A evidência confirma o formato errado publicado; não identifica por si só se o importador perdeu o filtro ou se outra versão foi publicada. A extração corrigida ainda precisa de validação no runtime.

Novos testes reproduzem a rejeição de objeto e aceitação de texto/null e verificam a projeção local; não executam o interpretador Xano. Os testes de hashes protegem integralmente as consultas/filtros. Nenhum outro endpoint foi alterado.

Ao consultar `xano.cmd workspace pull --help`, a CLI falhou antes de oferecer ajuda com `uv_os_get_passwd returned ENOMEM`. Não foram repetidas tentativas, executados dry-run ou publicação. Sem exportação atual e preview não foi seguro avançar à publicação automática autorizada. O backup disponível é anterior às últimas correções e não deve ser tratado como versão atual. A alternativa é revisar a linha na definição publicada no painel ou executar export/dry-run pelo PowerShell do usuário, onde a CLI já funcionou.
