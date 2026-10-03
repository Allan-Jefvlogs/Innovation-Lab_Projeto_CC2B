# Proposal: Integração real do módulo de Categorias

## Problema

A tela `/categorias` ainda exibe registros fictícios. Apesar de o Xano já fornecer leitura, criação e inativação, a interface não usa esses endpoints e não há endpoint local de ativação.

## Objetivo

Integrar a tela ao Xano para listar, pesquisar, criar e alternar o status de Categorias sem substituir erros por dados mockados.

## Escopo

- Carregar todas as páginas de `GET /categories` e pesquisar localmente por nome, sem diferenciar caixa ou acentos.
- Criar Categoria por `POST /categories`, com nome trimado, obrigatório, único e status inicial ativo.
- Ativar/inativar por PATCH, confirmando o status retornado pelo Xano antes de atualizar o State.
- Remover números fictícios de Produtos e exibir somente ID, nome, status e switch.
- Criar o endpoint de ativação ausente usando a permissão existente `category.update`; reutilizar a permissão existente `category.inactivate` para inativação.
- Preservar vínculos históricos de Produtos. O módulo de Produtos já filtra Categorias ativas em novos formulários e preserva uma referência atual inativa na edição.

## Fora do escopo

- Contagem de Produtos por Categoria, edição do nome, exclusão, mudança da matriz de permissões e alteração de outros módulos.
- Push Xano, commit ou push Git.

## Permissões

Manter a matriz existente: `category.read` permite leitura aos perfis já autorizados; criação e mudança de status continuam sujeitas aos grants atuais, que reservam escrita ao Líder. A UI oculta os controles de escrita para os demais perfis e o Xano permanece autoridade final.
