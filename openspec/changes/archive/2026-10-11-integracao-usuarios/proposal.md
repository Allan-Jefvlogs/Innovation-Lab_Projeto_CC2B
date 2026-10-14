# Proposta: integração de usuários e senha temporária

## Problema

A administração de usuários já lista, cria e edita contas reais. A senha definida pelo Líder ainda pode ser tratada como definitiva e o formulário de edição aceita troca direta. É necessário separar a senha temporária do reset administrativo e da senha definitiva escolhida pelo próprio usuário.

## Objetivo

Persistir a exigência de troca de senha, encaminhar o usuário à troca após login e impedir o acesso às APIs de estoque enquanto a exigência estiver ativa. O Líder poderá apenas cadastrar com senha inicial ou substituí-la por outra senha temporária em uma ação de reset explícita.

## Escopo

- Incluir `is_active` na tabela `user` com padrão `true`, sem apagar registros ou referências históricas.
- Permitir ao Líder inativar ou reativar usuário por ação explícita, com confirmação, e mostrar o status na listagem.
- Recusar login, restauração de sessão e APIs de estoque para usuário inativo.
- Proibir autoinativação e exigir outro Líder ativo antes de inativar um Líder.

- Acrescentar `must_change_password` à tabela autenticável `user`, com padrão `false` para contas existentes.
- Marcar `true` no cadastro e no reset; marcar `false` na troca feita pelo próprio usuário.
- Remover senha do PATCH cadastral e criar endpoints separados de reset administrativo e troca inicial autenticada.
- Expor a flag em `/auth/me`, estender o redirecionamento de login e a proteção central de rotas, e criar `/alterar-senha`.
- Incluir controles de mostrar/ocultar apenas para os valores recém-digitados nos formulários de cadastro, reset e troca.

## Fora do escopo

Visualização ou recuperação da senha atual, exclusão de usuários, alteração das permissões existentes, publicação Xano, commit e push.
