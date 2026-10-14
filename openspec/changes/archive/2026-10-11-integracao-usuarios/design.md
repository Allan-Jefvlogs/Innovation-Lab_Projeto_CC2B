# Design: usuários e troca obrigatória de senha

## Base existente

`user` é a tabela autenticável. Seu campo nativo `password` exige ao menos oito caracteres, uma letra e um dígito. `inventory_profile_id` referencia `inventory_profile`. O código reservado `administrator` na função `Inventory/authorize_permission` é exclusivo do perfil Líder. `GET /permissions` fornece os perfis reais.

## Contrato Xano

### Status de usuário

O schema acrescenta `bool is_active?=true`; registros existentes sem valor explícito continuam tratados como ativos. `GET /users` e `GET /users/by_id/{user_id}` devolvem a flag. `PATCH /users/by_id/{user_id}/inactivate` e `/activate` exigem `administrator` e editam exclusivamente `is_active`. Inativação recusa `$auth.id` como alvo. Se o alvo é Líder, verifica outro Líder ativo antes da escrita. Sem trava transacional validada, duas inativações cruzadas simultâneas entre Líderes ainda exigem proteção atômica adicional para uma garantia absoluta.

`auth/login` verifica a flag após conferir a senha e antes de emitir token. `/auth/me` recusa conta inativa; o frontend apaga o token e mostra a mensagem de inativação. A função `Inventory/authorize_permission` recusa conta inativa mesmo com token antigo. A troca inicial de senha também recusa usuário inativo. Reset administrativo de conta inativa permanece permitido, sem reativá-la. Reativação preserva perfil, senha e `must_change_password`. Nenhum registro `user` é removido, preservando histórico, movimentações e referências.

| Objeto | Alteração |
| --- | --- |
| `user` | Adicionar `bool must_change_password?=false` ao fim do schema. |
| `POST /users` | Escrever senha nativa e `must_change_password=true`. |
| `PATCH /users/by_id/{user_id}` | Aceitar somente nome, e-mail e perfil. |
| `PATCH /users/by_id/{user_id}/reset_password` | Exigir `administrator`; substituir senha nativa e marcar `true` em uma edição do registro. |
| `PATCH /auth/change-initial-password` | Usar exclusivamente `$auth.id`; exigir flag `true`; escrever senha nativa e marcar `false` em uma edição do registro. |
| `GET /auth/me` | Incluir a flag na resposta, sem senha ou hash. |
| `Inventory/authorize_permission` | Recusar acesso ao estoque quando a flag for `true`, inclusive para Líder. |
| `POST /auth/login` | Manter autenticação e retorno; remover o hash do metadata do evento de login. |

Os novos endpoints validam senha e confirmação iguais. A tabela `user` aplica a complexidade já existente. O reset não devolve senha nem hash. O endpoint de troca não recebe `user_id` do cliente.

## Interface e sessão

O formulário de cadastro chama a senha de “Senha inicial”. A edição mostra apenas nome, e-mail e perfil. Um modal separado realiza o reset. A nova página `/alterar-senha` usa o token autenticado para trocar a senha do próprio usuário. Valores de senha são enviados apenas pelo evento do formulário; o State guarda apenas flags de visibilidade, loading e mensagens.

`AuthState` lê `must_change_password` de `/auth/me`. Login e restauração de sessão encaminham para `/alterar-senha` quando necessário. `require_auth` redireciona qualquer outra rota protegida. Depois da troca, o frontend limpa o token, volta ao Login e informa o sucesso. O bloqueio no backend cobre APIs que usam a função central de autorização; endpoints fora dela exigiriam revisão separada.

## Segurança e implantação

A senha atual não é consultada nem exibida. A edição comum não aceita senha. As escritas de senha e flag ocorrem juntas em cada endpoint. Contas antigas ficam com a flag falsa. A publicação exige schema e endpoints relacionados no mesmo plano; até lá, o frontend novo não deve ser considerado pronto em runtime. Dry-run e validação estática não comprovam o comportamento remoto.
