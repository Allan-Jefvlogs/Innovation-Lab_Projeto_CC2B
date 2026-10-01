# Design: Preparação da Entrada no Reflex

## Seletores relacionais reutilizáveis

`Meu_projeto/components/searchable_select.py` fornece o componente comum para opções com `id`, `label` e `disabled`. O filtro usa substring após `casefold` e remoção de diacríticos, preservando o texto original e o ID como valor. Produtos e Fornecedores carregam inicialmente uma página de até 100 registros e oferecem carregamento explícito das páginas seguintes. Não há requisição ao Xano por caractere digitado.

Os formulários de Produto reutilizam o mesmo componente para Categoria e Fornecedor padrão. A Entrada o reutiliza para Produto (rótulo `código - nome`) e Fornecedor (nome amigável). A procura manual filtra as páginas já carregadas; o usuário pode carregar mais opções.

## Identificação de Produto

`EntryState` carrega a primeira página de `GET /products` e `GET /suppliers?status=ativo` com o Bearer da sessão. A seleção mantém `product_id`, código e nome separados. Um campo de leitura aceita teclado e, ao receber Enter, procura o código exato entre os Produtos carregados e continua paginação de `GET /products` até encontrar o código ou chegar ao fim. Como não existe endpoint local de busca por código, uma leitura pode exigir várias chamadas paginadas; a lista inteira não é carregada antecipadamente para o combobox.

Produto não encontrado limpa a seleção técnica e mostra `Produto não encontrado.`. O envio valida a presença de um `product_id` válido antes de chamar o endpoint.

## Fornecedor da Entrada

Ao selecionar Produto, o State lê seu `fornecedor_padrao_id`. Se houver valor, consulta-o na lista carregada ou por `GET /suppliers/by_id/{supplier_id}` e preenche a seleção de Fornecedor. Se não houver Fornecedor padrão, deixa a escolha vazia. O usuário pode limpar a escolha ou selecionar outro Fornecedor ativo. Uma referência padrão inativa não é enviada automaticamente; o usuário pode deixar a Entrada sem Fornecedor ou escolher um ativo, enquanto o backend valida qualquer ID recebido.

## Data e hora

A tela apresenta um campo `datetime-local` vazio e opcional, armazenado sem preenchimento artificial no frontend. Se informado, o State mantém e envia o valor ISO recebido pelo controle, aceito pelo input `timestamp` do endpoint. Se vazio, o campo é omitido e o backend usa `now` na execução da entrada.

## Integração transacional de Entrada

EntryState envia uma entrada autenticada por XanoClient.create_stock_entry, que usa POST /api:estoque/entries. O payload inclui product_id, quantidade e motivo; inclui supplier_id, data_hora e observacao somente quando preenchidos. O ID real do Produto e do Fornecedor é usado; código de Produto e user_id nunca são enviados.

O State valida Produto selecionado, quantidade decimal finita maior que zero e motivo não vazio. O backend segue como autoridade para permissão e validações de domínio. datetime-local é encaminhado sem preenchimento artificial ou ajuste de fuso; vazio é omitido para o backend usar now. Fornecedor vazio é omitido, nunca enviado como 0. Fornecedor padrão inativo não é enviado automaticamente.

Durante a requisição, o botão fica desabilitado e mostra Registrando...; o handler também bloqueia submissões repetidas. Sucesso exibe o saldo retornado pelo Xano e limpa a operação. Ao navegar para /produtos, o on_load existente executa novamente ProductsState.load_products, que consulta os saldos atuais no Xano.

Erros funcionais são mapeados pelos códigos retornados pelo Xano; 401 segue o fluxo existente de sessão/login e 403 mostra mensagem de permissão. Respostas desconhecidas exibem texto genérico sem detalhes internos. A Saída possui um fluxo de gravação independente descrito nesta mudança; EntryState permanece específico da Entrada.

## Refinamento de seleção e popovers

O campo de código não abre o combobox nem consulta a cada tecla. Ao pressionar Enter, EntryState procura o código exato, sem diferenciar caixa, primeiro nos Produtos carregados e depois nas páginas restantes sob demanda. Uma correspondência seleciona o ID real, atualiza o código canônico e o campo Produto e sugere o fornecedor padrão. A seleção manual do Produto mantém o caminho inverso e preenche o código.

Os searchable_select usam popover absoluto sobre o formulário, com z-index elevado e altura rolável limitada. O blur fecha com debounce curto para permitir que o clique numa opção seja processado antes do fechamento; Escape também fecha. Os handlers de abertura/consulta fecham o seletor relacionado que estava aberto. O mesmo comportamento é aplicado aos seletores de Categoria e Fornecedor nos formulários de Produto.

## Integração transacional de Saída

ExitState mantém seleção, código de barras, quantidade, data/hora, motivo, observação e saldo em estado separado de EntryState. A tela reutiliza searchable_select para busca parcial por código/nome sem diferenciar caixa ou acentos; ao pressionar Enter, procura código exato nas páginas já carregadas e carrega as seguintes sob demanda. Seleção manual e por código guardam o ID real do Produto e consultam o saldo já carregado via GET /stock.

A Saída chama XanoClient.create_stock_exit, que envia POST /api:estoque/exits com product_id, quantidade e motivo trimado. data_hora e observacao só são incluídos quando preenchidos. user_id não é enviado, pois o backend usa $auth.id; supplier_id não faz parte da requisição.

O State aceita quantidade decimal finita maior que zero, exige Produto com saldo carregado e bloqueia envio quando saldo é zero ou quantidade supera saldo_disponivel. O backend continua autoridade final; INSUFFICIENT_STOCK e os demais códigos funcionais têm mensagens específicas. Data/hora vazia é omitida para o backend preencher o horário; o valor informado é encaminhado sem ajuste de fuso.

Durante o POST, is_submitting bloqueia repetição e o botão mostra Registrando.... Sucesso mostra saldo_atual retornado pelo backend, atualiza o cache local de saldos da tela e limpa a operação. Erros preservam os campos; 401 segue o fluxo existente de sessão e 403 informa falta de permissão. A Entrada mantém seu State e seu payload próprios.