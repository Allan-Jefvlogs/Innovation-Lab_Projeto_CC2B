# Substituir Histórico por Auditoria

## Problema

A página `/movimentacoes` duplica informações de entradas e saídas já disponíveis em Relatórios. O sistema ainda não oferece uma consulta central das ações administrativas e operacionais.

## Objetivo

Retirar Histórico da navegação e oferecer Auditoria, com eventos persistidos pelo Xano somente após operações de negócio bem-sucedidas, consulta paginada e filtros úteis.

## Escopo

- Criar armazenamento e consulta de eventos de auditoria no Xano.
- Criar uma página Reflex protegida para leitura de auditoria.
- Manter intactos movimentos, endpoints de estoque e relatórios.
- Restringir a consulta inicialmente a administradores, pois não existe `audit.read` provisionado.
- Apresentar detalhes persistidos com descrições legíveis sem revelar valores pessoais ou segredos.
- Permitir exportação PDF dos eventos autorizados e filtrados, com limite explícito e sem arquivos permanentes no servidor.

## Fora de escopo / limitações

- Alterar ou publicar qualquer objeto remoto do Xano.
- Registrar eventos retroativos.
- Alterar arquivos de e-mail, Brevo, Resend, dispatcher ou solicitações de compra. Eventos de compras ficam pendentes até uma change coordenada com a integração de e-mail.
- Exclusão física de Produto/Categoria/Fornecedor: o sistema atual usa desativação, não possui endpoints de exclusão.
- Eventos de autenticação, que não fazem parte das mutações de domínio atuais.
