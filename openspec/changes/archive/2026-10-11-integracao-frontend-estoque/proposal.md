# Integrar a tela de Estoque com dados reais

## Problema

A tela `/estoque` ainda apresenta contadores e produtos fictícios, e os cards de situação não levam a uma listagem filtrada.

## Objetivo

Usar os saldos persistidos em `inventory_stock` enriquecidos com Produto, apresentar contagens reais por produto e permitir consultar cada situação em páginas próprias.

## Escopo

- Remover dados mockados da página de Estoque.
- Reutilizar `GET /stock`, adicionando filtro opcional por situação.
- Disponibilizar resumo agregado de totais por situação, protegido por `stock.read`.
- Implementar paginação e rotas reutilizáveis para listas por situação.
- Preservar as regras de autorização atuais.

## Fora do escopo

- Alterar operações de Entrada ou Saída.
- Alterar Produtos, Categorias, Fornecedores, Histórico, ou qualquer regra de saldo.
- Publicar mudanças no workspace Xano.
