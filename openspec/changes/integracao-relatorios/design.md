# Design: Relatórios operacionais

## Fluxo da tela

`ReportState.load_page` exige a sessão existente e carrega opções paginadas de Produtos e Fornecedores, a primeira página de movimentos e os resumos de movimentos e estoque. Datas começam vazias: sem período informado, o relatório consulta o conjunto geral disponível. Aplicar ou limpar filtros retorna a tabela à página 1. Navegar páginas preserva os filtros.

O tipo filtra somente a tabela detalhada para que os cards continuem mostrando entradas e saídas simultaneamente. Produto, Fornecedor e datas são aplicados tanto à tabela como aos totais de movimentos. Fornecedor filtra movimentos vinculados ao `supplier_id`; saídas normalmente não possuem Fornecedor.

## Contratos Xano

`GET /movements` conserva autenticação, `stock.read`, joins, campos e paginação atuais, acrescentando `timestamp? date_from?`, `timestamp? date_to?` e `int? supplier_id?`. IDs opcionais são anuláveis e positivos quando informados. A comparação temporal é inclusiva nos limites enviados pelo cliente.

`GET /movements_summary` usa autenticação e `stock.read`, recebe os mesmos filtros de datas, Produto e Fornecedor, sem `tipo`, e devolve `total_movimentacoes`, `quantidade_entradas` e `quantidade_saidas`. O total e as somas são calculados sobre todo o conjunto correspondente, nunca sobre a página da tabela. A implementação consulta o conjunto filtrado em uma query e agrega `tipo`/`quantidade` no fluxo Xano, sem chamadas por linha a outras tabelas. Essa estratégia evita N+1, mas mantém o conjunto filtrado em memória no Xano; um agregado nativo do banco deve substituir essa estratégia se estiver disponível e validado na instância.

`GET /stock_summary` continua sendo a única fonte para contagens atuais de produtos abaixo do mínimo e sem estoque.

## Datas

Campos de data são opcionais e não recebem período presumido. O cliente transforma `YYYY-MM-DD` em início do dia inicial e fim do dia final em `America/Sao_Paulo`, em epoch milissegundos, compatível com `data_hora`. Quando somente um limite é informado, somente esse limite é enviado. Uma data inicial posterior à final é rejeitada antes da consulta.

## UI e apresentação

Filtros de Produto e Fornecedor reutilizam `searchable_select`, com busca local insensível a caixa e acentos sobre opções carregadas e paginação explícita. A tabela usa diretamente dados enriquecidos por joins em `GET /movements`; nenhum fetch ocorre por item. Data é exibida em `dd/mm/aaaa HH:mm`, tipo como Entrada/Saída, fornecedor ausente como `—`, e quantidade permanece distinta dos totais de unidades nos cards.

Cards: total de registros, soma das quantidades de entradas, soma das quantidades de saídas, produtos atualmente abaixo do mínimo e produtos atualmente sem estoque. Tabela: Data/Hora, Tipo, Código, Produto, Quantidade, Usuário, Fornecedor e Motivo.

## Segurança e falhas

Todos os endpoints exigem a sessão e a autorização de leitura `stock.read`. 401 usa o fluxo de login existente; 403 mostra mensagem de permissão; entradas inválidas mostram mensagem de filtros; falhas inesperadas exibem mensagem genérica. Lista vazia é estado válido. Nenhum token é exibido ou registrado.

## Publicação

Nenhum push é feito nesta change. XanoScript deve passar validação e dry-run isolado; o resultado CREATE/UPDATE deve ser revisado antes de qualquer push real.
