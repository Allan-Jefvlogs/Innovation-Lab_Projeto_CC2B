# Diagnóstico de versão e reivindicação UNIQUE

> Registro histórico, fora do escopo atual. O projeto aprovou uso acadêmico com um operador por vez e substituição do SQL por operações nativas simples. Não implementar as opções abaixo nem exigir seus testes para a entrega vigente. Consultar design.md e publicacao-academica.md.

Este documento é uma análise local. Nenhum PATCH, schema, índice, função de provisionamento ou registro remoto foi alterado. O PATCH de status continua bloqueado com seu SQL atual.

## Estado encontrado

- purchase_request tem UNIQUE em chave_idempotencia e active_product_id, mas não tem versão de negócio. Esses índices protegem criação/requisição ativa, não atualizações concorrentes do mesmo pedido.
- purchase_request_history tem evento/dados/data, sem coluna de versão ou índice de reivindicação. Colocar uma versão apenas em dados JSON não cria exclusividade no banco.
- PATCH de status exige purchase_request.status.update, mas o UPDATE condicional utiliza Direct Database Query.
- PATCH de cancelamento exige cancel ou manage, valida propriedade e status aberta/em_analise, relê dentro da transação e faz db.edit por ID. Uma mudança entre a releitura e a edição ainda pode ser sobrescrita. O catch externo agrupa falhas em PURCHASE_REQUEST_CANCEL_FAILED; não há classificação específica de conflito de versão.
- O POST cria aberta; não é uma transição de um pedido existente. Um modelo versionado exigiria versão inicial explícita/default compatível.
- O dispatcher local atualiza email_status/data_atualizacao com campos parciais, sem alterar o status comercial. Por isso data_atualizacao não serve como token de versão comercial.
- provision_purchase_profile continua com read, manage e status.update, sem administrador nem stock.read. Controle de concorrência não exige grants administrativos nem mudança desses três grants.

## Viabilidade dos blocos nativos

Xano documenta índices UNIQUE e db.add/db.edit/db.transaction, já usados no projeto sem SQL. O schema local inventory_profile_permission também demonstra índice UNIQUE composto. A criação de uma reivindicação pode usar db.add e um par de colunas tipadas (pedido, versão). Isso evita depender de uma atualização condicional não aceita pelo MCP.

A documentação PostgreSQL explica que uma inserção concorrente sobre chave UNIQUE espera a transação conflitante: se ela confirma, há violação de unicidade; se reverte, a inserção pode prosseguir. Essa é a propriedade do mecanismo de banco proposto, não uma observação do workspace Xano. É necessário confirmar que o índice composto publicado é único, efetivo e não postergado e observar o erro real do Xano. A API não pode substituir essa restrição por uma consulta prévia de existência.

Não foi encontrada restrição documentada a plano pago para esses blocos básicos. Isso torna o desenho candidato ao Free; não comprova o protocolo completo, a importação ou o comportamento transacional do workspace.

## Duas opções de schema, ainda não aprovadas para implementação

| Opção | Mudanças propostas | Consequência |
| --- | --- | --- |
| Reutilizar o histórico como reivindicação | purchase_request.versao: inteiro não nulo, inicial 0; purchase_request_history.versao_anterior: inteiro nullable para legado/eventos sem transição; UNIQUE(purchase_request_id, versao_anterior) | Evita tabela nova. O histórico de transição deve ser inserido primeiro e funcionar como reivindicação dentro da mesma transação. |
| Reivindicação separada | purchase_request.versao; nova tabela mínima com pedido e versao_esperada não nulos, UNIQUE composto e data | Mantém a ordem reivindicação → pedido → histórico; acrescenta uma tabela e uma gravação por transição. |

A primeira opção é menor, mas depende de confirmar múltiplos NULL no índice do histórico e de impedir que novas transições omitam versao_anterior. Eventos legados, criada e eventos de e-mail não devem consumir versões de transição nem receber versões fictícias retroativas. A segunda oferece campos de chave obrigatórios, mas exige governança da tabela adicional. Não usar active_product_id, chave_idempotencia, data_atualizacao ou texto livre como substitutos da versão.

## Protocolo proposto

1. Autorizar o ator pelo grant específico da operação. Receber/validar versao_esperada, status_esperado e dados de negócio; não aceitar versão negativa, nula ou futura como reserva.
2. Dentro da mesma db.transaction, reler o pedido e validar a igualdade da versão/estado, a transição e a justificativa antes da primeira gravação. Preparar incrementos e dados do histórico antes de gravar.
3. Inserir a reivindicação UNIQUE da versão v usando db.add. Nunca usar upsert, ignorar duplicidade ou prosseguir após falha desse INSERT.
4. Somente após reivindicação bem-sucedida, gravar status e versão v+1. Na rejeição/cancelamento, liberar active_product_id e preencher encerramento conforme regras atuais.
5. Gravar o histórico na mesma transação. Na opção que reutiliza o histórico, o passo 3 já insere o evento completo, e a edição do pedido vem depois dele. Na opção de tabela separada, o histórico vem depois da edição.
6. Preservar intenções de notificação do cancelamento na mesma transação, sem chamadas HTTP de envio. Não modificar estoque no status/cancelamento.
7. Tratar falhas fora da transação, com códigos sanitizados e sem retry automático. Não confirmar sucesso antes do commit e da resposta coerente.

Se duas operações lerem v, somente uma reivindicação de (pedido,v) deve confirmar. A outra falha na restrição ou encontra v+1 numa leitura posterior. Isso só protege os escritores que usam o protocolo; um db.edit legado ainda pode ignorá-lo. Precondition depois de uma gravação não deve ser usado como prova de rollback: a documentação Xano limita o rollback a falhas de operações de banco.

## Participação obrigatória dos escritores

- Converter conjuntamente status e cancelamento; não liberar a nova versão com o cancelamento legado ainda escrevendo por ID.
- Adaptar POST para iniciar a versão sem reivindicação retroativa, GETs para projetar a versão, cliente/Reflex para enviar a versão confirmada e testes/caches para preservar os novos dados.
- Recebimento futuro deve consumir a versão e manter pedido, entrada real, saldo, movimento e histórico consistentes. recebimento_parcial/concluida continuam fora do seletor manual.
- Proibir outros endpoints, tarefas ou edições administrativas concorrentes que alterem status/versão sem o protocolo. Escritas parciais exclusivamente de email_status não devem consumir a versão comercial.
- Publicar de forma coordenada, com escritas do módulo suspensas durante a migração para evitar mistura entre escritores antigos e novos. Sem atribuir perfis/usuários automaticamente.

## Erros, rollback e recuperação

- Versão divergente antes de gravar: conflito de domínio, sem reivindicação nem histórico.
- Violação do índice da reivindicação: deve abortar a transação; traduzir o erro real somente depois de identificar seu tipo/código no Xano. Não afirmar HTTP 409 sem validar o mapeamento.
- Falha do histórico na opção separada: precisa reverter edição e reivindicação. Se o histórico for a própria reivindicação, sua falha ocorre antes de editar; uma falha de banco posterior precisa reverter o histórico também.
- Uma edição que retorne null/zero linhas sem erro, uma transformação que falhe depois do INSERT ou uma captura interna que suprima erros pode quebrar a promessa de tudo-ou-nada. O comportamento precisa ser demonstrado; não basta colocar os passos visualmente dentro de db.transaction.
- Timeout após possível commit: consultar pedido/versão/histórico, sem criar outra reivindicação ou repetir PATCH automaticamente. Uma reivindicação confirmada sem correspondente avanço de versão/histórico é incidente de integridade, não conflito normal.
- Reivindicações confirmadas não devem ser apagadas por TTL nem removidas automaticamente após timeout. Uma reivindicação órfã exige reconciliação manual; apagar a proteção pode permitir repetição de uma versão antiga.
- UNIQUE pode aguardar outra transação e pode participar de deadlocks. Manter transações curtas, ordem consistente de acesso ao pedido/estoque e sem chamadas externas. Observar lock timeout/deadlock reais e não implementar retry agressivo.

## Alternativa nativa adicional encontrada

A página oficial Query All Records possui seção Lock: “When used with a database transaction”. Uma amostra somente em memória com db.query purchase_request, return single e lock=true dentro de db.transaction passou no MCP 2.2.6. Nenhum arquivo de endpoint foi alterado e a amostra não foi executada.

Isso é evidência de uma opção documentada e sintaxe aceita, não de disponibilidade no Free nem de qual lock é adquirido, até quando é mantido ou como funciona após espera. Recomenda-se esclarecer/validar essa opção antes de aprovar novos campos/índices: ela pode evitar a mudança estrutural. Mesmo com lock, todos os escritores precisam validar o estado após adquirir a proteção; um cancelamento que já tenha decidido com base em leitura antiga pode sobrescrever depois de esperar.

## Plano de prova, mediante autorização futura

1. Confirmar workspace/branch/datasource, recursos do plano, schema, índice e regras reais; preservar cópia dos contratos. Usar contas e pedido de demonstração autorizados, sem envio de e-mails.
2. Verificar a opção nativa Lock e seu comportamento em duas operações controladas, sem migrar schema por hipótese.
3. Caso seja aprovada a alternativa UNIQUE, definir primeiro qual dos dois schemas usar e preparar migração compatível, contratos e todos os escritores locais.
4. Executar uma transição válida: um incremento, um evento, active_product_id coerente.
5. Executar duas operações concorrentes com a mesma versão e destinos diferentes permitidos; somente uma pode confirmar. Testar status contra cancelamento, não apenas dois status.
6. Descobrir uma restrição real que cause falha de banco dentro da transação. Conferir por leituras que pedido, versão, reivindicação, histórico e outbox voltaram ao estado anterior. Não presumir que ID inexistente ou campo omitido provoca erro.
7. Testar versão antiga, repetição após timeout, múltiplos NULL legados (se histórico for reivindicação), falha de edição/histórico, zero linhas e classificação sanitizada de duplicidade/deadlock.
8. Se houver gravação parcial, parar a liberação e reconciliar somente os registros de demonstração autorizados. Não apagar reivindicações nem alterar dados comerciais para “destravar”.

O PATCH atual continua fora da publicação. A análise UNIQUE está concluída como desenho; sua garantia no Xano Free permanece não comprovada.

## Fontes

- https://docs.xano.com/the-database/database-performance-and-maintenance/indexing
- https://docs.xano.com/the-function-stack/functions/database-requests/database-transaction
- https://docs.xano.com/the-function-stack/functions/database-requests/query-all-records
- https://www.postgresql.org/docs/current/index-unique-checks.html
