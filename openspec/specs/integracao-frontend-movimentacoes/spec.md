# integracao-frontend-movimentacoes Specification

## Purpose
TBD - created by archiving change integracao-frontend-movimentacoes. Update Purpose after archive.

## Requirements

### Requirement: O código da Entrada resolve o Produto ao pressionar Enter

O campo de código MUST aceitar digitação manual e teclado de leitor. Digitar MUST NOT abrir o combobox de Produto nem emitir chamadas por caractere. Ao pressionar Enter, a tela MUST procurar correspondência exata do código, ignorando caixa, na lista carregada e nas páginas restantes quando necessário. Ao encontrar, MUST selecionar o `product_id` real, preencher o campo Produto e o código canônico, sugerir Fornecedor padrão ativo quando houver e fechar ambos os popovers. Sem correspondência, MUST manter o texto digitado, limpar Produto e Fornecedor derivados e mostrar `Produto não encontrado.`

#### Scenario: Resolver pelo código
- **WHEN** usuário digita ou lê um código e pressiona Enter
- **THEN** Produto é selecionado pelo ID real, o campo Produto e o código canônico são preenchidos e o Fornecedor padrão ativo é sugerido

#### Scenario: Código sem correspondência
- **WHEN** o código não existe nas páginas consultadas
- **THEN** o texto digitado permanece, Produto e Fornecedor são limpos e a tela mostra `Produto não encontrado.`

### Requirement: Seletor pesquisável fecha como popover sem bloquear seleção

Cada searchable_select MUST abrir ao receber foco ou clique, fechar ao selecionar, ao perder foco para fora ou ao pressionar Escape. No máximo um seletor deve permanecer aberto por formulário. O painel MUST sobrepor o conteúdo sem empurrar os campos, manter largura alinhada ao controle, limite de altura e rolagem vertical. O fechamento por blur MUST permitir que o clique numa opção seja processado.

#### Scenario: Alternar entre seletores
- **WHEN** um seletor está aberto e usuário foca outro seletor
- **THEN** o primeiro fecha e apenas o segundo permanece aberto

#### Scenario: Fechar popover
- **WHEN** usuário seleciona uma opção, clica fora ou pressiona Escape
- **THEN** o popover fecha sem impedir a seleção escolhida

### Requirement: Entrada deve selecionar Produtos reais por busca

A tela `/movimentacoes/entradas` MUST carregar Produtos autenticados pelo Xano e permitir seleção por combobox pesquisável, exibindo código e nome amigáveis e mantendo `product_id` real no State. A busca MUST ser parcial, case-insensitive e accent-insensitive. A interface MUST usar paginação limitada, com carregamento inicial de até 100 registros e ação explícita para carregar outras páginas; digitar MUST NOT emitir requisição de listagem por caractere.

#### Scenario: Pesquisar Produto manualmente
- **WHEN** usuário digita trecho de código ou nome do Produto
- **THEN** opções carregadas correspondentes são filtradas parcialmente sem diferenciar caixa ou acentos, e selecionar uma opção guarda o ID Xano

#### Scenario: Carregar mais Produtos
- **WHEN** o Produto desejado não está entre as opções carregadas e existem outras páginas
- **THEN** usuário pode solicitar a página seguinte sem carregar o catálogo inteiro automaticamente

### Requirement: Leitura de código seleciona o Produto da Entrada

A tela MUST aceitar o código como entrada de teclado e MUST procurar o Produto quando o usuário/leitor concluir a leitura com Enter. Ao encontrar código igual, MUST selecionar o `product_id` e exibir código e nome. Se não encontrar, MUST mostrar `Produto não encontrado.`, limpar a seleção válida e impedir a tentativa de registro da Entrada. A procura MUST usar o endpoint e paginação existentes, sem criar endpoint nesta change.

#### Scenario: Leitura bem-sucedida
- **WHEN** usuário/leitor informa um código existente e pressiona Enter
- **THEN** Produto correspondente é selecionado e código/nome são apresentados

#### Scenario: Leitura sem correspondência
- **WHEN** código não corresponde a Produto existente após consultar páginas disponíveis
- **THEN** interface mostra `Produto não encontrado.` e nenhum `product_id` permanece selecionado

### Requirement: Fornecedor da Entrada usa seleção pesquisável e padrão do Produto

A Entrada MUST oferecer seleção pesquisável de Fornecedor por nome, com busca parcial, case-insensitive e accent-insensitive, exibindo nome amigável e mantendo o ID real. A lista MUST ser carregada em páginas limitadas com carregamento explícito. Ao selecionar Produto com Fornecedor padrão ativo, o State MUST preencher essa referência quando disponível; sem padrão, o campo permanece opcional/vazio. A seleção deve permitir substituir por outro Fornecedor ativo ou limpar. Se o fornecedor padrão existente estiver inativo, o State não deve enviá-lo automaticamente; o Xano valida a existência e o status do fornecedor recebido.

#### Scenario: Preencher Fornecedor padrão
- **WHEN** Produto selecionado possui `fornecedor_padrao_id`
- **THEN** Fornecedor correspondente é mostrado como seleção inicial, permitindo que usuário escolha outro fornecedor disponível

#### Scenario: Produto sem Fornecedor padrão
- **WHEN** Produto selecionado não possui Fornecedor padrão
- **THEN** Fornecedor permanece opcional e sem ID inventado

### Requirement: Data/hora da Entrada usa o contrato real do backend

A tela MUST apresentar data/hora opcional. Quando vazia, Reflex MUST omitir data_hora e o backend MUST atribuir a hora de conclusão. Quando informada, Reflex MUST encaminhar o valor de datetime-local sem criar fuso horário nem preencher data artificialmente.

#### Scenario: Data/hora omitida
- **WHEN** usuário deixa o campo de data/hora vazio
- **THEN** o payload MUST omitir data_hora para o Xano usar o horário do servidor

#### Scenario: Data/hora informada
- **WHEN** usuário informa data e hora
- **THEN** Reflex MUST enviar o valor escolhido sem ajuste de fuso arbitrário

### Requirement: Reflex MUST registrar Entrada usando o endpoint real do Xano

O botão Registrar entrada MUST chamar POST /api:estoque/entries com Bearer da sessão. O payload MUST conter o ID real do Produto, quantidade maior que zero e motivo trimado e não vazio. supplier_id, data_hora e observacao MUST ser omitidos quando vazios; supplier_id MUST NOT ser enviado como 0; user_id MUST NOT ser enviado. O backend permanece autoridade para autenticação, permissão e validações.

#### Scenario: Entrada válida
- **WHEN** usuário envia Produto selecionado, quantidade positiva e motivo preenchido
- **THEN** o client MUST enviar o payload do contrato ao endpoint POST /api:estoque/entries

#### Scenario: Quantidade ou motivo ausente
- **WHEN** quantidade não é numérica/positiva ou motivo fica vazio após trim
- **THEN** Reflex MUST impedir a chamada e mostrar mensagem de validação

#### Scenario: Fornecedor opcional ausente
- **WHEN** usuário escolhe Sem fornecedor ou não seleciona fornecedor
- **THEN** o payload MUST omitir supplier_id e MUST NOT enviar zero

#### Scenario: Usuário autenticado
- **WHEN** Reflex envia a Entrada
- **THEN** o payload MUST NOT conter user_id; o backend associa $auth.id

### Requirement: Envio da Entrada MUST proteger o formulário e apresentar resultado seguro

Enquanto a requisição estiver em andamento, o botão MUST ficar desabilitado e mostrar estado de envio, e uma segunda submissão MUST ser ignorada. Em sucesso, a interface MUST mostrar confirmação e saldo_atual retornado, limpar os campos da operação e refletir os saldos reais quando a lista de Produtos for carregada novamente. Falha MUST preservar os campos e mostrar mensagem amigável. Erro 401 MUST seguir o fluxo existente de sessão; 403 e códigos de validação MUST ser distinguidos; erros desconhecidos MUST usar mensagem genérica sem traceback.

#### Scenario: POST confirmado
- **WHEN** Xano retorna sucesso para a Entrada
- **THEN** interface MUST mostrar sucesso e o saldo retornado, limpar os campos e não exigir F5 para recarregar Produtos

#### Scenario: POST rejeitado
- **WHEN** Xano retorna erro funcional, de permissão ou conexão
- **THEN** interface MUST permanecer na tela, preservar os campos e mostrar mensagem adequada

### Requirement: Padrão de busca deve ser reutilizado em relacionamentos e movimentações

O seletor pesquisável compartilhado MUST ser usado para Categoria e Fornecedor padrão de Produto e para Produto e Fornecedor de Entrada, além do Produto na tela de Saída. A Saída não inclui Fornecedor, pois essa operação não possui essa regra de domínio.

#### Scenario: Reutilizar busca de Produto na Saída
- **WHEN** usuário busca manualmente ou lê o código de um Produto
- **THEN** a tela reutiliza o helper de combobox e o padrão de leitura por código, sem adicionar Fornecedor

### Requirement: Saída deve registrar movimentação pelo endpoint real

A tela /movimentacoes/saidas MUST carregar Produtos e saldos autenticados do Xano, permitir busca manual pesquisável e leitura de código por Enter, e exibir o saldo disponível real. A busca manual MUST ser parcial, case-insensitive e accent-insensitive; a leitura MUST procurar código exato, sem chamadas por caractere e com paginação sob demanda. Ambas MUST manter o ID real do Produto.

O registro MUST chamar POST /api:estoque/exits com product_id, quantidade positiva e finita, e motivo trimado não vazio. data_hora e observacao MUST ser omitidos quando vazios. user_id e supplier_id MUST NOT ser enviados. O backend permanece autoridade para autorização e integridade do saldo.

A interface MUST bloquear Saída sem saldo, com saldo zero ou com quantidade maior que saldo_disponivel; a resposta INSUFFICIENT_STOCK MUST receber mensagem amigável. Data/hora informada MUST ser encaminhada sem conversão arbitrária de fuso. Envio duplicado MUST ser bloqueado. Em sucesso, a tela MUST exibir saldo_atual retornado e limpar os campos, atualizando o saldo local para seleções posteriores. Erros MUST preservar os campos; 401 MUST seguir o fluxo existente de sessão, 403 MUST informar falta de permissão e erros desconhecidos MUST usar mensagem genérica.

#### Scenario: Saída válida

- WHEN usuário seleciona um Produto com saldo positivo, informa quantidade válida até o saldo e motivo
- THEN Reflex envia o payload de Saída ao Xano sem user_id ou supplier_id e exibe confirmação com o saldo retornado

#### Scenario: Código resolve Produto e saldo

- WHEN usuário ou leitor informa um código e pressiona Enter
- THEN a tela seleciona o Produto pelo ID real e apresenta seu saldo disponível carregado pelo GET /stock

#### Scenario: Produto sem saldo ou saldo insuficiente

- WHEN Produto não tem registro de saldo, tem saldo zero ou a quantidade excede o saldo
- THEN a interface bloqueia o POST e apresenta mensagem correspondente; se o backend responder INSUFFICIENT_STOCK, a tela apresenta erro amigável

#### Scenario: Datas opcionais

- WHEN data/hora é deixada vazia
- THEN data_hora é omitida para o backend preencher o horário

- WHEN data/hora é informada
- THEN Reflex encaminha o valor escolhido sem ajuste de fuso arbitrário

### Requirement: Histórico deve consultar movimentações reais do backend

A rota /movimentacoes MUST validar a sessão pelo fluxo AuthState existente e carregar movimentos pela chamada autenticada GET /api:estoque/movements. O client MUST enviar page e per_page=20 e incluir tipo e product_id somente quando seus filtros estiverem selecionados. Os filtros MUST ser combináveis, reiniciar a consulta na página 1 quando alterados e provocar nova consulta ao backend. A tela MUST preservar filtros ao mudar de página.

O Histórico MUST exibir Data/Hora, Tipo, Código, Produto, Quantidade, Usuário, Fornecedor, Motivo e Observação usando os campos enriquecidos que o endpoint retorna. MUST NOT fazer chamadas por linha para obter Produto, Usuário ou Fornecedor. MUST preservar a ordenação recebida do backend. Tipo entrada/saida MUST ser apresentado como Entrada/Saída sem alterar o valor original armazenado. Timestamp epoch em milissegundos MUST ser apresentado em formato pt-BR legível e não como número bruto. Quantidade MUST manter seu sinal e precisão, aplicando vírgula como separador decimal quando necessário.

O filtro por tipo MUST oferecer Todos, Entrada e Saída, mapeando Todos para omissão e as demais opções para entrada/saida. O filtro por Produto MUST armazenar o ID real, exibir código e nome e usar busca local case-insensitive/accent-insensitive nas opções carregadas; digitar MUST NOT consultar o Xano por caractere. O Produto selecionado MUST ser enviado como product_id.

A página MUST usar paginação real e exibir controles Anterior/Próxima desabilitados nos limites. Enquanto carrega, MUST mostrar indicador e evitar mostrar a página anterior como resultado do filtro novo. Sem itens, MUST mostrar mensagem de estado vazio. Produto ou Usuário sem nome e Fornecedor/Observação nulos MUST receber fallbacks legíveis, sem exibir None/null.

Erros 401 MUST seguir o fluxo de sessão/login; HTTP 403 ou PERMISSION_DENIED MUST informar falta de permissão para visualizar o histórico; INVALID_INPUT MUST indicar filtros inválidos; erros de conexão ou desconhecidos MUST exibir mensagem amigável sem traceback. A tela é somente de leitura e MUST NOT alterar Entrada, Saída ou backend.

#### Scenario: Abrir ou retornar ao Histórico

- **WHEN** usuário autenticado abre /movimentacoes
- **THEN** a aplicação valida a sessão e consulta a página atual com os filtros preservados, incluindo movimentos gravados desde a visita anterior

#### Scenario: Combinar filtros de tipo e Produto

- **WHEN** usuário escolhe Saída e um Produto
- **THEN** a tela consulta a página 1 de GET /movements com tipo=saida e o product_id real selecionado

#### Scenario: Paginar com filtros ativos

- **WHEN** usuário avança ou retorna uma página
- **THEN** o frontend envia a página indicada pelo backend e mantém tipo e product_id

#### Scenario: Buscar Produto para o filtro

- **WHEN** usuário digita trecho de código ou nome no seletor de Produto
- **THEN** as opções carregadas são filtradas localmente sem chamada ao Xano por caractere

#### Scenario: Mostrar carregamento e estado vazio

- **WHEN** a página está sendo consultada ou não contém movimentações
- **THEN** a tela mostra indicador de carregamento ou mensagem de histórico vazio, respectivamente

### Requirement: Histórico deve filtrar por usuário e alinhar suas colunas

A área de filtros MUST ser agrupada sob o rótulo Filtros e conter Tipo, Usuário, Produto e Limpar filtros, quebrando em telas estreitas. O seletor de Usuário MUST usar a listagem paginada segura do backend, exibir o nome e armazenar o ID. Ao selecionar usuário, o frontend MUST reiniciar na página 1 e enviar `user_id`, combinado com os demais filtros selecionados. Limpar filtros MUST limpar tipo, usuário e Produto e recarregar a primeira página sem filtros.

O cabeçalho e cada linha da tabela MUST usar a mesma estrutura de colunas e larguras para manter alinhamento. Quantidade MUST ocupar coluna própria de largura mínima suficiente e Usuário MUST começar na coluna seguinte, sem encostar ou concatenar visualmente. Tipo MUST ser centralizado, Quantidade alinhada à direita e as demais colunas à esquerda. Overflow horizontal MUST ser usado quando necessário em telas menores.

#### Scenario: Filtrar histórico por usuário

- **WHEN** o usuário seleciona uma pessoa e mantém outros filtros ativos
- **THEN** a página 1 é recarregada com `user_id` combinado a tipo e/ou `product_id`

#### Scenario: Limpar todos os filtros

- **WHEN** o usuário ativa Limpar filtros
- **THEN** tipo, usuário e Produto voltam ao padrão e todas as movimentações são recarregadas desde a página 1
