# Design: integração de perfis e permissões

## Contrato existente

`GET /permissions` retorna `profiles` (`id`, `code`, `display_name`, `permission_revision`), `permissions` (`id`, `code`, `resource`, `action`) e `permission_matrix`. Para `administrator`, a matriz informa acesso `integral` e `editable=false`; para `stockkeeper` e `read_only`, fornece a lista de códigos concedidos e `permission_revision`.

`PATCH /permissions/profiles/{profile_code}` recebe `permissions` como lista de códigos e `permission_revision`. O Xano exige `administrator`, recusa editar esse perfil, valida os códigos, substitui os grants e registra `inventory_permission_audit` na mesma transação. O frontend não escreve diretamente nas tabelas.

## Estado e interface

`PermissionState` mantém perfis, catálogo, grants salvos, códigos em edição, revisão do perfil e mensagens. Os grupos visuais são derivados de `resource`; os códigos vêm apenas do catálogo. Labels conhecidos são traduzidos para português; códigos futuros recebem fallback legível sem criar grants.

O perfil Líder mostra o catálogo integral marcado e bloqueado. Almoxarife e Auxiliar podem marcar/desmarcar localmente. Trocar de perfil descarta o rascunho anterior e informa essa decisão. Cancelar alterações restaura os códigos salvos. Salvar envia a revisão conhecida; em conflito, a matriz é recarregada para revisão antes de nova tentativa. Após sucesso, a resposta atualiza o estado e uma nova consulta confirma o persistido.

## Segurança e limites

`AuthState.require_auth` mantém `/perfis` acessível apenas ao perfil Líder, e `PermissionState` verifica a sessão antes de chamar a API. A autoridade final permanece no Xano. A auditoria existente é mantida. Validação local não substitui teste runtime dos grants após publicação do frontend.

## Permissões efetivas da sessão e navegação

`GET /permissions` é administrativo e não será chamado pela navegação de funcionários. O endpoint autenticado `GET /auth/me` incluirá `inventory_profile_code` e `permission_codes`: para `administrator`, os códigos do catálogo representam seu acesso integral; para outros perfis, serão carregados de `inventory_profile_permission` e `inventory_permission`. O estado global preencherá esses campos tanto no login quanto na restauração de sessão.

A sidebar usará os códigos retornados pelo Xano: `product.read`, `category.read`, `supplier.read`, `stock.read`, `stock.entry`, `stock.exit`, `movement.read` e `report.read`. Estoque exige `stock.read`; Histórico exige `movement.read`; Relatórios exige `report.read`. Usuários e Perfis e permissões exigem `administrator`. Dashboard continua visível para toda sessão autenticada por não ter uma permissão de backend dedicada identificada.

`AuthState.require_auth` aplicará os mesmos grants como proteção de navegação do frontend; `/usuarios` e `/perfis` continuam restritas ao administrator. Toda chamada de API permanece protegida no Xano. Os grants são recarregados em login/restauração de sessão; alterações feitas por um Líder terão efeito na próxima restauração, sem polling. Não há atualização automática durante uma sessão já aberta.

O endpoint compartilhado `GET /movements` aceita `movement.read` OU `report.read`, usando o parâmetro alternativo do autorizador central. Assim Relatórios funciona sem liberar a navegação do Histórico. `GET /movement_users`, exclusivo do Histórico, exige `movement.read`; `GET /movements_summary` exige `report.read`.

Relatórios não reutiliza `/products` ou `/suppliers`, pois esses endpoints retornam dados do cadastro e exigem grants operacionais. O novo `GET /report_options` exige `report.read`, recebe `kind=product|supplier`, pagina os dados e retorna somente IDs e campos mínimos de identificação usados nos filtros. Isso mantém o contrato de relatório completo sem conceder `product.read` ou `supplier.read`.

O catálogo guarda `movement.read` (`resource=movement`, `action=read`) e `report.read` (`resource=report`, `action=read`) na tabela existente `inventory_permission`, provisionada por `Inventory/seed_initial_data`. Os grants default serão adicionados para `stockkeeper` e `read_only`, pois ambos têm `stock.read` no baseline local; assim o baseline preserva o acesso anterior. Em produção, antes de qualquer execução do seed ou publicação, revisar a matriz atual e conceder cada novo grant apenas a perfis que atualmente possuem `stock.read`, sem remover grants existentes. Esta change não executa seed nem migração de dados.

A extensão de `/auth/me` é estritamente de leitura e só expõe os códigos efetivos do próprio usuário autenticado. Nenhum endpoint administrativo ou tabela de grants fica acessível ao usuário comum.
