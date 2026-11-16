# Revisão de compatibilidade e segurança — 2026-11-11

> A decisão posterior de escopo acadêmico substituiu o bloqueio SQL do PATCH: o arquivo atual usa db.get/db.edit/db.add, sem versão, reivindicação ou Lock. As análises antigas de concorrência abaixo são históricas; a correção de isolamento da Reposição continua válida. O plano atual está em publicacao-academica.md.

## Evidências e limites

Nenhuma leitura de dados, publicação, migração, atribuição de perfil ou escrita foi executada no workspace. A conclusão abaixo combina código local, documentação oficial e validação sintática do Xano Developer MCP 2.2.6. Não comprova execução no workspace 152211, branch v1, datasource live.

## PATCH de status: permanece bloqueado

O script local preserva grant específico, ator autenticado, status esperado, transições aprovadas, justificativa na rejeição, limpeza de active_product_id e histórico na mesma estrutura db.transaction. As proteções UNIQUE de criação (chave_idempotencia e active_product_id) não impedem, por si só, que duas atualizações da mesma solicitação sobrescrevam status.

A implementação atual depende de Direct Database Query. A documentação web restringe esse recurso aos planos Launch/Scale atualizados e descreve identificadores físicos/aliases que não foram confirmados para o SQL local. Não há prova de que o SQL do script participa da mesma transação do histórico nesse workspace.

Foram investigadas operações nativas:

- Edit Record documenta seleção por field_name/field_value, sem compare-and-swap por ID + estado nem lock de linha documentado nessa página. Releitura seguida de db.edit não satisfaz o requisito.
- Bulk Operations documenta arrays com IDs para Bulk Update/Patch. Isso não demonstra atualização condicional por status esperado. A amostra db.bulk.update com where foi rejeitada pelo MCP instalado: argumento where inválido.
- O material de referência do MCP mostra isolation=serializable, mas a amostra mínima foi rejeitada pelo mesmo validador, que esperava stack diretamente dentro de db.transaction. Não usar esse exemplo como garantia disponível.
- Database Transaction documenta rollback para falhas de operações de banco. Não é suficiente para provar isolamento contra atualizações concorrentes; a documentação alerta que falhas em condicionais e transformações não determinam rollback.

Não foi encontrada solução já comprovada e compatível com as ferramentas/plano atuais. O PATCH permanece sem substituição e fora da publicação.

### Alternativas para revisão posterior

1. Verificar com o Xano uma operação nativa de atualização condicional ou lock disponível no Free. Se existir no editor do workspace, exportar o XanoScript gerado, validar importação e executar testes controlados de conflito e rollback após autorização. Não basta o recurso aparecer em documentação genérica.
2. Se não houver esse recurso, avaliar um protocolo de transição com versão e reivindicação UNIQUE gravada por operação nativa, dentro da transação. Exigiria mudança de schema local/revisada e participação de **todos** os escritores de status, inclusive cancelamento e recebimento futuro. Validar estado/versão antes da reivindicação, impedir duas reivindicações da mesma versão no banco e manter pedido/histórico/reivindicação atômicos. Esse desenho não foi implementado nem comprovado; precisa de aprovação estrutural e teste real antes de substituir o PATCH.

Não utilizar um bloqueio somente no Reflex ou processo Python: ele não cobre outras sessões, processos e chamadas diretas à API.

## Reposição: correção local implementada

- Reutiliza Inventory/purchase_request_notification_all_access após stock.read e purchase_request.read. O helper reconhece administrador ou grant manage; read já foi exigido pelo chamador.
- As duas consultas paginadas continuam classificando todos os produtos insuficientes conforme existência de solicitação ativa, sem filtrar o produto pela propriedade do pedido.
- O backend inicializa os cinco campos de pedido com null. Só preenche o objeto público se o pedido pertence a auth.id ou há escopo global. O solicitante é projetado apenas para uso interno.
- A resposta acrescenta solicitacao_detalhes_disponiveis. Sem acesso, ID, quantidade solicitada, urgência, status e data permanecem null. Campos de produto, saldo, mínimo e situação continuam disponíveis.
- Mantém três db.query no endpoint (saldo ausente, elegíveis, já solicitados). O helper acrescenta leituras constantes de autorização, sem consulta por produto. Continua um GET de leitura para carregar as duas abas.
- Reflex exibe Detalhes restritos, sem número zero falso nem ação de cancelamento. O cliente rejeita marcador que não seja booleano e detalhes preenchidos em linha marcada como restrita.
- A ausência do marcador mantém compatibilidade com o contrato legado. Isso não torna seguro um backend antigo que continue expondo dados: a publicação da projeção segura é obrigatória.
- Cache usa a mesma infraestrutura/TTLs/invalidação por endpoint, com namespace de contrato e chaves separadas por leitura própria/global. Mudança de escopo descarta linhas anteriores, mantendo chaves de escrita ambígua. Não altera o coordenador.
- Publicar o helper, se ausente, antes do endpoint. Validar por leitura com contas de demonstração autorizadas: próprio, terceiro sem manage, gestor com read+manage e administrador. O perfil Compras, sem stock.read, deve continuar sem acesso à página completa de Reposição.

## Gráfico: revisão posterior implementada em dashboard-funcional

Na revisão inicial, movements_dashboard_get.xs usava db.direct_query para gerar datas e agrupar contagens. A etapa posterior autorizada removeu essa dependência e implementou db.query com stream, filtros de data e agregação em sete contadores locais. A documentação atual está em ../dashboard-funcional/grafico-xano-free.md; nenhuma versão foi publicada.

São mantidas duas declarações de consulta de dados, um GET do frontend e o envelope serie/recentes. A contagem consome todo o stream do período, não uma página. A semântica dos filtros/cursor e o resultado real ainda dependem de validação publicada de leitura.

A investigação de concorrência foi ampliada em diagnostico-concorrencia-unique.md. Não altera o PATCH de status, o cancelamento nem schemas. A opção Lock de Query All Records foi aceita apenas sintaticamente; o protocolo UNIQUE continua sendo proposta sem garantia de runtime.

## Validação local

- Onze testes novos de isolamento/compatibilidade, combinando análise estrutural do backend e mocks do consumidor/perfis; não executam XanoScript nem provam autorização em runtime.
- Suíte regressiva: 332 testes aprovados, incluindo Reposição, perfil Compras, cache e demais módulos.
- A sintaxe final de stock_replenishment_get.xs foi aceita pelo MCP. As amostras rejeitadas de atualização condicional e isolamento foram avaliadas somente em memória, sem arquivos publicados ou executados.
- Compilação Reflex e OpenSpec strict aprovados. A verificação de whitespace dos arquivos desta etapa é registrada separadamente do problema preexistente em users_by_id_inactivate_patch.xs:35, que permanece fora do escopo.

## Fontes

- https://docs.xano.com/the-function-stack/functions/database-requests/direct-database-query
- https://docs.xano.com/the-function-stack/functions/database-requests/edit-record
- https://docs.xano.com/the-function-stack/functions/database-requests/bulk-operations
- https://docs.xano.com/the-function-stack/functions/database-requests/database-transaction
