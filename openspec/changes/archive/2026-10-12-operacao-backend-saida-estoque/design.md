# Design: Operação backend de Saída de Estoque

## Modelo existente

Reutilizar `inventory_movement`, que já possui `product_id`, `tipo` com valores `entrada` e `saida`, `quantidade` decimal, `data_hora`, `user_id`, `supplier_id` nullable, `motivo` e `observacao`. Não criar tabela nova. A linha de saldo oficial continua sendo `inventory_stock`, com unicidade por `product_id`.

## Endpoint e contrato

- Grupo: `Inventory Stock`, identificador canônico `api:estoque`.
- Rota: `POST /exits`.
- Autenticação: `auth = "user"`.
- Permissão: `stock.exit`, verificada por `Inventory/authorize_permission` dentro da transação.
- Inputs obrigatórios: `product_id` inteiro, `quantidade` decimal, `motivo` texto trimado.
- Inputs opcionais: `data_hora` timestamp e `observacao` texto nullable.
- O endpoint não aceita `user_id` nem `supplier_id` como inputs.

O perfil `administrator` mantém acesso integral implícito pela função central. O seed adiciona `stock.exit` ao catálogo e ao conjunto inicial de grants de `stockkeeper`, de forma idempotente e aditiva. `read_only` não recebe grant inicial. Grants já existentes não são removidos nem reescritos.

## Validação e efeitos

Dentro de uma única `db.transaction`, o endpoint:

1. exige `stock.exit` para o usuário autenticado;
2. rejeita quantidade menor ou igual a zero ou motivo vazio com `INVALID_INPUT`;
3. exige Produto existente e ativo (`PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE`);
4. carrega a linha `inventory_stock` do Produto e rejeita ausência com `STOCK_BALANCE_NOT_FOUND`;
5. compara `quantidade` ao saldo lido e rejeita quantidade maior com `INSUFFICIENT_STOCK`, antes de qualquer escrita;
6. calcula `saldo_atual - quantidade` e atualiza o saldo com `db.edit`;
7. cria `inventory_movement` com `tipo = "saida"`, `$auth.id`, o motivo, a observação e `supplier_id = null`;
8. retorna movimento, saldo anterior e saldo atual.

O input `decimal` e as preconditions nativas fazem a validação numérica; `quantidade > 0` rejeita zero, negativos e valores que não satisfaçam a comparação. `quantidade <= saldo` impede que a operação, isoladamente, calcule saldo negativo. A precisão segue o tipo decimal já usado em `inventory_stock`.

Para `data_hora`, a variável efetiva inicia com `now` do backend e recebe o timestamp informado quando presente. O usuário responsável sempre vem de `$auth.id`. Saída não usa Fornecedor; o campo da movimentação recebe `null`.

## Atomicidade e concorrência

`db.edit inventory_stock` e `db.add inventory_movement` executam sob o mesmo `db.transaction`. Falha em qualquer escrita propaga erro e desfaz a atualização/inserção da transação. Deadlock detectado ao editar o saldo retorna `STOCK_CONCURRENCY_CONFLICT`; outra falha dessa edição retorna `STOCK_UPDATE_FAILED`.

A estratégia disponível para esta instância é read-modify-write (`db.get` → validar/calcular → `db.edit`). `db.direct_query` não é utilizável nesta instância e não será usado. A documentação MCP XanoScript 2.7.1 lista níveis de isolamento transacional, mas a validação MCP de um bloco mínimo com `isolation = "serializable"` falhou com `Expecting --> stack <-- but found --> '\n' <--`; há também evidência anterior do parser/importador do workspace rejeitando essa construção. A sintaxe, portanto, não está confirmada como utilizável nesta instância. Não há lock/CAS ou incremento condicional de linha confirmado para esta instância, e essa sintaxe de isolamento não será introduzida.

Consequentemente, a transação garante atomicidade das escritas da requisição, mas não serializa mudanças concorrentes entre Saídas e Entradas. Duas Saídas podem ler o mesmo saldo, ambas passar pela precondition e sobrescrever uma à outra; os movimentos poderiam exceder a quantidade líquida refletida no saldo. O saldo calculado por uma execução isolada nunca é negativo, mas não se declara proteção contra overselling/lost update concorrente. Uma garantia forte depende de mecanismo de concorrência suportado e verificado no workspace antes da publicação.

## Resposta

Retorna `movement_id`, `product_id`, `tipo`, `quantidade`, `saldo_anterior`, `saldo_atual`, `data_hora`, `supplier_id` nulo, `user_id`, `motivo` e `observacao`.

## Erros

- `PERMISSION_DENIED` e erros de perfil: função central de autorização.
- `INVALID_INPUT`: quantidade não positiva ou motivo vazio; tipos fora do input declarado são rejeitados pelo validador Xano.
- `PRODUCT_NOT_FOUND`, `PRODUCT_INACTIVE`.
- `STOCK_BALANCE_NOT_FOUND`.
- `INSUFFICIENT_STOCK`.
- `STOCK_CONCURRENCY_CONFLICT` para deadlock do `db.edit`.
- `STOCK_UPDATE_FAILED` para outra falha ao editar o saldo.

Falha na gravação do movimento propaga a exceção para fora da transação, provocando rollback do `db.edit`.

## Testes e publicação

A validação estática MCP, OpenSpec e Git não comprova comportamento de runtime nem
concorrência. A validação anterior da interface de Saída ocorreu sem registrar movimentação.
Posteriormente, o usuário executou operações reais pelo navegador; os resultados reportados
estão discriminados abaixo e não comprovam cenários que foram bloqueados pela interface.

### Evidências dos testes reais informados pelo usuário

As operações foram executadas pelo NexStock com o Produto fictício ID `6`, código
`TESTE-SAIDA-20261012-001`. O usuário reporta que a Entrada e as três Saídas foram
registradas com sucesso e que as respostas mostraram os seguintes saldos:

| Operação | Quantidade | Saldo retornado |
|---|---:|---:|
| Entrada | 10,75 KG | — |
| Saída | 1,25 KG | 9,50 KG |
| Saída | 0,75 KG | 8,75 KG |
| Saída | 8,75 KG | 0 KG |

A sequência é aritmeticamente consistente: `10,75 - 1,25 - 0,75 - 8,75 = 0 KG`. Isso
constitui evidência reportada de escritas reais bem-sucedidas para esses valores, incluindo
saldo final zero. Não é evidência de rollback nem de comportamento concorrente.

O histórico exibido na interface mostrou uma Entrada e três Saídas, com horários e o usuário
`Allan Teste2`. Posteriormente, o usuário confirmou diretamente no Xano que há exatamente
esses quatro movimentos. Isso confirma a contagem no backend; não equivale a uma inspeção
completa dos payloads de resposta do `POST /exits`.

Em duas situações, a interface bloqueou a tentativa antes de haver comprovação de chamada ao
endpoint: quantidade superior ao saldo, e seleção do Produto com saldo zero, que mostrou
indisponibilidade e deixou o botão Registrar saída desabilitado. Essas observações são
rejeições de frontend. Não comprovam resposta `INSUFFICIENT_STOCK`, validação ou ausência de
escrita pelo backend para essas tentativas.

### Testes negativos diretos da API informados em 2026-10-12

O usuário confirmou chamadas diretas ao `POST /exits` com os seguintes resultados. São testes
de backend; não devem ser confundidos com as tentativas bloqueadas pela interface descritas
acima.

| Cenário | Resposta observada | Verificação de efeitos |
|---|---|---|
| Saldo insuficiente | `ERROR_CODE_INPUT_ERROR`, mensagem `INSUFFICIENT_STOCK` | Saldo continuou em `0 KG`; Histórico continuou com quatro movimentos |
| Quantidade zero | `ERROR_CODE_INPUT_ERROR`, mensagem `INVALID_INPUT` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |
| Quantidade negativa | `ERROR_CODE_INPUT_ERROR`, mensagem `INVALID_INPUT` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |
| Motivo vazio | `ERROR_CODE_INPUT_ERROR`, mensagem `INVALID_INPUT` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |
| Produto inexistente | `ERROR_CODE_INPUT_ERROR`, mensagem `PRODUCT_NOT_FOUND` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |
| Produto inativo | `ERROR_CODE_INPUT_ERROR`, mensagem `PRODUCT_INACTIVE` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |
| Requisição sem `Authorization`, com JSON válido | HTTP `401`, `ERROR_CODE_UNAUTHORIZED`, mensagem `Unauthorized - Authentication Required` | Chamada não autenticada rejeitada; não foi relatada leitura posterior independente de saldo e movimentos especificamente após essa resposta |
| Usuário autenticado sem `stock.exit` | `ERROR_CODE_INPUT_ERROR`, mensagem `PERMISSION_DENIED` | Após o conjunto de rejeições, saldo continuou em `0 KG` e o Histórico permaneceu com quatro movimentos |

O conjunto foi realizado no Produto fictício ID `6` (`TESTE-SAIDA-20261012-001`), cujo saldo
já era zero após a Entrada e as três Saídas bem-sucedidas. O usuário confirmou que, ao final
dos testes negativos, o saldo permaneceu zero e o Histórico permaneceu com exatamente quatro
movimentações: uma Entrada e três Saídas. As respostas acima são evidência reportada pelo
usuário, sem inspeção independente dos logs ou payloads brutos nesta documentação.

Uma tentativa anterior de testar autenticação retornou HTTP 500 porque o comando `curl` enviou
JSON malformado. A chamada foi corrigida com `Invoke-WebRequest`, que enviou JSON válido e
recebeu HTTP 401. O HTTP 500 decorreu da formatação da requisição de teste e não constitui
evidência de falha no mecanismo de autenticação.

### Critérios originais da tarefa 4.4 e status da cobertura

Texto original da tarefa 4.4, preservado como histórico do escopo anterior:

> Executar e registrar os cenários funcionais de autorização, inputs, Produto, saldo insuficiente, zero final, data/hora, movimento e resposta somente após aprovação explícita para escritas no datasource compartilhado; usar Produto fictício dedicado, não alterar Produtos reais e registrar que os testes não foram executados em ambiente isolado. Manter pendente até haver evidência suficiente; rollback exige ambiente isolado ou harness aprovado.

A cobertura funcional demonstrada agora inclui Entrada e Saídas reais com saldo final zero,
histórico com uma Entrada e três Saídas, além das rejeições diretas por saldo insuficiente,
quantidade zero, quantidade negativa, motivo vazio, Produto inexistente/inativo,
autenticação ausente e permissão `stock.exit` ausente. O usuário confirmou saldo zero e quatro
movimentos após os testes negativos.

Continuam sem evidência: rejeição por ausência de linha de saldo (`STOCK_BALANCE_NOT_FOUND`),
uso de `data_hora` personalizada, inspeção completa dos campos da resposta do endpoint e
rollback após falha induzida depois de uma escrita. Esses cenários foram transferidos para a
Change `validacao-avancada-operacoes-estoque`; a transferência não os declara executados.
As tentativas de saldo insuficiente e produto com saldo zero bloqueadas pela interface
continuam registradas apenas como bloqueios de frontend; as chamadas diretas negativas acima
são evidência separada de comportamento do backend.

Rollback após falha controlada não foi testado. Concorrência, prevenção contra lost update e
garantia contra overselling também não foram testadas nem comprovadas; a limitação descrita
em Atomicidade e concorrência permanece. Não se declara que a interface ou o endpoint
ofereçam proteção concorrente.

A conta Xano disponível está no plano Free e, conforme a limitação confirmada para esta
conta, não permite Sandbox nem Data Source adicional. Portanto, não há ambiente de dados
isolado disponível para esta Change. Qualquer teste que grave no datasource existente
depende de aprovação explícita e deve usar exclusivamente Produto fictício criado para
teste. A aprovação precisa abranger os registros e chamadas de escrita necessários. Os
movimentos confirmados são registros de auditoria e não devem ser apagados como limpeza;
o Produto fictício pode ser inativado após a execução, com os IDs e resultados registrados.

A prova de rollback exige uma falha controlada após a primeira escrita. Não se deve induzir
essa falha no datasource compartilhado. Sem ambiente isolado ou harness de teste aprovado,
o cenário de rollback permanece sem evidência. A tarefa 4.4 foi redefinida para a cobertura
funcional demonstrada e marcada após a transferência documental dos cenários não testados;
isso não aprova rollback, data/hora personalizada, saldo ausente ou inspeção completa das
respostas.

### Proposta de separação documental da cobertura

Esta Change mantém os requisitos funcionais de `POST /exits` e a cobertura positiva e
negativa demonstrada. A Change `validacao-avancada-operacoes-estoque` recebe formalmente a
prova de rollback, o cenário de saldo ausente e a verificação detalhada de timestamp,
respostas e invariantes após falhas, com pré-requisitos, riscos e critérios de aprovação.
Rollback deve ser testado em ambiente isolado ou harness seguro, nunca por falha induzida no
datasource compartilhado.

A proteção contra lost update e overselling continua separada na Change
`seguranca-concorrencia-estoque`. Nenhum dos testes funcionais acima demonstra serialização,
controle concorrente ou prevenção de overselling; a limitação técnica descrita em
Atomicidade e concorrência permanece.

### Evidências do preview de publicação

Em 2026-10-12 foi executado o preview isolado do endpoint, sem push:

```cmd
cmd.exe /d /s /c "set SHELL=powershell.exe&& xano.cmd workspace push -d .\xano --dry-run --no-guids -i api/inventory_stock/exits_post.xs"
```

Resultado informado: `Matched: 1 of 153 files` e `UPDATE query exits POST`. O filtro
`-i` limitou o preview ao artefato desta Change; o resultado indica atualização do endpoint
existente. O MCP também validou `exits_post.xs`.

O seed local `xano/function/inventory/seed_initial_data.xs` não foi incluído no preview.
Ele contém alterações de catálogo e grants pertencentes a outras Changes, além do conteúdo
relacionado a `stock.exit`. A conferência direta do painel do workspace confirmou que
`stock.exit` já existe no catálogo e que `stockkeeper` já possui esse grant. Assim, não é
necessário publicar o seed para satisfazer essas dependências e evitaria misturar alterações
de outras Changes no escopo de publicação desta.

Essas evidências cobrem o preview do endpoint e suas dependências de autorização. O preview
não foi um push e não comprova comportamento de runtime, rollback ou concorrência; esses
limites permanecem conforme registrados acima.

## Registro histórico da tarefa de concorrência transferida

Texto original da tarefa 4.5, mantido como requisito transferido e não realizado: Testar
concorrência em datasource isolada e obter mecanismo suportado antes de declarar proteção
contra overselling.

A conta Free não oferece o ambiente isolado exigido por esse texto. A tarefa de identificar,
implementar e testar uma proteção concorrente pertence agora a
seguranca-concorrencia-estoque. Este registro histórico não declara teste realizado nem
proteção implementada. A implementação atual permanece sujeita ao risco descrito em
Atomicidade e concorrência.
