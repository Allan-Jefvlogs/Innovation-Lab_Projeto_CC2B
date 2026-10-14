# Integrar operações de Produto no Reflex

## Por que

A lista de Produtos já consulta o Xano, mas os formulários de criação e edição ainda não estão conectados a eventos de persistência. A tela de criação atual apresenta campos estáticos sem estado nem chamada HTTP; por isso, clicar em “Salvar produto” não envia dados ao backend. Também não há navegação para editar um registro nem controle de status integrado.

## O que muda

- Integrar criação, consulta individual, atualização e inativação aos endpoints existentes de Produto.
- Exibir ação de edição por ID do Xano e proteger a rota dinâmica correspondente.
- Adicionar ativação sem exclusão física. O snapshot atual não possui endpoint de ativação; esta change inclui um endpoint Xano local `PATCH /products/by_id/{product_id}/activate`, protegido por `product.update`.
- Manter o Xano como autoridade de persistência e autorização.

## Escopo

Inclui integração Reflex dos formulários de Produto e listagem, campos permitidos pelo contrato Xano, carregamento de Categorias ativas para seleção e feedback de carregamento/erro/sucesso. Inclui o endpoint local de ativação necessário para completar o ciclo de status.

Não inclui criação/edição/inativação de Categoria ou Fornecedor, exclusão física, alteração de saldo/movimentações, alteração de login/sessão, nem sincronização ou push do endpoint novo para o workspace Xano.

## Dependências e decisões existentes

- Reutiliza autenticação, token Bearer, `AuthState` e o cliente Xano existente.
- Usa `product.read`, `product.create`, `product.update` e `product.inactivate` nos endpoints correspondentes.
- O endpoint genérico PATCH não altera `status`; a reativação usa endpoint específico, sem ampliar o contrato de PATCH existente.
- Categoria é uma referência numérica `categoria_id`; somente Categorias ativas podem ser escolhidas em novas associações.
- O backend sempre valida grants; a visibilidade de ações no frontend é apenas orientação de UX.

## Validação

Validar XanoScript localmente pelo MCP, compilar Reflex, validar esta change OpenSpec e revisar `git diff --check`. Testes com registros reais devem ser feitos manualmente em workspace/datasource apropriado. Esta change não autoriza push ao Xano.
