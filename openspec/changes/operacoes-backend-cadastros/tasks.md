# Tasks

## 1. Preparar e confirmar escopo de implementação

- [x] 1.1 Conferir a Specification desta change com `design.md`, a proposal aprovada e as specifications consolidadas de autenticação, domínio, cadastros básicos, fundação técnica e movimentação de estoque.
- [x] 1.2 Inspecionar os schemas Xano locais de `user`, `category`, `product` e `supplier` e confirmar que os campos/índices existentes correspondem aos contratos da Specification.
- [x] 1.3 Confirmar os nomes de tabelas, função compartilhada, grupo/canonical e convenções de arquivos XanoScript já descritos no Design antes de implementá-los.
- [x] 1.4 Confirmar que `members_accounts` e `admin/user_role` permanecem fora do helper de autorização do estoque e usam `admin/member` legado.

## 2. Criar perfis, catálogo e grants iniciais

- [x] 2.1 Criar a tabela de perfil com códigos únicos `administrator`, `stockkeeper` e `read_only`, nomes de exibição e `permission_revision` iniciado em `1`.
- [x] 2.2 Criar o catálogo controlado com os doze códigos de permissão de Categoria, Produto e Fornecedor.
- [x] 2.3 Criar a tabela de grants com referências obrigatórias e unicidade composta por perfil e permissão.
- [ ] 2.4 Semear os três perfis, o catálogo e a matriz inicial aprovada para Almoxarife e Auxiliar.
- [x] 2.5 Implementar o acesso integral implícito de `administrator`, sem grants mutáveis para o Líder.
- [ ] 2.6 Verificar persistência da matriz, unicidade de grants e idempotência/segurança da rotina de provisionamento inicial.

## 3. Associar usuários autenticados a perfis

- [x] 3.1 Adicionar `user.inventory_profile_id` como referência nullable ao perfil, preservando `user.role` quick-start sem conversão automática.
- [x] 3.2 Garantir que endpoints protegidos rejeitem vínculo ausente, inexistente ou inválido antes de acessar dados de cadastro.
- [x] 3.3 Garantir que signup não aceite `inventory_profile_id` nem `profile_code` fornecido pelo usuário.
- [x] 3.4 Implementar `PATCH /users/by_id/{user_id}/profile`, acessível apenas ao Líder, com validação do alvo e dos três códigos de perfil.
- [x] 3.5 Impedir que o Líder altere o próprio perfil e validar atribuição manual a usuários existentes e novos.
- [x] 3.6 Implementar bootstrap interno de uso único do primeiro `administrator`, com usuário alvo explícito, transação e marcador singleton único; não expor endpoint HTTP.
- [x] 3.7 Documentar o bootstrap como exceção controlada para criar somente o primeiro Líder: execução por operador confiável do workspace após confirmação de identidade, bloqueio de execuções posteriores e atribuição normal exclusiva do Líder depois do bootstrap.
- [ ] 3.8 Testar bootstrap concorrente, rejeição de segunda execução, ausência de endpoint público e atribuição inicial a usuário não atribuído.
- [ ] 3.9 Testar perfis válidos/inválidos, tentativas por não-Líder, autoalteração, perfil desconhecido, signup com campo forjado e usuário sem perfil.

## 4. Implementar autorização central do estoque

- [x] 4.1 Implementar função compartilhada que recebe o código de permissão, resolve perfil via `$auth.id`/`user.inventory_profile_id` e falha fechada para usuário sem vínculo válido.
- [x] 4.2 Implementar bypass integral de `administrator` apenas para funcionalidades do Sistema de Gerenciamento de Estoque.
- [x] 4.3 Para Almoxarife e Auxiliar, exigir grant persistido exato antes de qualquer leitura ou escrita protegida.
- [x] 4.4 Manter permissões fora do token e resolver o estado persistido em cada requisição autenticada.
- [x] 4.5 Definir e implementar envelopes/códigos estáveis para autenticação, perfil ausente/inválido, autorização, validação, regra de negócio, não encontrado, duplicidade e conflito de revisão.
- [ ] 4.6 Testar as 36 combinações da matriz inicial, bypass do Líder, revogação efetiva no próximo uso do mesmo token e ausência de grants implícitos.

## 5. Implementar consulta, alteração e auditoria de permissões

- [x] 5.1 Implementar `GET /permissions`, somente para Líder, retornando catálogo, matriz efetiva e revisões.
- [x] 5.2 Implementar `PATCH /permissions/profiles/{profile_code}` com lista completa de grants, revisão esperada e alvos limitados a `stockkeeper` e `read_only`.
- [x] 5.3 Aceitar `permissions: []`; rejeitar perfil Líder, perfil/código desconhecido, permissão duplicada e revisão obsoleta sem alteração parcial.
- [x] 5.4 Atualizar grants e `permission_revision` atomicamente com transação e proteção contra sobrescrita concorrente usando índice único de auditoria por perfil/revisão anterior.
- [x] 5.5 Criar tabela append-only `inventory_permission_audit` com ator, perfil alvo, revisão anterior/nova e códigos adicionados/removidos.
- [x] 5.6 Gravar auditoria na mesma transação dos grants; reverter grants e revisão se o registro de auditoria falhar.
- [x] 5.7 Não criar endpoint para consultar, editar ou apagar auditoria nesta change.
- [ ] 5.8 Testar acesso exclusivo do Líder, substituição total/vazia, conflito de versão, atomicidade, rollback e conteúdo dos eventos confirmados.

## 6. Implementar endpoints de Categoria

- [x] 6.1 Implementar `GET /categories` com `category.read`, filtro opcional de status e paginação/ordenação comuns.
- [x] 6.2 Implementar `GET /categories/by_id/{category_id}` com `category.read` e erro estável para ID inexistente.
- [x] 6.3 Implementar `POST /categories` com `category.create`, campo obrigatório `nome`, status inicial ativo e retorno do registro criado.
- [x] 6.4 Implementar `PATCH /categories/by_id/{category_id}` com `category.update`, permitindo somente `nome` e PATCH não vazio.
- [x] 6.5 Implementar `PATCH /categories/by_id/{category_id}/inactivate` com `category.inactivate`, idempotente e sem exclusão física.
- [ ] 6.6 Testar perfis autorizados/negados, validação, duplicidade, detalhe, filtros, paginação, inativação e preservação de referências.

## 7. Implementar endpoints de Produto

- [x] 7.1 Implementar `GET /products` e `GET /products/by_id/{product_id}` com `product.read`, filtros de status/categoria e paginação/ordenação comuns.
- [x] 7.2 Implementar `POST /products` com `product.create`, campos obrigatórios aprovados, descrição opcional, status inicial ativo e sem aceitar ID/status/estoque atual do cliente.
- [x] 7.3 Validar na criação que `categoria_id` identifica Categoria existente e ativa.
- [x] 7.4 Implementar `PATCH /products/by_id/{product_id}` com `product.update` e lista permitida de campos mutáveis.
- [x] 7.5 Validar Categoria ativa somente quando uma nova associação/troca de `categoria_id` for solicitada; permitir outros PATCHes preservando referência existente a Categoria inativa.
- [x] 7.6 Implementar `PATCH /products/by_id/{product_id}/inactivate` com `product.inactivate`, preservando produto e referências.
- [x] 7.7 Implementar `limpar_descricao` no PATCH de Produto, rejeitar valor direto nulo pela entrada não anulável, rejeitar combinação conflitante e limpar somente quando a flag for `true`.
- [ ] 7.8 Testar perfis autorizados/negados, campos, categoria ausente/inativa, reassociação válida, unicidade, paginação, inativação e preservação histórica.
- [ ] 7.9 Testar omissão, atualização não nula, limpeza explícita, nulo rejeitado, combinação conflitante e flag falsa sem valor em PATCH de Produto.

## 8. Implementar endpoints de Fornecedor

- [x] 8.1 Implementar `GET /suppliers` e `GET /suppliers/by_id/{supplier_id}` com `supplier.read`, filtros de status/tipo de documento e paginação/ordenação comuns.
- [x] 8.2 Implementar `POST /suppliers` com `supplier.create`, campos obrigatórios, enum CPF/CNPJ, opcionais aprovados e status inicial ativo.
- [x] 8.3 Implementar `PATCH /suppliers/by_id/{supplier_id}` com `supplier.update` e apenas os campos mutáveis aprovados.
- [x] 8.4 Implementar `PATCH /suppliers/by_id/{supplier_id}/inactivate` com `supplier.inactivate`, preservando registro e referências.
- [x] 8.5 Implementar `limpar_contato` e `limpar_endereco` no PATCH de Fornecedor, rejeitar valores diretos nulos pela entrada não anulável e rejeitar combinações conflitantes.
- [ ] 8.6 Testar perfis autorizados/negados, campos, unicidade de `documento`, filtros, paginação e inativação sem exclusão física.
- [ ] 8.7 Testar omissão, atualização não nula, limpeza explícita, nulo rejeitado, combinação conflitante e flags falsas sem valores em PATCH de Fornecedor.

## 9. Aplicar contratos transversais e limites de domínio

- [x] 9.1 Aplicar paginação padrão `page=1`, `per_page=20`, limite `100`, ordenação estável por ID e envelope Xano especificado em todas as listagens.
- [x] 9.2 Confirmar que listas sem filtro de status incluem registros ativos e inativos e que filtros aceitam somente valores válidos.
- [x] 9.3 Aplicar unicidade pelos valores armazenados em `category.nome`, `product.codigo` e `supplier.documento`, sem trim, conversão de caixa, remoção de pontuação ou validação extra de CPF/CNPJ.
- [ ] 9.4 Traduzir conflitos dos índices únicos para `DUPLICATE_VALUE`, mantendo a constraint persistente como proteção contra concorrência.
- [ ] 9.5 Confirmar que PATCH genérico não altera ID/status, rejeita corpo sem alteração efetiva e implementa limpeza dos opcionais aprovados pelas flags explícitas; confirmar envelope de rejeição para null direto.
- [x] 9.6 Confirmar ausência de DELETE/remoção física e inativação exclusivamente por alteração para `inativo`.
- [x] 9.7 Verificar que operações de cadastro, atribuição de perfil e grants não alteram saldo, estruturas de estoque ou movimentações.
- [x] 9.8 Verificar que `members_accounts` e `admin/user_role` seguem usando `admin/member` e não ganham bypass de Líder.

## 10. Validar XanoScript e executar testes backend

- [x] 10.1 Validar pelo Xano Developer MCP cada novo arquivo XanoScript em escopo: tabelas, grupo, endpoints e funções compartilhadas.
- [x] 10.2 Corrigir erros do validador nos arquivos desta change e repetir a validação; não ampliar o escopo para corrigir o erro preexistente em `xano/workspace/meu_espaco.xs`.
- [ ] 10.3 Executar unit tests das funções de autorização, validação e atualização da matriz.
- [ ] 10.4 Executar workflow tests para endpoints e cenários de aceitação em datasource isolado de teste, sem usar datasource live.
- [ ] 10.5 Testar duplicidades concorrentes, atomicidade de grants/auditoria, efeito imediato de alteração de permissão e ausência de efeitos em estoque.
- [x] 10.6 Revisar especificação, cobertura de cenários e diff dos artefatos da change; não executar sincronização nem Archive nesta change.

## Apply review execution notes

- `Inventory/bootstrap_first_leader` e `inventory_bootstrap_state` foram criados e validados estaticamente; a função não foi executada porque os artefatos não foram sincronizados ao workspace.
- A proteção concorrente de grants usa índice único de auditoria por (`target_profile_id`, `revision_before`) e rollback transacional; o parser MCP validou os arquivos, mas a concorrência real permanece sem workflow test.
- Os handlers de unicidade fazem pre-check, capturam falhas de escrita e só mapeiam para `DUPLICATE_VALUE` quando uma consulta confirma outro registro com o mesmo valor. Essa rota real da constraint ainda aguarda teste de execução.
- O contrato atualizado usa inputs de valor opcionais não anuláveis e flags booleanas explícitas para limpeza; não usa sentinelas nem exige distinguir ausência de null em input nullable. Os testes de execução desse contrato permanecem pendentes.
- O bootstrap está documentado como exceção apenas para provisionar o primeiro Líder; depois do marcador único, toda atribuição de perfil é exclusiva da operação protegida pelo Líder, sem endpoint ou caminho de autoelevação permanente.
- Nesta tentativa, `xano unit_test list -o json` e `xano workflow_test list -o json` foram bloqueados pelo PowerShell porque a execução de `xano.ps1` está desabilitada pela política local. Invocando `xano.cmd unit_test list -o json` e `xano.cmd workflow_test list -o json`, ambos falharam com `uv_os_get_passwd returned ENOMEM`. Não foi possível inspecionar os testes nem confirmar datasource isolado; por isso nenhum comando `run` ou `run_all` foi iniciado e nenhum teste foi executado ou simulado.
