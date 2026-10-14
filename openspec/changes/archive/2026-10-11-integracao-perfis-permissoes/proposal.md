# Proposta: integração de perfis e permissões

## Problema

A rota `/perfis` mostra perfis e uma matriz fictícia. O Xano já fornece o catálogo real, os grants por perfil e um endpoint administrativo para substituí-los com revisão e auditoria.

## Objetivo

Permitir ao Líder consultar a matriz real e editar apenas os grants de Almoxarife e Auxiliar de almoxarifado, usando os endpoints existentes.

## Escopo

- Remover os mocks da página e carregar `GET /permissions`.
- Mostrar perfis reais e agrupar o catálogo por módulo, com labels em português e códigos preservados internamente.
- Separar permissões salvas das marcações em edição; descartar alterações não salvas ao trocar de perfil.
- Enviar códigos e `permission_revision` no PATCH, atualizar a matriz após sucesso e tratar conflito de revisão.
- Manter Líder protegido e sem controles editáveis.
- Retornar os grants efetivos do usuário autenticado em `/auth/me` e condicionar a navegação a esses códigos.
- Manter as APIs e a autorização do backend como autoridade final; recarregar grants em novo login/restauração de sessão.
- Separar `movement.read` e `report.read` de `stock.read`, com grants visíveis na matriz administrativa.
- Preservar a listagem compartilhada de movimentos para Histórico ou Relatórios e servir opções mínimas dos filtros por endpoint protegido por `report.read`.

## Fora do escopo

Alterar regras de criação/edição de cadastros, entradas, saídas, usuários, autenticação ou auditoria; executar seed/migração de grants ou publicar Xano; adicionar polling e atualização automática de grants durante sessão ativa.
