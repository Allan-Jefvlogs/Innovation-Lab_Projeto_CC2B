# Design: Relatórios operacionais

## Fluxo e filtros

`ReportState` mantém campos editáveis separados do snapshot aplicado. Aplicar filtros copia datas, tipo, Produto e Fornecedor para o snapshot, recarrega tabela e resumo na primeira página; limpar restaura todos os campos e aplica a consulta geral. Mudar de página usa o snapshot existente. Datas opcionais são convertidas para limites inclusivos em `America/Sao_Paulo`.

Datas inicial e final compartilham uma linha flexível e quebram em viewport estreita. Tipo, Produto e Fornecedor compõem uma segunda linha equilibrada. A tela exibe somente três cards informativos: total de registros, soma das unidades de entrada e soma das unidades de saída.

## Contratos Xano

`GET /movements` fornece tabela paginada e recebe `tipo`, `product_id`, `supplier_id`, `date_from` e `date_to`. `GET /movements_summary` recebe os mesmos filtros relevantes e calcula os totais sobre todos os registros correspondentes. O campo `tipo` é opcional e aceita `entrada` ou `saida`; tipo Saída produz soma de entradas igual a zero e vice-versa. Ambos os endpoints seguem protegidos por `stock.read`.

## Exportação

PDF e XLSX são gerados em memória pela aplicação Reflex, sem criar arquivos permanentes ou dependências adicionais. O XLSX usa OOXML e o PDF usa um gerador enxuto na biblioteca padrão Python. A obtenção de linhas percorre `GET /movements` em lotes de 100 até `nextPage` ficar vazio, com limite de segurança de 100.000 registros. A tabela exportada, resumo e filtros vêm do mesmo snapshot aplicado; exportações não se limitam à página visível. O PDF usa A4 paisagem e repete os cabeçalhos nas páginas seguintes.

## Apresentação e segurança

A tabela usa joins existentes para Produto, Usuário e Fornecedor, sem requests por linha. Erros são registrados pelo cliente com método, path, status, código e payload do Xano, sem Authorization/token; a interface mostra mensagem amigável. A situação atual do estoque não faz parte desta versão dos relatórios.
