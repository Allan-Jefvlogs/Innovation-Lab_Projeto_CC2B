# NextStock

Sistema de gerenciamento de estoque desenvolvido com **Python/Reflex** e **Xano**.

Repositório: [Allan-Jefvlogs/Innovation-Lab_Projeto_CC2B](https://github.com/Allan-Jefvlogs/Innovation-Lab_Projeto_CC2B)

Este README apresenta a versão acadêmica, suas jornadas de uso e as limitações conhecidas. As orientações consideram o código local e os registros de validação disponíveis em 16/11/2026. Prazo da atividade: **22/11/2026, às 23h59**.

## 1. Apresentação

O **NextStock** centraliza o cadastro de materiais, o acompanhamento do estoque e o registro de entradas e saídas. Também permite solicitar reposição, acompanhar compras e registrar o recebimento dos produtos.

O problema tratado é a dificuldade de manter informações consistentes quando cadastros, movimentações e pedidos ficam dispersos. O sistema reúne essas informações para ajudar a identificar itens abaixo do mínimo, acompanhar solicitações e reconhecer os responsáveis pelas operações.

O público-alvo são empresas com almoxarifado ou estoque de materiais e as pessoas responsáveis por sua gestão, operação, consulta e compras.

O projeto utiliza Reflex para a interface e o servidor da aplicação Python, Xano para os serviços e a persistência dos dados, Git/GitHub para versionamento e OpenSpec para organização dos requisitos. A identidade visual utiliza sálvia, menta, pêssego, rosa e taupe.

## 2. Acesso ao aplicativo

### Disponibilidade e requisitos de acesso

Não há um endereço público de deploy confirmado para informar neste documento. O endereço do repositório não é o endereço do aplicativo.

Para utilizar o sistema, é necessário:

- Ter uma conta ativa previamente cadastrada pela administração, com perfil e permissões adequados.
- Receber as credenciais por um canal privado autorizado. Este repositório não fornece contas ou senhas de demonstração.
- Ter acesso à internet e ao ambiente Xano configurado, mesmo ao executar o Reflex localmente.
- Usar um navegador atualizado. A apresentação foi preparada para uso em notebook, com adaptações de layout para telas menores.

### Execução local no Windows/PowerShell

Na pasta raiz do projeto, com o ambiente virtual já preparado:

```powershell
.\scripts\iniciar_nexstock_dev.ps1
```

O [inicializador de desenvolvimento](scripts/iniciar_nexstock_dev.ps1) utiliza o Reflex instalado em `.venv` (o ambiente isolado das dependências Python do projeto), executa a aplicação em modo de desenvolvimento e não habilita flags adicionais. Flags são opções de configuração que habilitam ou desabilitam funcionalidades.

Como alternativa, usando o mesmo ambiente virtual:

```powershell
.\.venv\Scripts\reflex.exe run --env dev
```

Com a `.venv` ativada, também é possível usar `reflex run`. Aguarde a inicialização e abra o **endereço do frontend exibido no terminal**, correspondente à interface acessada pelo navegador. A porta pode variar conforme o ambiente; não há um servidor local permanentemente disponível garantido por este README. Para encerrar a execução, utilize `Ctrl+C` no terminal.

Se o projeto ainda não estiver instalado, obtenha o repositório e, na sua raiz, prepare uma `.venv` somente se ela não existir:

```powershell
git clone https://github.com/Allan-Jefvlogs/Innovation-Lab_Projeto_CC2B.git
cd Innovation-Lab_Projeto_CC2B
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\iniciar_nexstock_dev.ps1
```

É necessário ter Python e Git instalados. As versões das dependências estão em [requirements.txt](requirements.txt), incluindo Reflex 0.9.12. Os caminhos dos comandos são relativos à raiz do projeto; o nome da pasta criada pelo clone é o nome do repositório, `Innovation-Lab_Projeto_CC2B`. A primeira inicialização também pode precisar baixar recursos da interface. **A instalação em outra máquina não foi validada na preparação deste manual.**

O cliente utiliza a configuração Xano existente no código; `XANO_API_BASE_URL` permite substituir a URL base pelo ambiente do processo. A equipe responsável deve confirmar a configuração ao preparar outra máquina. Não presuma que criar um `.env` fará suas variáveis serem carregadas automaticamente. Não coloque credenciais em comandos compartilhados, capturas ou arquivos versionados. Não é necessário configurar um provedor de e-mail para executar a recuperação demonstrativa.

### Funcionalidades condicionadas à configuração

| Funcionalidade | Padrão atual no código | Observação |
| --- | --- | --- |
| Gráfico real de movimentações | Habilitado | `NEXSTOCK_DASHBOARD_REAL_MOVEMENTS_ENABLED` |
| Notificações de solicitações | Habilitadas | `NEXSTOCK_PURCHASE_NOTIFICATIONS_ENABLED` |
| Recebimento vinculado a compras | Habilitado | `NEXSTOCK_PURCHASE_RECEIPTS_ENABLED` |
| Alteração voluntária da própria senha | Desabilitada | `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED`; possui limitações de segurança na seção 7. |
| Resumo ampliado de estoque insuficiente, incluindo saldo zero | Desabilitado | `NEXSTOCK_DASHBOARD_INSUFFICIENT_SUMMARY_ENABLED`; houve aceitação manual com ativação apenas no processo local. |

Definir explicitamente uma dessas flags como `false` substitui o padrão e desabilita a função. As flags são lidas ao carregar os módulos; mudanças no ambiente exigem reiniciar a aplicação. O inicializador normal não altera esses padrões. A presença de uma opção no código não comprova, por si só, a publicação de seu contrato no Xano.

## 3. Perfis de usuários

O sistema reconhece os perfis abaixo. **Grants** são as permissões efetivamente concedidas à conta, como consultar produtos ou registrar uma entrada. Elas são retornadas pelo Xano para a sessão de uso após a autenticação. O nome do perfil não deve ser interpretado como garantia de acesso a qualquer operação.

| Perfil | Responsabilidade | Acesso previsto na implementação |
| --- | --- | --- |
| **Líder** | Administração e acompanhamento geral. | A identidade administrativa permite gerir usuários, consultar e editar os perfis permitidos, acessar Auditoria e realizar as operações administrativas. O backend continua responsável por autorizar cada ação. |
| **Almoxarife** | Operação do estoque e acompanhamento da reposição. | Consulta e manutenção de cadastros, entradas, saídas, relatórios e solicitações conforme os grants atribuídos. Não recebe administração de usuários ou Auditoria apenas por ser operador. |
| **Auxiliar de almoxarifado** | Apoio e consulta às informações liberadas. | Acesso conforme os grants do perfil; operações de escrita só são disponibilizadas quando autorizadas. Não se deve presumir acesso a todas as consultas ou a todas as movimentações. |
| **Compras** | Acompanhamento e gestão das compras solicitadas. | Entra na área **Compras solicitadas**, com leitura, gestão e atualização de status previstas no provisionamento local. Não recebe permissão de entrada de estoque nem de cancelamento automaticamente. A navegação deste perfil é restrita à área de compras e à alteração voluntária de senha, quando habilitada. |

Na página **Perfis e permissões**, a edição implementada é dos grants de **Almoxarife** e **Auxiliar de almoxarifado**. Não há um fluxo geral de criação livre de novos perfis nessa página.

Regras importantes para as jornadas:

- Visualizar estoque, registrar entrada e registrar saída são permissões distintas.
- A página completa de Reposição exige acesso ao estoque e leitura de solicitações.
- Ler solicitações permite consultar as próprias; o acesso global depende também da permissão de gestão ou do acesso administrativo, conforme a autorização do backend.
- Criar, cancelar e atualizar status de solicitações são ações com permissões próprias. Ter leitura não concede essas ações.
- Receber uma compra exige permissão de entrada e acesso autorizado à solicitação. O perfil Compras não recebe produtos apenas por gerenciar os pedidos.
- Acesso por URL não substitui autorização. Se uma opção não aparecer ou for negada, solicite conferência do perfil ao Líder.

Essas são as regras da implementação local. A matriz completa de autorização no ambiente publicado ainda tem verificações pendentes, descritas na seção 7.

## 4. Funcionalidades

| Área | O que o usuário encontra | Rota |
| --- | --- | --- |
| Login | Acesso com conta existente e encaminhamento para a área permitida. | `/` |
| Dashboard / Painel | Produtos ativos, solicitações em andamento, indicador de estoque abaixo do mínimo, gráfico real de entradas e saídas e cinco movimentações recentes, conforme o acesso disponível. | `/dashboard` |
| Produtos | Pesquisa, cadastro, edição, unidade, estoque mínimo, categoria, fornecedor padrão e ativação/inativação autorizada. | `/produtos` |
| Categorias | Organização dos produtos e manutenção das categorias. | `/categorias` |
| Fornecedores | Cadastro e edição de nome/razão social, tipo de documento, documento e contato. | `/fornecedores` |
| Estoque | Consulta das quantidades e da situação dos produtos. | `/estoque` |
| Entradas | Entrada avulsa ou recebimento vinculado a uma solicitação elegível. | `/movimentacoes/entradas` |
| Saídas | Registro de retirada com validação de quantidade disponível. | `/movimentacoes/saidas` |
| Reposição de Estoque | Produtos que precisam de reposição e acompanhamento das compras já solicitadas. | `/reposicao` |
| Compras solicitadas | Listagem, detalhes, histórico e ações de status/cancelamento autorizadas. | `/compras` e `/compras/<id>` |
| Relatórios | Consulta de movimentações com filtros e exportação em PDF ou Excel. | `/relatorios` |
| Auditoria | Consulta administrativa de eventos e exportação em PDF. | `/auditoria` |
| Usuários | Cadastro, edição, perfil, situação e redefinição administrativa de senha. | `/usuarios` |
| Perfis e permissões | Consulta da matriz de permissões e edição dos perfis permitidos. | `/perfis` |
| Recuperação demonstrativa | Validação do formato de e-mail e confirmação visual, sem recuperação real. | `/recuperar-senha` |

O gráfico apresenta **duas séries de contagem de movimentações**, entradas e saídas, com períodos de **7 dias, 30 dias e 12 meses**. Ele não representa a soma de quantidades de produtos com unidades diferentes.

O sino disponibiliza notificações internas elegíveis de solicitações de compra, contador de não lidas, leitura individual e navegação ao pedido. A lista possui rolagem e carregamento incremental. O badge mostra `9+` a partir de dez não lidas; o painel mantém o total. Notificações internas não equivalem a envio de e-mail.

As telas distinguem carregamento, ausência de registros, falha e falta de acesso. Informações preservadas em cache podem ser sinalizadas como desatualizadas. Uma mensagem de erro não deve ser interpretada como quantidade zero.

## 5. Manual de utilização

### 5.1 Primeiro acesso — todos os perfis

1. Abra o endereço local informado pelo terminal e acesse a tela de login.
2. Informe as credenciais recebidas por canal privado e entre.
3. Se o sistema exigir a substituição da senha temporária, conclua a etapa apresentada em `/alterar-senha` e siga as instruções para entrar novamente.
4. Confira seu nome/perfil no cabeçalho e as opções disponíveis no menu. Compras é encaminhado para **Compras solicitadas**; os demais perfis são encaminhados para o Dashboard.
5. Utilize a opção de saída da conta ao terminar, especialmente em um computador compartilhado.

Se houver indisponibilidade ou limitação temporária de requisições, aguarde e utilize a ação de nova tentativa quando disponível. Não repita uma operação de escrita sem antes verificar se ela já foi registrada.

### 5.2 Preparar os cadastros — Líder ou operador autorizado

1. Em **Categorias**, use a ação de cadastro para organizar os materiais; confira a confirmação antes de continuar.
2. Em **Fornecedores**, abra o cadastro, informe nome/razão social, tipo e número do documento e contato conforme as validações do formulário. O endereço não é solicitado na interface atual.
3. Em **Produtos**, clique em **Novo produto**. Preencha código e nome, descrição quando necessária, categoria, fornecedor padrão, unidade e estoque mínimo.
4. Clique em **Salvar produto** e aguarde a confirmação. O cadastro do produto não substitui o registro de uma entrada para acrescentar quantidade ao estoque.
5. Para corrigir um cadastro, abra sua edição, revise os campos e salve. A situação e a ação de ativação/inativação aparecem conforme as permissões; utilize a confirmação solicitada.

### 5.3 Administrar usuários e acessos — Líder

1. Acesse **Usuários** e clique em **Novo usuário**.
2. Preencha nome, e-mail, perfil e a senha inicial conforme o formulário. Nome, e-mail e perfil devem começar sem dados de outro cadastro.
3. Confirme o cadastro e comunique as orientações de acesso por um canal privado, sem publicar a senha.
4. Na edição, use somente as ações necessárias, incluindo alteração de perfil, situação ou redefinição administrativa de senha quando autorizada.
5. Em **Perfis e permissões**, selecione um perfil editável, marque ou desmarque as descrições das permissões e salve. Os códigos técnicos são mantidos internamente.

Alterar permissões interfere no que as contas podem acessar. Não conceda acesso amplo apenas para tornar um botão visível.

### 5.4 Acompanhar estoque — Líder, Almoxarife ou Auxiliar autorizado

1. No **Painel**, confira os indicadores disponíveis e os avisos de atualização ou acesso.
2. Selecione **7 dias**, **30 dias** ou **12 meses** no gráfico e consulte as movimentações recentes.
3. Abra **Estoque** para localizar um produto e conferir quantidade, unidade e situação.
4. Para investigar movimentações de um período ou produto, utilize **Relatórios**.

Por padrão, o indicador do Dashboard é **Abaixo do mínimo**. O resumo ampliado **Estoque insuficiente**, que também inclui saldo zero, depende da configuração indicada na seção 2. A ausência de dados por erro não significa que não existam produtos a repor.

### 5.5 Solicitar reposição — operador autorizado

1. Abra **Reposição de Estoque** pela ação disponível no Dashboard ou pela rota `/reposicao`, se seu perfil permitir.
2. Consulte as listas de produtos que precisam de reposição e de compras já solicitadas.
3. No produto elegível, abra a solicitação e confira o produto e a unidade. Informe quantidade e urgência.
4. Confirme uma única vez e aguarde o resultado. Um produto com solicitação ativa não deve receber outro pedido ativo pelo mesmo fluxo.
5. Acompanhe a solicitação registrada. A confirmação de cadastro comprova o registro da solicitação, não o envio de uma mensagem de e-mail.

Para cancelar uma solicitação autorizada, abra **Cancelar solicitação**, informe o motivo obrigatório e confirme. Aguarde a confirmação efetiva. Cancelar um pedido não representa uma saída de estoque nem desfaz movimentações já registradas.

### 5.6 Acompanhar a compra — Compras ou gestor autorizado

1. Acesse **Compras solicitadas**, utilize os filtros disponíveis e abra os detalhes do pedido.
2. Confira produto, quantidade, situação e histórico. Leitores sem escopo global só podem acessar solicitações próprias autorizadas.
3. Quando permitido, selecione a próxima situação e confirme. O fluxo previsto é **Aberta → Em análise → Aprovada → Em compra → Aguardando recebimento**.
4. Uma solicitação em análise pode ser rejeitada pela ação autorizada, com a justificativa exigida. Cancelamento é uma ação separada, sujeita à permissão e ao estado do pedido.
5. Use **Voltar** para retornar à listagem. Não tente concluir manualmente um recebimento pelo seletor de status: a conclusão decorre das entradas vinculadas.

### 5.7 Registrar uma entrada — Almoxarife ou outro usuário autorizado

1. Abra **Entradas** e localize o produto pelo código, leitura de código de barras ou busca disponível.
2. Escolha **entrada avulsa** para uma entrada sem vínculo com pedido, ou selecione uma solicitação de compra elegível.
3. Para recebimento vinculado, confira o produto, a unidade, a quantidade solicitada, o que já foi recebido e o restante. São elegíveis pedidos em **Aguardando recebimento** ou **Recebimento parcial**, dentro do escopo autorizado.
4. Informe a quantidade desta entrada e os demais campos apresentados, como fornecedor, data/hora, motivo e observação. Não exceda o saldo pendente nem utilize um produto diferente do pedido.
5. Confirme uma única vez. Aguarde o modal de sucesso e confira as informações apresentadas; o saldo final só deve ser mostrado quando confirmado pelo servidor.
6. Consulte o estoque e o pedido: recebimento menor que o total mantém **Recebimento parcial**; completar a quantidade solicitada leva a **Concluída**. O mesmo fluxo atualiza estoque e recebimento; não registre outra entrada avulsa para a mesma entrega.

A entrada avulsa continua disponível e não altera automaticamente uma solicitação de compra. Pedidos antigos sem unidade histórica confirmada podem não ser elegíveis ao vínculo; solicite conferência ao responsável antes de registrar a entrega por outro caminho.

### 5.8 Registrar uma saída — operador com permissão

1. Abra **Saídas**, identifique o produto pelo código ou busca e confira a quantidade disponível.
2. Informe quantidade, data/hora, motivo e observação conforme o formulário.
3. Confirme e aguarde o resultado. A operação deve rejeitar quantidade superior ao disponível.
4. Feche o modal de sucesso e confira o estoque ou o relatório de movimentações. Não presuma um saldo que não tenha sido confirmado.

### 5.9 Consultar relatórios e auditoria

**Relatórios — usuários com acesso à função:**

1. Abra **Relatórios** e selecione período, tipo de movimentação, produto e fornecedor conforme necessário.
2. Clique em **Aplicar filtros** e confira os registros e a paginação.
3. Utilize **Exportar PDF** ou **Exportar Excel** após carregar resultados válidos. Alterações nos filtros devem ser aplicadas antes de exportar; dados desatualizados ou com erro podem bloquear a exportação.

**Auditoria — Líder com acesso administrativo:**

1. Abra **Auditoria** e utilize os filtros de datas, ID do usuário, ação e entidade.
2. Clique em **Aplicar filtros**. Leia data/hora, usuário, ação, entidade, registro, resumo e alterações.
3. Valores pessoais omitidos não podem ser recuperados pelo relatório. Quando faltam detalhes no evento, a interface informa essa ausência sem inventar valores.
4. Clique em **Exportar PDF** para exportar os eventos autorizados que atendem aos filtros, incluindo as demais páginas.
5. O limite é **500 eventos**. Se a consulta exceder esse limite, refine os filtros: o sistema informa o excesso e **não gera um PDF parcial**.

A Auditoria atual cobre produtos, categorias, fornecedores, usuários, perfis, permissões e os eventos administrativos de credenciais previstos no contrato. Entradas, saídas, solicitações de compra e e-mails não fazem parte dessa página. Consulte movimentações em **Relatórios** e o histórico de cada compra em seus detalhes.

### 5.10 Notificações e senha

**Notificações:** clique no sino, role a lista ou use **Carregar mais**. Clique em uma notificação para abrir a solicitação correspondente; uma notificação não lida tenta registrar a leitura antes de navegar. Use **Marcar como lida** para registrar a leitura sem abrir o pedido. O contador só muda após a confirmação do servidor. Se a leitura falhar, o estado não lido é preservado e a navegação autorizada pode continuar.

**Alteração voluntária de senha:** quando habilitada em um ambiente autorizado, a opção **Alterar senha** fica no menu da conta e abre `/conta/alterar-senha`. Informe senha atual, nova senha e confirmação; após sucesso, a sessão local é encerrada e é necessário entrar novamente. A função permanece desabilitada por padrão e não revoga os tokens de outras sessões.

**Esqueceu sua senha?:** no login, o link abre `/recuperar-senha`. Informe um e-mail em formato válido, clique em **Solicitar recuperação** e depois em **Entendi** para voltar ao login. **Este fluxo é exclusivamente demonstrativo:** não consulta contas, não envia e-mail, não gera tokens, não armazena a solicitação e não redefine senhas. O texto do modal não comprova um envio real. Para recuperar acesso de verdade nesta versão, procure o Líder responsável pela redefinição administrativa.

### Capturas úteis para a apresentação

Nenhuma imagem é presumida ou incorporada por este README. Para ilustrar o manual, a equipe pode produzir capturas autorizadas de:

- Dashboard com os indicadores e os três seletores do gráfico.
- Cadastro de produto e consulta de estoque.
- Reposição, detalhes de uma solicitação e recebimento parcial/concluído.
- Filtros de Relatórios e PDF da Auditoria.
- Menu de um operador e menu de Compras, demonstrando a diferença de acesso.
- Recuperação de senha, com legenda explícita de que se trata de demonstração.

Use dados de demonstração autorizados e oculte nomes pessoais, e-mails, documentos, contatos, credenciais e qualquer conteúdo sensível. As capturas ainda precisam ser selecionadas pela equipe; não são evidências anexadas a este documento.

## 6. Exemplos de utilização

Os cenários abaixo são **inteiramente ilustrativos**. A empresa, os produtos, as quantidades e os resultados não representam registros existentes nem testes executados no Xano. Não crie esses registros em um ambiente real apenas para reproduzir o texto.

### Cenário: almoxarifado da empresa fictícia Horizonte

1. **Cadastro:** o Líder cadastra a categoria Materiais de escritório, um fornecedor fictício e o produto Papel A4, código `DEMO-A4`, unidade `CX` e mínimo de 10 caixas.
2. **Entrada inicial:** um operador autorizado registra uma entrada avulsa de 12 caixas. Nesse exemplo, o produto fica com saldo de 12 caixas.
3. **Consumo:** uma saída autorizada de 8 caixas deixa 4 caixas disponíveis. O produto passa a estar abaixo do mínimo.
4. **Reposição:** o operador autorizado solicita 8 caixas pela página de Reposição. A equipe de Compras acompanha a análise, a aprovação e a aquisição até **Aguardando recebimento**.
5. **Recebimento parcial:** chegam 3 caixas. O Almoxarife registra uma entrada vinculada de 3 caixas; o pedido passa a **Recebimento parcial**, com 5 caixas ainda pendentes. Sem outras movimentações, o saldo ilustrativo seria de 7 caixas.
6. **Conclusão:** chegam as 5 caixas restantes. Uma segunda entrada vinculada completa as 8 caixas solicitadas, e o pedido fica **Concluído**. Sem outras movimentações, o saldo ilustrativo seria de 12 caixas.
7. **Acompanhamento:** a equipe consulta o gráfico e os relatórios de entradas/saídas; o Líder consulta na Auditoria os eventos administrativos de cadastro, sem esperar encontrar ali os recebimentos.

Os saldos acima são cálculos explicativos do exemplo. No aplicativo, confira sempre o saldo confirmado pelo servidor. A unidade da solicitação deve ser preservada; não há conversão automática de caixas em unidades.

### Cenário: consulta sem permissão de escrita

Um Auxiliar com grants de consulta acompanha o estoque e os relatórios liberados. Ao identificar falta de material, comunica o operador responsável. Não pode registrar entrada, saída ou solicitação apenas porque consegue visualizar o produto. Se receber uma permissão adicional, ela deverá ser concedida pela administração e reconhecida na sessão.

## 7. Limitações conhecidas

### Restrições que afetam o uso

- **Recuperação de senha:** somente demonstração visual, sem envio ou redefinição real, mesmo que o modal utilize uma mensagem semelhante à de um fluxo real.
- **Alteração voluntária de senha:** implementação e teste funcional com conta dedicada relatados pelo usuário, mas desabilitada por padrão. Sair da conta neste navegador não invalida os comprovantes digitais de acesso (tokens JWT) já emitidos em outras sessões. Essa invalidação, chamada de revogação remota, não está implementada. A proteção abrangente de logs (registros técnicos) e debugger (ferramenta de inspeção da execução) também não está comprovada.
- **Indicador ampliado de estoque insuficiente:** foi aceito manualmente com a flag habilitada somente no processo local; o padrão continua desabilitado. Isso não desabilita a consulta de estoque nem o indicador anterior de produtos abaixo do mínimo.
- **E-mails de compras:** registrar ou cancelar uma compra não comprova envio de e-mail. Há código de integração e uma outbox (registro das intenções de envio), mas a entrega automática completa não está comprovada. Publicação seletiva, configuração dos provedores Resend/Brevo, restrições de destinatário/IP, entrega e conferência dos resultados ainda têm pendências. Não há execução automática comprovada do dispatcher, a rotina responsável por processar essas intenções.
- **Acesso público:** não há link de deploy confirmado neste manual. A execução local depende de uma conta e dos serviços Xano disponíveis.

Também podem ocorrer falhas temporárias de conexão ou limitação de requisições, tanto no serviço remoto quanto no controle local de chamadas. Nesses casos, observe os avisos de indisponibilidade ou dados desatualizados, em vez de interpretar um erro como ausência de registros.

O projeto não inclui controle financeiro, emissão de notas fiscais ou recuperação real de senha por e-mail.

### Funcionalidades existentes com verificações técnicas pendentes

As seis changes abaixo são os conjuntos de requisitos e tarefas acompanhados no OpenSpec e permanecem ativas. Uma pendência de comprovação **não significa uma falha funcional confirmada**. Da mesma forma, testes locais com mocks (respostas simuladas) ou inspeção de XanoScript não comprovam o comportamento do ambiente publicado.

Para interpretar as pendências:

- **Rollback:** desfazer as alterações de uma operação quando uma etapa falha, evitando, por exemplo, atualizar o estoque sem registrar a movimentação correspondente.
- **Idempotência:** repetir a mesma solicitação identificada sem gerar uma segunda operação, como uma entrada duplicada após uma falha de conexão.
- **Concorrência:** duas ou mais operações acontecendo ao mesmo tempo. Testar cada uma separadamente não comprova como elas se comportam juntas.
- **Índice único com valores nulos:** regra do banco que impede valores repetidos em um campo; ainda é necessário verificar como ela trata registros em que esse campo está sem valor.
- **Isolamento e guards:** isolamento é manter os dados de cada usuário dentro do acesso permitido; guards são verificações de acesso na aplicação e não substituem a autorização do Xano.
- **Invariantes, helper e QA:** invariantes são regras que devem continuar verdadeiras, como a consistência entre saldo e movimentações; helper é uma função auxiliar; QA é a verificação de qualidade, incluindo a inspeção visual.

| Change e registro de referência | Evidência disponível | Limitação relevante |
| --- | --- | --- |
| [recebimento-compras-estoque](openspec/changes/recebimento-compras-estoque/publicacao-controlada.md) | Implementação local, testes documentados, previews e recebimentos parcial/total relatados pelo usuário. | Comparação remota integral, comportamento de índices únicos com valores nulos, rollback, concorrência e matriz de testes em ambiente seguro não estão integralmente comprovados. |
| [auditoria-sistema](openspec/changes/auditoria-sistema/design.md) | Interface, contratos e verificações locais de transação; uso da tela relatado pelo usuário. | Rollback real e evidências suficientes de publicação seletiva e consultas autorizadas/negadas permanecem pendentes. Não há falha de rollback confirmada. |
| [dashboard-reposicao-compras](openspec/changes/dashboard-reposicao-compras/design.md) | Indicador aceito manualmente com flag local e relatos de criação, cancelamento e recebimento. | Faltam evidências completas de todas as combinações visuais/de acesso, rejeição e invariantes, além dos cenários de integração com destinatário de e-mail. |
| [perfil-compras-solicitacoes](openspec/changes/perfil-compras-solicitacoes/design.md) | Perfil, guards, contratos de status e testes locais documentados. | Matriz remota de grants, isolamento, paginação, transições, estado desatualizado, publicação do helper de escopo global e associação autorizada de conta de teste não estão totalmente comprovadas. |
| [backend-solicitacoes-compras](openspec/changes/backend-solicitacoes-compras/design.md) | Código local de criação, histórico, status, cancelamento, recebimento e outbox; relatos de uso parcial. | Permanecem critérios de índices no Xano Free, idempotência sob concorrência, rollback, permissões publicadas e entrega externa de e-mail. Não há garantia comprovada de entrega exatamente uma vez. |
| [dashboard-funcional](openspec/changes/dashboard-funcional/design.md) | Testes locais documentados e aceitação manual informada do gráfico, notificações, navegação e senha; aceitação visual de Dashboard desktop/móvel. | Faltam a matriz remota integral de autorização/isolamento/paginação, verificações específicas de datas e séries, proteção abrangente de logs e QA detalhado da central em todas as larguras previstas. Revogação de JWT continua ausente. |

A aceitação manual informada pelo usuário em 16/11/2026 inclui o Dashboard autenticado em **1920 × 960**, além de conferência visual desktop e móvel dos grupos aprovados. Não foram anexados a este README capturas, medições ou logs independentes; a dimensão móvel efetivamente utilizada não foi confirmada. Essa aceitação não substitui os testes técnicos pendentes.

Neste ciclo, as limitações foram registradas sem executar novas tentativas remotas para preenchê-las. Qualquer comprovação futura de escrita, concorrência ou rollback exige ambiente seguro e autorização específica.

Para consultar os contratos consolidados, veja [openspec/specs](openspec/specs/). As decisões e os critérios ainda abertos permanecem nas changes indicadas acima.
