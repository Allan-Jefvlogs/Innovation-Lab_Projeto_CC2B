# Design — Auditoria

## Arquitetura

O Xano registra cada evento em `inventory_audit_log` a partir das funções/endpoints que executam a operação. O Reflex apenas consulta `GET /audit_logs`; não cria eventos. A leitura usa autenticação e o autorizador central exigindo `administrator`, sem introduzir perfil ou grant novo.

Cada evento mantém horário do servidor, ID e nome de exibição do ator no momento da ação, ação, entidade, ID afetado opcional, resumo e JSON de alterações permitidas. Senhas, tokens, chaves, documentos de fornecedores e credenciais não devem ser incluídos nos snapshots. Não há preenchimento retroativo.

O endpoint de leitura retorna paginação com totais e aceita período, usuário, ação e entidade. Ordenação é decrescente por horário e ID.

## Apresentação e exportação

O Reflex traduz ações, entidades, campos conhecidos e permissões. A formatação usa uma lista permitida de campos; chaves desconhecidas não exibem seus valores. Campos pessoais conhecidos apresentam somente o nome do campo e a indicação de que os valores foram omitidos. Um ID de perfil pode ser resolvido usando uma única leitura do endpoint administrativo existente `GET /permissions`; sem correspondência, a interface mantém somente o ID.

A exportação usa exatamente os filtros da tela e consulta todas as páginas do GET existente, sequencialmente, em lotes de até 100 eventos. O limite é 500 eventos. Acima dele, ou quando os metadados/IDs indicam mudança ou inconsistência durante a leitura, a exportação falha sem produzir um arquivo parcial. O PDF é gerado em memória e baixado pelo Reflex; nenhum arquivo é persistido em diretório público ou temporário. Cada página do GET continua protegida pela autorização administrativa existente no Xano.

O PDF é A4 paisagem, contém as sete colunas da tabela, cabeçalho, horário de emissão, resumo dos filtros e numeração de páginas. Textos longos são quebrados e continuam na página seguinte.

## Cobertura dos detalhes

Os eventos antigos não são enriquecidos retroativamente. O evento atual de atualização de usuário não contém `changes`; a tela informa “Detalhes não registrados”. Uma mudança local futura no writer Xano pode registrar indicadores booleanos de campos seguros alterados, sem armazenar valores pessoais. Essa melhoria do writer requer revisão/publicação separada e não faz parte desta implementação Reflex.

## Substituição da rota

O menu troca `/movimentacoes` por `/auditoria`. Entradas e Saídas continuam nas rotas existentes. O endpoint `/movements` permanece, pois Relatórios e os controles de estoque ainda dependem dele.

## Autorização e exposição

A rota exige sessão válida no Reflex e só inicia consulta quando o perfil atual é administrador. O endpoint repete a autorização no Xano. O menu não substitui essa verificação.

## Atomicidade dos eventos nas muta??es instrumentadas

Os endpoints locais das mutacoes abrangidas foram revisados. As gravacoes de negocio e o evento de auditoria permanecem na mesma transacao, com rollback em runtime ainda pendente de confirmacao no Xano.

- Cria??o de Produto: `product`, saldo inicial `inventory_stock` e evento.
- Categorias: cria??o, edi??o, ativa??o e inativa??o junto do evento correspondente.
- Produtos: edi??o, ativa??o e inativa??o junto do evento correspondente.
- Fornecedores: cria??o, edi??o e inativa??o junto do evento correspondente.
- Usu?rios: cria??o, edi??o, ativa??o, inativa??o, mudan?a de perfil e redefini??o de credencial junto do evento correspondente. Nenhum segredo ? inclu?do no evento.
- Perfis/permiss?es: substitui??o dos grants, revis?o, `inventory_permission_audit` e evento geral na mesma transa??o.
- Entradas e saidas de estoque ficam fora do escopo da Auditoria; seus endpoints mantem as gravacoes de saldo e movimento dentro da transacao, sem inserir evento em inventory_audit_log.

A atomicidade foi revisada estruturalmente: as mutacoes auditadas e seus eventos estao dentro do mesmo db.transaction. O teste induzido de rollback no Xano live foi dispensado para cumprir o prazo e nao foi executado; portanto, rollback em runtime nao esta comprovado. A tarefa 2.4 permanece pendente e nenhum teste de rollback deve ser marcado como aprovado.

A funcao Inventory/record_audit_event nao e chamada por nenhum endpoint. Ela fica fora do escopo desta publicacao seletiva; o arquivo local sera preservado, sem ser incluido no push.

## Escopo fora desta entrega

Entradas e saídas de estoque, solicitações de compra e eventos de e-mail permanecem fora do escopo atual desta change de Auditoria, conforme a decisão registrada na proposta e na tarefa 2.3. Essa exclusão não é uma pendência de implementação desta entrega. Os fluxos de entrada e saída mantêm suas gravações existentes de saldo e `inventory_movement`, sem criar eventos em `inventory_audit_log`. Solicitações de compra e eventos de e-mail não são instrumentados por esta change.

## Publicação

A tabela inventory_audit_log ja existe no workspace 152211, branch v1, ID 913875, conforme confirmado pelo usuario; nao inclui-la no push. Publicar seletivamente apenas os endpoints locais restantes de catalogo/admin e GET /audit_logs, depois de revisar o dry-run. Nao incluir entradas/saidas, solicitacoes de compra, eventos de e-mail nem Inventory/record_audit_event. A verificacao de autorizacao e consulta no Xano permanece pendente.

## Limitações e riscos residuais — ciclo atual

### Tarefa 2.4 — atomicidade em runtime

- **Implementação/evidência disponível:** os endpoints locais instrumentados colocam as gravações de negócio e o `db.add inventory_audit_log` dentro de `db.transaction`. `tests/test_audit_atomicity_contract.py` verifica essa estrutura estática; não executa Xano nem demonstra rollback.
- **Verificação ausente:** não foi executada uma falha induzida durante a gravação do evento para confirmar que o Xano reverte a mutação de negócio.
- **Motivo e tentativas:** o teste de rollback no Xano live foi dispensado anteriormente; não há uma tentativa de runtime malsucedida registrada. O código foi revisado estruturalmente, mas isso não substitui o teste.
- **Risco residual:** se o runtime não reverter a transação como esperado, uma mutação poderia persistir sem seu evento de auditoria. Não há falha desse tipo confirmada.
- **Condição para comprovação:** executar o teste somente em ambiente seguro e com autorização específica. Nenhuma nova tentativa será feita neste ciclo, conforme decisão do usuário.

### Tarefas 4.2 e 4.3 — publicação e autorização remotas

- **Implementação/evidência disponível:** o endpoint local `GET /audit_logs` exige autenticação e chama `Inventory/authorize_permission` com `administrator`; o código da interface também restringe a consulta ao administrador. As tarefas estavam marcadas como concluídas, mas a busca nos registros locais não encontrou saídas, capturas ou relatório que comprove a publicação e os resultados dos testes remotos.
- **Verificação ausente:** comprovação de que os endpoints seletivos foram publicados; resposta de uma consulta autorizada como administrador; e rejeição de uma consulta feita sem perfil administrativo. O design já registrava a verificação remota de consulta/autorização como pendente.
- **Motivo e tentativas:** não há resultados documentados que permitam confirmar esses critérios. A presença do contrato local e as marcações anteriores não provam a versão publicada nem o comportamento remoto. Nenhuma nova consulta será feita neste ciclo, conforme decisão do usuário.
- **Risco residual:** a definição remota pode divergir do código local ou a autorização publicada pode não corresponder ao contrato esperado. Isso é ausência de comprovação, não falha funcional confirmada.
- **Condição para comprovação:** obter evidência de publicação e executar, com contas autorizadas apropriadas, somente as consultas de leitura necessárias; preservar apenas status e contexto não sensível no registro.

As limitações acima mantêm as tarefas 2.4, 4.2 e 4.3 abertas. Não há falha de rollback ou de autorização remota confirmada; há critérios sem evidência suficiente. Não serão realizadas novas tentativas para essas pendências durante este ciclo.
