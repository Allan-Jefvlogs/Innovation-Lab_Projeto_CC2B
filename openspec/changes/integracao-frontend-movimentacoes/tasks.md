# Tasks: Integração Reflex de Movimentações

## 1. Seletores e carregamento

- [x] 1.1 Extrair seletor pesquisável reutilizável com busca parcial, sem caixa/acentos e valor por ID.
- [x] 1.2 Reutilizar o seletor em Categoria e Fornecedor padrão dos formulários de Produto.
- [x] 1.3 Carregar Produtos e Fornecedores de Entrada com autenticação e primeira página limitada.
- [x] 1.4 Implementar carregamento explícito das páginas seguintes sem carregamento ilimitado.

## 2. UX de Entrada

- [x] 2.1 Implementar combobox pesquisável de Produto por código/nome e manter `product_id` real.
- [x] 2.2 Implementar leitura de código por teclado e busca ao pressionar Enter, avançando páginas existentes sob demanda.
- [x] 2.3 Exibir erro sem seleção válida quando o código não for encontrado.
- [x] 2.4 Implementar combobox pesquisável de Fornecedor e preenchimento a partir de `fornecedor_padrao_id`.
- [x] 2.5 Exibir data/hora opcional vazia e explicar a regra de fallback do backend.
- [x] 2.6 Habilitar o registro da Entrada no endpoint publicado, com estado de envio e proteção contra duplo clique.

## 3. Limites e validação

- [x] 3.1 Corrigir textos quebrados encontrados nos formulários de Produto e manter rótulos da tela de movimentações em UTF-8.
- [x] 3.2 Documentar reutilização futura de busca/leitura de Produto na Saída.
- [x] 3.3 Validar compile Reflex, OpenSpec strict e `git diff --check`.
- [ ] 3.4 Testar manualmente busca, leitor, validações e fluxo de Entrada com backend runtime.
- [x] 3.5 Integrar a gravação de Entrada ao endpoint Xano publicado, sem implementar Saída.

## 4. Integração da Entrada

- [x] 4.1 Adicionar XanoClient.create_stock_entry para POST /api:estoque/entries com opcionais omitidos quando vazios e sem user_id.
- [x] 4.2 Implementar validação no EntryState para Produto, quantidade positiva, motivo e fornecedor opcional.
- [x] 4.3 Vincular campos da Entrada ao State, habilitar o botão, bloquear envio duplicado, mostrar loading e feedback.
- [x] 4.4 Mapear erros funcionais, permissão, sessão, conexão e fallback genérico.
- [x] 4.5 Mostrar saldo retornado pelo backend, limpar os campos em sucesso e reutilizar a recarga existente de Produtos ao abrir /produtos.
- [x] 4.6 Validar compile Reflex, OpenSpec strict e git diff --check.
- [ ] 4.7 Executar os testes manuais de Entrada sem automatizar POST nesta implementação.

## 5. Refinamento de UX da Entrada

- [x] 5.1 Resolver Produto por código exato ao pressionar Enter e manter seleção manual bidirecional com o campo de código.
- [x] 5.2 Tornar os searchable_select popovers sobrepostos, com fechamento por blur/Escape e abertura exclusiva entre seletores relacionados.
- [ ] 5.3 Validar manualmente leitura, código inexistente, seleção manual e fechamento dos popovers.

## 6. Integração da Saída

- [x] 6.1 Adicionar XanoClient.create_stock_exit para POST /api:estoque/exits, omitindo opcionais vazios e sem user_id/supplier_id.
- [x] 6.2 Criar ExitState independente de EntryState, com busca por código, seletor manual e carregamento de saldos reais.
- [x] 6.3 Implementar validação de saldo e quantidade, bloqueio de saldo zero/insuficiente e prevenção de duplo envio.
- [x] 6.4 Integrar campos, feedback, mapeamento de erros e atualização do saldo após sucesso.
- [x] 6.5 Documentar contrato, saldo, opcionais, identidade do usuário e tratamento de erros.
- [x] 6.6 Validar compilação Reflex, OpenSpec strict e git diff --check sem chamar POST /exits.
- [ ] 6.7 Validar manualmente a Saída no navegador sem registrar movimentação de teste.