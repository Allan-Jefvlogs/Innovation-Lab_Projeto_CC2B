## ADDED Requirements

### Requirement: Cabeçalho e saudação autenticada
O Dashboard MUST preservar a sidebar fixa e o layout aprovado, remover a busca sem funcionalidade e mostrar uma saudação baseada no primeiro nome autenticado e no horário de São Paulo. O menu do usuário MUST oferecer Alterar senha e Sair, reutilizando o logout existente.

#### Scenario: Saudação
- **WHEN** uma sessão válida abre o Dashboard
- **THEN** o texto usa Bom dia (05–11), Boa tarde (12–17) ou Boa noite (18–04) em `America/Sao_Paulo`
- **AND** usa o primeiro nome disponível sem inventar nome
- **AND** não mostra “VISÃO GERAL DO ESTOQUE” nem “Aqui está o resumo do seu estoque hoje”.

#### Scenario: Logout
- **WHEN** o usuário seleciona Sair
- **THEN** `AuthState.logout` limpa a sessão local e retorna ao login.

### Requirement: Notificações baseadas em eventos persistidos
O backend MUST derivar notificações de `purchase_request_history` e persistir somente a leitura individual em uma estrutura mínima. MUST NOT incluir eventos de e-mail, criar histórico retroativo ou inferir uma conclusão sem evento persistido.

#### Scenario: Acesso próprio
- **WHEN** usuário autenticado tem `purchase_request.read`, mas não `purchase_request.manage`
- **THEN** lista, contador e marcação são limitados aos pedidos em que ele é solicitante
- **AND** identidade vem de `$auth.id`, não de parâmetro fornecido pelo cliente.

#### Scenario: Acesso global
- **WHEN** usuário tem `purchase_request.read` e `purchase_request.manage`, ou é administrador pelo mecanismo existente
- **THEN** pode consultar eventos de todos os pedidos.

#### Scenario: Marco de ativação
- **WHEN** a central é habilitada
- **THEN** somente eventos com data igual ou posterior a `$env.NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT` são considerados
- **AND** ausência do marco falha fechada, sem incluir histórico anterior.

#### Scenario: Configuração de marco inválida
- **WHEN** o marco está ausente, vazio, fora do formato Unix milliseconds de 13 dígitos positivos ou não pode ser convertido fielmente
- **THEN** GET e PATCH rejeitam antes de acessar eventos, com categorias sanitizadas distintas
- **AND** não expõem o valor da variável nem usam um marco substituto.

#### Scenario: Leitura individual
- **WHEN** um evento acessível é marcado como lido
- **THEN** a leitura é gravada para o usuário autenticado e o estado da interface muda somente após confirmação
- **AND** repetição sequencial não cria uma segunda leitura.

#### Scenario: Eventos apresentados
- **WHEN** há eventos persistidos de `criada`, `status_alterado`, `cancelada`, `rejeitada` ou `recebimento_registrado`
- **THEN** a interface mostra data/hora, descrição legível, referência ao pedido e estado lida/não lida
- **AND** não apresenta evento de e-mail como evento comercial nem cria conclusão fictícia.

### Requirement: Central compacta com rolagem incremental
A central MUST preservar o cabeçalho com título e total não lido e apresentar uma lista com altura máxima, rolagem vertical independente e sem rolagem horizontal. MUST remover os botões Anterior e Próxima, preservando a paginação do GET existente. O painel MUST permanecer alinhado ao sino e limitado à largura disponível.

#### Scenario: Aproximação do fim da lista
- **WHEN** o usuário rola a lista perto do fim, o painel está aberto e existe próxima página
- **THEN** o frontend consulta uma página adicional de forma controlada e acrescenta seus eventos à lista existente
- **AND** mantém a ordem confirmada, elimina duplicatas por history_id e ignora eventos de scroll referentes a uma página já consumida
- **AND** não inicia outra chamada enquanto uma operação está em andamento.

#### Scenario: Erro ao acrescentar página
- **WHEN** uma página adicional falha ou ocorre rate limit
- **THEN** os itens já carregados e a última página confirmada são preservados
- **AND** novos eventos de scroll não repetem a tentativa; recuperação exige ação explícita após o cooldown
- **AND** não há polling, retry automático nem alteração do orçamento do coordenador.

#### Scenario: Alternativa por teclado
- **WHEN** há mais registros e o usuário não utiliza a rolagem
- **THEN** uma ação compacta Carregar mais no fim da lista usa as mesmas travas de carregamento
- **AND** não há navegação Anterior/Próxima nem substituição dos itens já apresentados.

#### Scenario: Contador sobre o sino
- **WHEN** o total não lido é zero ou indisponível
- **THEN** o botão mostra somente o sino de contorno
- **WHEN** há de uma a nove notificações não lidas
- **THEN** um badge circular vermelho discreto com número branco aparece no canto superior direito do sino
- **WHEN** há dez ou mais
- **THEN** o badge mostra 9+, mantendo o total real no cabeçalho e na descrição acessível
- **AND** uma confirmação de leitura atualiza o total e o badge sem alterar o tamanho ou alinhamento do botão.

### Requirement: Abertura de pedido a partir de notificação
A central MUST abrir `/compras/{purchase_request_id}` ao acionar uma notificação acessível, reutilizando a autorização atual dos detalhes no Reflex e no Xano. MUST usar apenas purchase_request_id/history_id da notificação carregada para a sessão, sem alterar o pedido.

#### Scenario: Evento não lido
- **WHEN** o usuário autorizado clica numa notificação não lida ou ativa seu botão por teclado
- **THEN** o frontend tenta o PATCH existente com history_id uma única vez, respeitando o cooldown e travas existentes
- **AND** atualiza a leitura e o contador somente após confirmação e navega para o purchase_request_id correspondente.

#### Scenario: Falha na leitura
- **WHEN** a tentativa de leitura falha ou tem resultado ambíguo
- **THEN** o frontend preserva o estado não lido e o contador confirmado e permite abrir o pedido
- **AND** não repete o PATCH automaticamente; sessão expirada ou trocada impede usar os dados antigos para navegar.

#### Scenario: Evento já lido ou clique repetido
- **WHEN** o evento já está lido
- **THEN** a ação apenas navega, sem outro PATCH
- **WHEN** há cliques rápidos repetidos na mesma abertura
- **THEN** a ação em andamento ou já encaminhada à navegação não é executada novamente.

#### Scenario: Leitura sem abertura
- **WHEN** o usuário clica em Marcar como lida
- **THEN** a leitura segue o fluxo existente sem navegar
- **AND** o clique não propaga à ação de abertura da notificação.

#### Scenario: Permissões e estados finais
- **WHEN** o perfil não tem as permissões atuais exigidas pela rota de detalhes
- **THEN** a interface não amplia o acesso nem marca a leitura para simular abertura
- **WHEN** o usuário autorizado abre um evento de pedido cancelado ou concluído
- **THEN** o status final não impede a navegação; o GET de detalhes continua decidindo a autorização do registro.

### Requirement: Alteração voluntária de senha
O Xano MUST validar a senha atual do usuário autenticado, a confirmação e a política de senha existente antes de gravar a senha. Os valores de senha MUST ser sensíveis e MUST NOT aparecer em logs ou auditoria.

O endpoint MUST usar exclusivamente `$auth.id`, sem aceitar um identificador arbitrário. MUST rejeitar senha nova equivalente à armazenada usando verificação nativa, preservar o tipo password do schema e retornar somente confirmação sanitizada. A política local existente de no mínimo oito caracteres, uma letra ASCII e um número MUST ser preservada. Contas em troca inicial obrigatória continuam usando o fluxo já existente.

#### Scenario: Senha inválida
- **WHEN** senha atual, confirmação ou política falha
- **THEN** a senha armazenada não é alterada e uma mensagem segura é exibida.

#### Scenario: Nova senha repetida
- **WHEN** a nova senha corresponde ao hash da senha atual
- **THEN** o backend rejeita com NEW_PASSWORD_MUST_DIFFER antes de qualquer gravação.

#### Scenario: Privacidade e cancelamento
- **WHEN** o usuário conclui, cancela ou envia o formulário
- **THEN** o frontend não persiste senhas em State/LocalStorage, limpa os campos do formulário e usa mensagens fixas sem payloads sensíveis
- **AND** mostrar/ocultar senha usa controles acessíveis e não muda os valores nem os envia por eventos de digitação.

#### Scenario: Falha ou resposta ambígua
- **WHEN** o backend falha, retorna confirmação inválida ou a conexão expira
- **THEN** não há mensagem de sucesso nem retry automático; o usuário recebe orientação para verificar o login antes de repetir
- **AND** um 429 respeita cooldown sem aumentar o orçamento do coordenador.

#### Scenario: Alteração confirmada
- **WHEN** o Xano confirma a nova senha
- **THEN** o frontend limpa a sessão local e exige novo login
- **AND** a interface não afirma que outros tokens foram revogados.
- **AND** a tela de login apresenta o aviso existente de senha alterada.

### Requirement: Gráfico de linhas real com períodos sem misturar unidades
Quando o contrato agregado estiver publicado e habilitado, o Dashboard MUST manter o gráfico de linhas atual, suas cores, dimensões, legenda e eixos. MUST mostrar contagens de operações, sem somar quantidades de unidades diferentes, com seleção de últimos 7 dias (padrão), 30 dias ou 12 meses em `America/Sao_Paulo`. Os períodos diários incluem hoje; os 12 meses são meses civis, incluindo o mês corrente, com agrupamento mensal.

O endpoint MUST usar operações nativas compatíveis com o Xano Free, sem Direct Database Query. A agregação MUST consumir todos os movimentos do intervalo semiaberto, inclusive quando ultrapassarem o tamanho de uma página, e MUST NOT realizar consultas por produto ou por linha.

#### Scenario: Consulta agregada
- **WHEN** a API é autorizada por `movement.read` ou `report.read`
- **THEN** uma resposta contém todas as datas do período escolhido (7 ou 30 dias, ou 12 meses) e as cinco movimentações recentes
- **AND** dias sem movimento têm zero somente após agregação completa
- **AND** os endpoints de relatório permanecem inalterados.

#### Scenario: Limites de datas
- **WHEN** o período começa na fronteira de um dia em São Paulo e termina após 7 ou 30 dias, ou começa no primeiro dia do mês e termina após 12 meses civis
- **THEN** movimentos no início são incluídos e movimentos exatamente no fim são excluídos
- **AND** os agrupamentos usam datas de São Paulo, mesmo quando a data UTC é diferente
- **WHEN** o intervalo é parcial, invertido ou incompatível com o período selecionado
- **THEN** o endpoint rejeita a consulta antes das leituras de movimentações, sem retornar zeros fictícios.

#### Scenario: Contagens e recentes
- **WHEN** existem operações com quantidades e unidades diferentes
- **THEN** cada operação conta uma vez em seu dia e tipo
- **AND** as cinco movimentações recentes mantêm suas quantidades individuais e não ficam limitadas ao intervalo do gráfico.

#### Scenario: Contrato não publicado ou erro
- **WHEN** a flag de integração está desligada ou a consulta falha
- **THEN** a página não chama um contrato indisponível nem mostra série demonstrativa como dado real
- **AND** erro não é convertido em série zerada.

#### Scenario: Troca de senha ainda não publicada
- **WHEN** `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED` está desligada
- **THEN** os campos e ação de envio permanecem desabilitados
- **AND** nenhum PATCH de senha é enviado.

### Requirement: Orçamento, cache e atualização
As leituras MUST reutilizar o coordenador e cache por sessão existentes. MUST NOT adicionar polling ou aumentar o orçamento configurado.

#### Scenario: Carga fria autorizada
- **WHEN** todas as quatro fontes do Dashboard e a central de notificações estão habilitadas e autorizadas
- **THEN** há no máximo cinco GETs de dados, além da validação de sessão
- **AND** o gráfico agregado substitui o GET separado de movimentações recentes.

#### Scenario: Sem permissão de compras
- **WHEN** o usuário não tem `purchase_request.read`
- **THEN** não é feito GET do resumo de compras nem das notificações, e os demais indicadores continuam independentes.

#### Scenario: Cache da central
- **WHEN** o usuário abre o sino com resposta ainda válida no cache
- **THEN** a consulta não é repetida
- **AND** após logout ou troca de identidade, os itens privados anteriores não são reutilizados.

#### Scenario: Troca do período do gráfico
- **WHEN** o usuário escolhe outro período autorizado
- **THEN** somente a fonte de movimentações é consultada, reutilizando cache por sessão, intervalo e período
- **AND** nenhuma linha de outro período é apresentada como pertencente à seleção atual
- **AND** o componente permanece um gráfico de linhas, sem substituição por barras.
- **AND** o seletor usa três chips compactos horizontais com destaque para o período atual, sem recarregar a página.

#### Scenario: Transporte de fronteiras de datas
- **WHEN** o cliente envia qualquer um dos três períodos
- **THEN** envia timestamps Unix em milissegundos correspondentes às fronteiras civis de São Paulo
- **AND** o backend reconstrói meia-noite com hora explícita antes de validar a igualdade do início, sem remover a proteção.

#### Scenario: Falha e mudança de escopo da central
- **WHEN** uma consulta retorna 429 ou o escopo/sessão muda durante a requisição
- **THEN** não há retry automático e o cooldown existente é respeitado
- **AND** resultados de outra sessão ou do escopo global anterior não são aplicados à interface.
