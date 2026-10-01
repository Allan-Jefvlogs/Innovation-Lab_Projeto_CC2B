# Tasks: Fundação técnica de Estoque

## 1. Contrato e modelo
- [x] 1.1 Conferir specs consolidadas, changes arquivadas e snapshot Xano para evitar duplicação.
- [x] 1.2 Definir saldo obrigatório por Produto com inicialização zero e situação derivada.
- [x] 1.3 Definir `stock.read`, concessões iniciais aditivas e grupo/endpoint de consulta.

## 2. Persistência e ciclo de vida
- [x] 2.1 Criar `inventory_stock` com referência única ao Produto e quantidade decimal não negativa.
- [x] 2.2 Criar função interna idempotente para inicializar os Produtos já existentes sem saldo.
- [x] 2.3 Criar saldo zero atomicamente com Produto em `POST /products`.

## 3. Permissão e consulta
- [x] 3.1 Acrescentar `stock.read` ao catálogo e aos grants iniciais de Almoxarife e Auxiliar sem substituir grants existentes.
- [x] 3.2 Criar grupo `Inventory Stock` e endpoint autenticado/paginado `GET /stock` com autorização `stock.read`.
- [x] 3.3 Retornar produto, quantidade, mínimo, situação derivada e paginação.

## 4. Validação
- [x] 4.1 Validar todos os XanoScripts novos/alterados com Xano Developer MCP.
- [x] 4.2 Executar `openspec validate fundacao-tecnica-estoque --strict`.
- [x] 4.3 Executar `git diff --check` e revisar os arquivos Xano afetados.
- [ ] 4.4 Testar autorização, criação atômica, idempotência de inicialização, paginação e limites das três situações em datasource isolado.

## 5. Publicação posterior
- [ ] 5.1 Revisar e aprovar o escopo publicado; esta change local não autoriza push remoto.
- [ ] 5.2 Antes de ativar consulta remota, executar a inicialização de saldos existentes após confirmar que não há saldos externos a reconciliar.
- [ ] 5.3 Integrar o Reflex em change própria/de integração depois de publicar e validar o endpoint.
