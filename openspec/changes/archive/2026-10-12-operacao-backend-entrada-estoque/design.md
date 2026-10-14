# Design: Operação backend de Entrada de Estoque

## Contexto

`inventory_stock` é a fonte oficial de saldo, com um registro único por Produto e quantidade decimal não negativa. O projeto já estabelece movimentações como histórico confirmado, quantidade positiva, Produto obrigatório, motivo obrigatório, Fornecedor contextual opcional em entradas e usuário responsável. Ainda não há tabela ou endpoint local para gravar movimentações.

## Decisões técnicas

### Modelo persistido

Criar `inventory_movement` com:

| Campo | Tipo | Regra |
|---|---|---|
| `id` | inteiro | chave primária |
| `product_id` | inteiro, referência a `product` | obrigatório |
| `tipo` | enum | `entrada` ou `saida`; nesta change somente `entrada` é criada |
| `quantidade` | decimal | positiva em operações confirmadas |
| `data_hora` | timestamp | obrigatória no registro; definida pelo backend |
| `user_id` | inteiro, referência a `user` | usuário autenticado, nunca aceito do cliente |
| `supplier_id` | inteiro anulável, referência a `supplier` | opcional; preserva Fornecedor contextual da entrada |
| `motivo` | texto | obrigatório |
| `observacao` | texto anulável | opcional |

Não duplicar código/nome do Produto, descrição do Fornecedor, situação de estoque, saldo anterior ou saldo posterior na tabela. O saldo anterior e posterior são calculados pela operação e incluídos na resposta; o histórico mantém os dados da movimentação e as referências estáveis.

### Endpoint e autorização

Adicionar `POST /entries` ao grupo existente `Inventory Stock`, canonical `estoque`. O endereço lógico publicado segue o padrão do grupo, `api:estoque/entries`. Requer `auth = "user"` e chama `Inventory/authorize_permission` com `stock.entry`.

`stock.entry` segue o padrão recurso.ação já adotado (`stock.read`, `product.create`). O seed cria o código idempotentemente e acrescenta o grant somente a `stockkeeper`. O perfil `administrator` recebe acesso integral pelo bypass central; `read_only` não recebe o grant. O seed permanece aditivo e não remove grants configurados manualmente.

### Entrada e validação

Corpo aceito:

```json
{
  "product_id": 123,
  "quantidade": 10.5,
  "supplier_id": 5,
  "data_hora": "2026-09-29T10:30:00Z",
  "motivo": "Compra",
  "observacao": "Nota fiscal 123"
}
```

`supplier_id`, `data_hora` e `observacao` são opcionais. Não há `user_id` no contrato. `product_id`, `quantidade` e `motivo` são obrigatórios. O Xano valida o tipo timestamp no input; quantidade zero/negativa, motivo vazio, Produto inexistente/inativo, Fornecedor inexistente/inativo e ausência de saldo são rejeitados antes de qualquer confirmação.

O Fornecedor padrão cadastrado no Produto não é consultado nem imposto pelo backend nesta operação. O ID escolhido pelo usuário é validado independentemente, permitindo outro Fornecedor ativo ou nenhum Fornecedor.

### Data/hora efetiva

Dentro da transação, inicializar `data_hora` com `now` do Xano e substituir pelo timestamp informado quando presente. Assim a omissão usa o relógio do backend durante a conclusão; não depende do horário do cliente.

### Transação e concorrência

`auth = "user"` autentica a requisição; a primeira etapa do stack transacional chama `Inventory/authorize_permission` com `stock.entry`. A quantidade e o motivo também são verificados antes de ler Produto, Fornecedor ou saldo. A transação valida Produto ativo, Fornecedor ativo quando enviado e saldo existente. O saldo ausente é tratado como inconsistência (`STOCK_BALANCE_NOT_FOUND`), sem criação silenciosa, pois a fundação exige saldo zero para todo Produto.

O primeiro teste runtime do endpoint na instância atual retornou `payload: Not supported. Please upgrade your Xano instance.` e `statement: Throw Error` ao executar o bloco `db.direct_query`. Embora o MCP documente a sintaxe de `db.direct_query`, essa documentação não garante disponibilidade no plano/runtime deste workspace. O endpoint deixa de depender desse recurso.

A alternativa suportada usa as operações nativas `db.get` e `db.edit` dentro de `db.transaction`: lê o saldo existente, calcula `saldo_atual + quantidade` em XanoScript e grava o resultado no mesmo registro de `inventory_stock`. Logo após o cálculo, `db.edit` atualiza o saldo; depois, `db.add` cria a movimentação, ainda na mesma transação. A documentação do MCP descreve `db.transaction` como execução atômica das operações incluídas. Falha na atualização, inserção do histórico ou qualquer validação propaga erro e reverte as escritas da transação. A restrição única de `inventory_stock.product_id` mantém a cardinalidade 1:1.

Esta alternativa é read-modify-write. A instância não disponibiliza no mecanismo XanoScript validado uma operação nativa de incremento atômico nem uma sintaxe confirmada de row lock/compare-and-set. A consulta seguida de edição reduz a janela entre leitura e gravação, mas não impede que duas requisições simultâneas leiam o mesmo saldo e uma sobrescreva o incremento da outra. Portanto, atomicidade entre saldo e histórico permanece, mas não há garantia contra lost update sob concorrência. Não se declara isolamento serializável nem locking explícito. Uma garantia forte exigirá um mecanismo de serialização oficialmente suportado pela instância ou upgrade; até lá, entradas concorrentes para o mesmo Produto são um risco conhecido.

### Resposta de sucesso

Retornar o ID do movimento, Produto, tipo, quantidade, saldo anterior/atual, data/hora efetiva, Fornecedor e usuário responsável. A resposta vem dos registros/resultados persistidos da transação.

### Erros

Usar códigos estáveis compatíveis com as APIs existentes:

- autorização: `PERMISSION_DENIED` pelo autorizador central;
- quantidade igual a zero/negativa ou motivo vazio: `INVALID_INPUT`; tipos não conversíveis (por exemplo, texto no decimal ou timestamp malformado) são rejeitados pelo validador de input do Xano antes do stack;
- Produto ausente: `PRODUCT_NOT_FOUND`;
- Produto inativo: `PRODUCT_INACTIVE`;
- Fornecedor ausente: `SUPPLIER_NOT_FOUND`;
- Fornecedor inativo: `SUPPLIER_INACTIVE`;
- deadlock reportado durante a edição do saldo: `STOCK_CONCURRENCY_CONFLICT`;
- outra falha na edição do saldo: `STOCK_UPDATE_FAILED`;
- timestamp malformado: rejeição pelo validador nativo do input `timestamp`, antes do stack e sem escrita; o código/corpo exato do erro de framework precisa de runtime em datasource isolada;
- saldo não inicializado: `STOCK_BALANCE_NOT_FOUND`.

O bloco de edição do saldo trata deadlock com código estável `STOCK_CONCURRENCY_CONFLICT` e demais erros daquele comando com `STOCK_UPDATE_FAILED`. Falhas posteriores, inclusive ao inserir a movimentação, propagam falha para fora da transação. Uma falha de gravação não pode deixar movimento ou saldo parcial.

## Alternativas consideradas

- **Ler saldo, somar no XanoScript e gravar com `db.edit`:** adotada como alternativa disponível na instância. Mantém saldo e movimento na mesma transação, mas pode perder incremento em concorrência; essa limitação deve ser removida antes de alegar segurança para entradas concorrentes.
- **Recalcular o saldo a partir do histórico:** rejeitada porque a fundação definiu `inventory_stock` como saldo oficial e o usuário não quer reconstrução do histórico.
- **Criar saldo ausente automaticamente nesta operação:** rejeitada para não ocultar falha de inicialização/migração; toda criação de Produto já inicializa saldo e existe rotina explícita de backfill.
- **Usar Fornecedor padrão como obrigação:** rejeitada; é sugestão da interface, não uma regra de fornecedor exclusivo.

## Riscos e validação pendente

- `db.direct_query` falhou em runtime na instância com indicação explícita de upgrade necessário; foi removido desta operação.
- O mecanismo `db.get` + `db.edit` é validável no MCP e participa da transação, mas não fornece incremento atômico nem proteção contra lost update. Testes concorrentes permanecem necessários e não devem ser considerados aprovados pela validação estática.
- Deve-se confirmar que os nomes físicos SQL correspondem aos slugs/campos Xano publicados no workspace.
- O unique index garante um saldo por Produto; a inicialização de todos os saldos existentes é pré-condição operacional.
- A cobertura runtime foi executada parcialmente no datasource disponível, sem isolamento: há uma Entrada real e testes negativos diretos reportados pelo usuário. O escopo e os limites dessas evidências estão consolidados na seção abaixo; elas não comprovam rollback nem concorrência.

## Fronteiras

Esta change altera somente o backend local e seus artefatos OpenSpec. Não altera Reflex, saldo pela interface, Saída, autenticação, quick-start `admin/member`, histórico consultável, nem sincroniza/publica qualquer artefato.

## Evidências de runtime e revisão de importação

O usuário confirmou que `POST /entries` foi exercitado pelo NexStock com uma Entrada real de
`10,75 KG` no Produto fictício ID `6`. O Histórico confirmou a movimentação. As tabelas
`inventory_stock` e `inventory_movement` estavam disponíveis e foram utilizadas. Esta
evidência demonstra uma operação de Entrada bem-sucedida no runtime informado; não comprova
por si só rollback, concorrência ou todos os cenários avançados da matriz original da tarefa 4.4, que foram transferidos.

Foi realizado um dry-run isolado do arquivo `xano/api/inventory_stock/entries_post.xs`, com
resultado `Matched: 1 of 153 files` e `UPDATE query entries POST`. Nenhuma operação `DELETE`
apareceu no preview. O filtro isolou o endpoint existente para revisão e o resultado foi
somente um preview: não publicou nem aplicou diferenças locais no workspace remoto.

O usuário confirmou diretamente no painel Xano que `stock.entry` existe no catálogo de
permissões e que `stockkeeper` possui o grant. As tabelas necessárias já estavam disponíveis
e foram usadas pela operação real. Nesta revisão não foi identificada necessidade de incluir
o seed, tabelas ou funções compartilhadas no escopo do preview; não foi executado seed nem
publicação.

A tarefa 4.5 confirma exclusivamente a revisão do escopo do preview e das dependências remotas, sem representar publicação efetiva. A tarefa 4.4 foi redefinida para a cobertura funcional executada e documentada abaixo; os cenários avançados foram transferidos, sem aprovação presumida. A ausência de Sandbox/Data Source isolada na conta Free e o risco de concorrência por read-modify-write continuam registrados.

## Consolidação da cobertura funcional da tarefa 4.4

### Texto original da tarefa 4.4 preservado como histórico

A tarefa foi reformulada para refletir a cobertura demonstrada. Este é o texto original, mantido sem checkbox histórico:

> Executar testes funcionais em datasource isolada: autorização, validações, timestamp, incremento e atomicidade; testar concorrência depois de adotar mecanismo que impeça lost update.

### Evidências de runtime informadas pelo usuário

| Cenário | Resultado confirmado | Fonte e limite da evidência |
|---|---|---|
| Entrada válida pelo NexStock, Produto fictício ID `6`, quantidade `10,75 KG` | O usuário confirmou sucesso, saldo atualizado e movimentação registrada no Histórico | Confirmação expressa do usuário e registro no Histórico observado por ele; não foi anexado nesta Change payload bruto, log exportado ou captura de tela |
| Entrada e Saída: Produto inexistente | O usuário confirmou rejeição com o resultado esperado pelo contrato (`PRODUCT_NOT_FOUND`) | Confirmação expressa de chamada direta ao backend; sem resposta bruta/captura arquivada |
| Entrada e Saída: Produto inativo | O usuário confirmou rejeição com o resultado esperado pelo contrato (`PRODUCT_INACTIVE`) | Confirmação expressa de chamada direta ao backend; sem resposta bruta/captura arquivada |
| Entrada e Saída: requisição sem autenticação | O usuário confirmou rejeição conforme esperado | Confirmação expressa de chamada direta ao backend; status e corpo brutos não foram incluídos na evidência recebida |
| Entrada e Saída: usuário autenticado sem a permissão necessária (`stock.entry`/`stock.exit`) | O usuário confirmou rejeição conforme esperado pelo contrato (`PERMISSION_DENIED`) | Confirmação expressa de chamada direta ao backend; sem resposta bruta/captura arquivada |
| Entrada e Saída: quantidade zero ou negativa | O usuário confirmou rejeição conforme esperado pelo contrato (`INVALID_INPUT`) | Confirmação expressa de chamada direta ao backend; sem resposta bruta/captura arquivada |
| Entrada e Saída: motivo vazio | O usuário confirmou rejeição conforme esperado pelo contrato (`INVALID_INPUT`) | Confirmação expressa de chamada direta ao backend; sem resposta bruta/captura arquivada |

Os códigos entre parênteses são os resultados definidos pelo contrato local para os cenários;
como o usuário não forneceu os corpos/status brutos das chamadas negativas, eles são registrados
como resultado esperado confirmado, não como resposta bruta inspecionada independentemente.
Para o caso positivo, o registro correspondente no Histórico foi confirmado pelo usuário; não
há captura ou export desse registro anexado a esta Change.

A cobertura aconteceu no datasource disponível, não em Sandbox ou Data Source isolada. A conta
Xano utilizada está no plano Free e não oferece esses recursos. O dry-run e a revisão de
importação estão documentados acima e não equivalem à execução ou publicação do endpoint.

### Cenários ainda não comprovados e transferência

Permanecem sem comprovação: rollback provocado depois da primeira escrita, cenário de saldo
`inventory_stock` ausente, `data_hora` personalizada, inspeção de todos os campos das respostas
de Entrada e Saída e invariantes de saldo/movimentos após falhas. Esses testes avançados foram
transferidos para `validacao-avancada-operacoes-estoque`; transferência não significa que foram
executados. Devem aguardar ambiente isolado ou harness apropriado quando houver risco de falha
induzida ou alteração de estado.

Concorrência, lost update e prevenção de overselling pertencem exclusivamente a
`seguranca-concorrencia-estoque`. A Entrada usa read-modify-write (`db.get` + `db.edit`), e a
cobertura funcional sequencial aqui registrada não prova proteção concorrente.
