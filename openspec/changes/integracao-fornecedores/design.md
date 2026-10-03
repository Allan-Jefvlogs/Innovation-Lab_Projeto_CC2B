# Design: Integração do módulo de Fornecedores

## Modelo e API

A tabela Xano `supplier` já possui `id`, `nome_razao_social`, `tipo_documento` (`CPF`/`CNPJ`), `documento` único, `contato` opcional, `endereco` opcional e um campo legado `status`. A tela não exibirá nem editará status. Não serão criadas rotas; serão reutilizados `GET /suppliers`, `POST /suppliers`, `GET /suppliers/by_id/{supplier_id}` e `PATCH /suppliers/by_id/{supplier_id}`.

O POST e PATCH aplicarão trim nos campos textuais e rejeitarão nome vazio; POST também rejeitará documento vazio. A unicidade de documento será mantida pela validação existente e pelo índice único. PATCH continuará aceitando `limpar_contato` e `limpar_endereco` para apagar valores opcionais sem alterar campos não enviados.

## State e interface

`SupplierState` carregará todas as páginas (100 itens por chamada), fará busca local por substring normalizada em nome e documento e manterá os dados de formulário, item em edição, loading e mensagens. Edição carrega o detalhe real antes de abrir o formulário. O modal inclui nome/razão social, tipo de documento, documento, contato e endereço opcional, que já existe no modelo.

A tabela apresenta somente ID, Nome / Razão social, Documento, Contato e Ações. Não há status, ativação, inativação ou exclusão. Erros de autorização, duplicidade, validação, sessão e conexão recebem feedback adequado sem mocks.

## Integração com Entrada

A página de Entrada continuará usando o seletor já existente e IDs reais. A carga e a paginação deixarão de filtrar `status=ativo`, pois Fornecedor não terá status operacional; um fornecedor criado ou previamente associado poderá ser selecionado. `inventory_movement.supplier_id` não é alterado. O nome será atualizado em novas consultas/carregamentos.

## Permissões

Reutilizar grants atuais: leitura para os três perfis, escrita para Líder e Almoxarife; Auxiliar somente consulta. Os botões de escrita são ocultados para Auxiliar por conveniência, sem substituir autorização do Xano.

## Validação e publicação

Validar os XanoScripts alterados no MCP, compilar Reflex, validar OpenSpec strict e `git diff --check`. Preparar dry-run Xano limitado ao POST e PATCH cadastrais e revisar seus objetos. Não publicar sem revisão do preview; não executar testes runtime de criação/edição nesta etapa.
