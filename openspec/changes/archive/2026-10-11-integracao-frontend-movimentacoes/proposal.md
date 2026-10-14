# Preparar seleção de Produto e Fornecedor na Entrada

## Problema

A tela de Entrada ainda usa opções fixas e não identifica Produtos nem Fornecedores reais. Isso impede a busca por código/nome e o uso do Fornecedor padrão cadastrado no Produto. O projeto ainda não possui contrato backend local para confirmar uma movimentação de entrada.

## O que muda

- Carregar Produtos e Fornecedores reais com a sessão atual do NexStock.
- Reutilizar o seletor pesquisável de relacionamentos nos formulários de Produto e Entrada.
- Permitir busca parcial, sem diferenciar caixa ou acentos, mostrando nomes/códigos e mantendo IDs reais no State.
- Preparar leitura de código de barras como entrada de teclado: Enter procura o código e seleciona o Produto correspondente.
- Preencher o Fornecedor da Entrada pelo Fornecedor padrão do Produto quando disponível, permitindo escolher outro Fornecedor ativo ou deixar vazio.
- Exibir data e hora opcional sem gerar valor no frontend quando estiver vazia.
- Manter o registro da entrada desabilitado até existir contrato de gravação backend.

## Fora do escopo

- Criar ou alterar API, tabelas, estoque ou Xano.
- Registrar entradas/saídas, atualizar saldo ou histórico no Reflex.
- Integrar gravação de movimentação, decisão ainda dependente do contrato backend.
- Implementar a seleção/leitura funcional na tela de Saída nesta change; o padrão será documentado para reutilização futura.

## Dependências

- Reutiliza autenticação, Bearer token e XanoClient existentes.
- Reutiliza `GET /products`, `GET /suppliers` e `GET /suppliers/by_id/{supplier_id}`.
- Reutiliza o padrão de seletor pesquisável definido em `integracao-frontend-produtos`.
- O Xano permanece autoridade de dados, integridade e autorização.

## Aditamento de escopo: Saída de estoque

Esta mudança também integra /movimentacoes/saidas ao endpoint já publicado POST /api:estoque/exits. A Saída usa ExitState separado, pesquisa Produto real por seletor ou código lido, mostra o saldo de GET /stock, valida a quantidade contra o saldo, envia data_hora e observacao apenas quando preenchidos e nunca envia user_id ou supplier_id. As seções anteriores que diziam que a Saída ficaria fora do escopo são substituídas por este aditamento. O backend Xano e o fluxo de Entrada permanecem fora das alterações funcionais desta integração.

## Aditamento de escopo: consulta do Histórico

Esta mudança também integra a rota /movimentacoes ao GET /api:estoque/movements. A tela exibe as movimentações reais em páginas de 20 itens, combina filtros de tipo e Produto e apresenta os dados relacionados que o backend já retorna. A pesquisa de Produto é local às opções carregadas; nenhuma consulta é feita por caractere ou por movimentação. Este escopo é somente de leitura e não altera os fluxos de Entrada e Saída nem o backend Xano.
