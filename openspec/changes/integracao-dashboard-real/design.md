# Design: Dashboard com dados reais

## Contratos existentes

- `GET /products` aceita `status`, `page`, `per_page` e retorna metadados paginados. A contagem de Produtos ativos usa `status=ativo`, `page=1`, `per_page=1` e `itemsTotal`; não percorre o catálogo.
- `GET /categories` e `GET /suppliers` retornam `itemsTotal`; cada contagem usa somente uma linha paginada.
- `GET /stock?situacao=abaixo_minimo&page=1&per_page=5` retorna a contagem total e no máximo cinco alertas. O contrato local define `abaixo_minimo` como saldo positivo menor que o mínimo; saldos zerados pertencem à situação `sem_estoque`.
- `GET /movements?page=1&per_page=5` entrega movimentações recentes e aceita `movement.read` ou `report.read`, conforme o contrato local de autorização central.
- Os outros recursos exigem, respectivamente, `product.read`, `category.read`, `supplier.read` e `stock.read`. A interface apenas evita consultas sem grant; o Xano continua validando a autorização.

## Requisições e cache

Com sessão validada e todos os grants, uma carga fria agenda cinco GETs concorrentes. A validação de sessão `/auth/me`, quando necessária antes do Dashboard, é uma chamada separada e pode levar o total inicial a seis. A reserva e a janela continuam sob o `XanoRequestCoordinator` existente, configurado em até sete chamadas por 20 segundos.

Os dados são projetados e armazenados no `SessionReadCache` existente, usando token apenas para gerar a impressão digital da chave. TTLs: Produtos 30 s; Categorias e Fornecedores 120 s; Estoque e Movimentações 15 s. Nenhum token, grant ou dado de autenticação é armazenado. Escritas Xano bem-sucedidas invalidam as cinco chaves do Dashboard da sessão; falhas de escrita não invalidam nem atualizam o cache.

O cache já usado pela listagem de Produtos não é usado como fonte direta para o indicador: sua projeção contém somente uma página, combina Estoque e Produtos, e não preserva `itemsTotal` filtrado por status. Não é suficiente para garantir a contagem de Produtos ativos.

## Falhas e autorização

Sem permissão, o carregador não faz a consulta e o indicador informa falta de acesso. `401` limpa o cache da sessão e retorna ao login. `403` remove o dado privado da fonte negada e mantém a tela sem reutilizar esse cache. Falhas temporárias podem usar uma entrada anterior dentro da janela de retenção do cache, identificada como desatualizada. Sem resposta válida, o indicador aparece indisponível; nunca se substitui erro por zero. Uma única ação manual tenta novamente somente as fontes com falha, reaproveitando as demais entradas válidas.

O Dashboard não confirma operações de estoque e não é fonte de autorização nem de saldo para Entradas/Saídas.

## Evidências e limitações

Os testes simulados verificam projeção, contagem, grants, isolamento, expiração, invalidação por escrita, 429 e timeout. A compilação Reflex é uma validação local. Estes resultados não comprovam publicação dos contratos locais nem comportamento no workspace remoto. A apresentação visual e a confirmação das contagens reais ainda dependem de teste no navegador com sessão e grants apropriados.
