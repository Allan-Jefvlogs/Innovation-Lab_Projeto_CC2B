# Proposta: Integração real do módulo de Fornecedores

## Problema

A página `/fornecedores` apresenta registros fictícios e não permite manter os fornecedores reais do Xano.

## Objetivo

Integrar a listagem, busca, criação e edição de Fornecedores à API existente do Xano, preservando a associação por ID usada pelas entradas e pelo histórico.

## Escopo

- Substituir todos os dados de demonstração por dados reais paginados de `GET /suppliers`.
- Permitir busca local por nome/razão social e documento, sem diferenciar caixa ou acentos.
- Criar e editar Fornecedores pelos endpoints existentes, com trim e tratamento de documento duplicado.
- Exibir `ID | Nome / Razão social | Documento | Contato | Ações`, sem status e sem exclusão.
- Preservar as permissões existentes e a relação de `supplier_id` nas movimentações.
- Manter todos os Fornecedores disponíveis para seleção de entrada, sem filtrar por status legado.

## Fora do escopo

- Criar endpoints novos, alterar grants, ativar/inativar, excluir, alterar histórico ou fazer push Xano, commit ou push Git.

## Permissões

Reutilizar `supplier.read`, `supplier.create` e `supplier.update`. O Líder e Almoxarife mantêm escrita conforme os grants atuais; Auxiliar permanece somente leitura. Xano continua autoridade final.
