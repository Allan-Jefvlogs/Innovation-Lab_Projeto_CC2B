# Auditoria de ações do sistema

## ADDED Requirements

### Requirement: Apresentar detalhes de auditoria de forma legível e privada
A interface MUST traduzir ações, entidades, campos conhecidos e permissões para descrições compreensíveis. Alterações com valores seguros disponíveis MUST apresentar o nome do campo e os valores anterior e novo. Valores de campos pessoais e segredos MUST NOT ser exibidos. Campos desconhecidos MUST NOT ser serializados ou expostos como JSON bruto. Eventos sem detalhes persistidos MUST ser identificados como “Detalhes não registrados”. Um ID de perfil MUST ser associado a um nome somente quando houver correspondência obtida de fonte autorizada; sem correspondência, a interface MUST NOT inventar um nome. Eventos existentes MUST NOT ser alterados retroativamente.

#### Scenario: Evento sem detalhes
- **WHEN** um evento de auditoria não possui alterações persistidas
- **THEN** a interface informa que os detalhes não foram registrados e não apresenta um traço como se fosse conteúdo

#### Scenario: Campo pessoal alterado
- **WHEN** um evento contém indicador de alteração de contato, documento, telefone ou e-mail
- **THEN** a interface identifica o campo alterado e omite seus valores

#### Scenario: Permissões alteradas
- **WHEN** um evento inclui códigos de permissões
- **THEN** a interface apresenta descrições amigáveis sem expor a estrutura JSON

### Requirement: Exportar eventos de auditoria autorizados em PDF
A exportação MUST exigir sessão válida e autorização administrativa no Reflex e MUST consultar o endpoint Xano já protegido para todos os registros que correspondam aos filtros atuais, não somente a página visível. A coleta MUST ser paginada e limitada a 500 eventos; se exceder o limite, se a coleta ficar inconsistente, ou se uma página falhar, MUST NOT gerar um PDF parcial. O arquivo MUST ser criado em memória, em A4 paisagem, conter os filtros, data/hora de emissão, as sete colunas da Auditoria e numeração de páginas, usando a mesma apresentação segura da interface. O sistema MUST NOT persistir o arquivo em diretório público ou temporário.

#### Scenario: Exportação filtrada completa
- **WHEN** um administrador exporta um conjunto filtrado de até 500 eventos e todas as páginas são lidas sem inconsistências
- **THEN** o navegador recebe um PDF completo com os filtros usados, sem incluir valores pessoais que a interface omite

#### Scenario: Limite excedido ou coleta inconsistente
- **WHEN** mais de 500 eventos correspondem aos filtros ou os metadados/páginas mudam durante a coleta
- **THEN** o sistema informa que é necessário restringir os filtros e não oferece um arquivo parcial como completo

#### Scenario: Usuário sem autorização
- **WHEN** usuário sem perfil administrativo tenta exportar eventos
- **THEN** o Reflex não consulta os dados para exportação e o Xano mantém sua autorização administrativa como proteção final

#### Scenario: Nenhum evento correspondente
- **WHEN** a consulta autorizada não encontra eventos para os filtros atuais
- **THEN** o sistema informa que não há registros e não gera um PDF com dados fictícios

### Requirement: Registrar ações bem-sucedidas no backend
O Xano MUST persistir um evento após cada mutação suportada ser concluída com sucesso. Falhas da operação principal MUST NOT produzir eventos de sucesso. O registro MUST incluir horário, ator, ação, entidade, identificador quando aplicável, resumo e alterações permitidas. MUST NOT registrar senhas, tokens, chaves, credenciais ou documentos sensíveis. O Reflex MUST NOT fabricar eventos.

#### Cenário: Mutação falha
- **WHEN** uma operação de domínio é rejeitada ou falha
- **THEN** nenhum evento de sucesso dessa operação é gravado

#### Cenário: Alteração concluída
- **WHEN** uma operação suportada é confirmada pelo Xano
- **THEN** o evento é armazenado no backend com ator autenticado e resumo legível

### Requirement: Persistir muta??o e auditoria atomicamente
Para cada endpoint instrumentado, as grava??es da opera??o de neg?cio e o evento correspondente MUST ser executados dentro da mesma `db.transaction`. A resposta MUST NOT indicar sucesso se a transa??o falhar. Uma falha ao inserir o evento MUST reverter as grava??es da opera??o principal, sujeito ? confirma??o do comportamento transacional do Xano no runtime de destino.

#### Cen?rio: Falha ao inserir o evento
- **WHEN** a muta??o de neg?cio foi executada dentro da transa??o e a inser??o de `inventory_audit_log` falha
- **THEN** a transa??o n?o deve confirmar a muta??o nem o evento e o endpoint deve retornar falha

### Requirement: Consultar auditoria protegida
`GET /audit_logs` MUST exigir autenticação e autorização administrativa no Xano, suportar filtros por período, usuário, ação e entidade, ordenar do mais recente para o mais antigo e paginar com total real. A resposta MUST projetar apenas campos necessários à consulta.

#### Cenário: Usuário sem acesso administrativo
- **WHEN** usuário sem perfil administrador consulta auditoria
- **THEN** o Xano recusa a consulta

#### Cenário: Filtros combinados
- **WHEN** administrador aplica filtros e navega páginas
- **THEN** a consulta preserva os filtros e pagina somente os eventos correspondentes

### Requirement: Substituir Histórico na navegação
O menu MUST apresentar “Auditoria” no lugar de “Histórico”. A rota antiga MUST deixar de ser registrada; entradas, saídas, movimentações e relatórios MUST continuar disponíveis e seus dados MUST permanecer intactos.

#### Cenário: Navegar no menu
- **WHEN** administrador acessa o menu
- **THEN** encontra Auditoria e não encontra Histórico

#### Cenário: Relatórios de movimentação
- **WHEN** usuário abre Relatórios
- **THEN** os movimentos existentes continuam consultáveis pelo backend sem migração ou remoção

### Requirement: Não fabricar cobertura
Eventos anteriores à implantação MUST NOT ser inventados. A interface MUST diferenciar ausência real de eventos de erro de consulta. Ações cujos endpoints ainda não tenham instrumentação MUST ser documentadas como cobertura pendente.

#### Cenário: Ainda sem eventos
- **WHEN** a consulta autorizada retorna uma lista realmente vazia
- **THEN** a interface apresenta estado vazio, não histórico retroativo

### Requirement: Exclude stock movements from this audit delivery
Stock entry and exit operations MUST NOT create events in `inventory_audit_log` in this delivery because they are already available in Reports. Their stock-balance and `inventory_movement` writes MUST remain unchanged. This exclusion applies to all entries and exits and MUST NOT remove movement data or the `/movements` endpoint. Purchase requests and email events are outside this delivery.

#### Scenario: Stock entry or exit
- **WHEN** an entry or exit updates stock and records an inventory movement
- **THEN** the operation keeps its existing transactional stock and movement writes and creates no `inventory_audit_log` event

#### Scenario: Movement reports
- **WHEN** a user with the existing report authorization opens movement reports
- **THEN** existing and new movement records remain available through `/movements`
