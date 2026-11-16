# Alteração voluntária da própria senha — revisão local

## Reutilização e escopo

Já existiam `/conta/alterar-senha`, o menu Alterar senha, AccountPasswordState, `auth_client.change_password`, o PATCH local `api/authentication/auth/change_password_PATCH.xs` e a flag `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED=false`. A troca inicial obrigatória `/alterar-senha` e `auth/change-initial-password` permanece separada e inalterada. A implementação foi completada nesses arquivos, sem criar outro endpoint ou alterar o menu, AuthState, schemas, permissões ou funcionalidades já validadas.

Todos os perfis ativos e autenticados podem trocar a própria senha, sem grant administrativo ou de compras. O usuário em troca inicial obrigatória é direcionado ao fluxo existente. A flag continua desabilitada por padrão e não foi alterada no ambiente; não habilitar antes da publicação e revisão de segurança.

## Autenticação observada no código

O login carrega user por email, usa `security.check_password` e emite `security.create_auth_token` para user.id, extras vazio e expiration 86400 segundos. O Reflex armazena o token em LocalStorage e valida a sessão por auth/me antes de liberar acesso. `user.password` é do tipo nativo password, internal, com filtros min:8/minAlpha:1/minDigit:1. Nenhuma alteração desses objetos foi feita.

A documentação oficial descreve tokens nativos Xano como JWE, não um JWT legível que o frontend deva decodificar. O projeto frequentemente usa o termo JWT para esses tokens. Fontes: https://docs.xano.com/building-backend-features/user-authentication-and-user-data.md e https://docs.xano.com/the-function-stack/functions/security.md . Não há interpretação de token nem mudança criptográfica nesta entrega.

## Contrato do PATCH

Grupo Authentication, canonical local DipsnlZk. `PATCH /auth/change-password`, autenticação user obrigatória. Entradas obrigatórias: current_password, password, confirm_password, todas sensitive. Nenhum user_id aceito para escolher o alvo; consulta e edição usam `$auth.id`.

Antes de editar, o script verifica confirmação, regex existente de oito caracteres/letra ASCII/número, existência/atividade do usuário, ausência de troca inicial pendente e hash disponível. Valida a senha atual com `security.check_password`. Outro check nativo compara a senha nova ao mesmo hash e rejeita igualdade. Uma única operação db.edit grava password no campo do tipo password, cujo hash é gerenciado pelo Xano; não há hash manual no Python nem armazenamento em coluna text. O resultado intermediário de edição é limitado a id e a resposta pública é somente `{senha_atualizada: true}`.

Erros previstos: 401 do autenticador para sessão inválida; 400 para confirmação, política, senha atual incorreta e senha repetida; 403 para conta inativa/fluxo inicial obrigatório; 500 para falha interna ou edição não confirmada. Senha atual incorreta antes era 403 local: o cliente reconhece também a categoria legada sem confundi-la com sessão expirada. O código de domínio é sanitizado e não contém valores enviados. Comportamento HTTP/importador ainda precisa de validação publicada.

Não há auditoria, histórico comercial, e-mail ou chamadas externas. Uma única edição de senha não exige outra transação envolvendo tabelas adicionais. Não são prometidas propriedades de runtime a partir de testes estruturais.

## Interface e limpeza

O formulário mantém o cartão existente e acrescenta labels, três campos mascarados, controles Mostrar/ocultar com aria-pressed, botão Alterar senha e Cancelar. Não usa State para senhas nem on_change para enviar cada tecla. Valores existem temporariamente no submit; o dicionário recebido é esvaziado e as referências locais são liberadas ao sair do handler. `reset_on_submit=True` limpa o DOM inclusive em erro de validação; será necessário redigitar as senhas. Cancelar reseta o DOM e volta à página inicial do perfil, sem chamada de escrita. Autocomplete é desabilitado, mas extensões/gerenciadores externos podem ignorar essa preferência do navegador.

O handler bloqueia duplo envio, respeita 429 e não executa retries. Falha/timeout podem ser ambíguos: não concluir sucesso nem repetir automaticamente; orientar login com a nova senha antes de tentar novamente. Só confirmação booleana true dispara AuthState.complete_password_change, já existente, que limpa sessão/cache locais e apresenta aviso de sucesso no login. Se a sessão mudar durante a chamada, não deslogar a nova identidade.

## Logs, Request History e debugger

### Estado operacional reportado após publicação — 2026-11-14

O usuário confirmou no painel que `Request History` está `Disabled` exclusivamente para `PATCH /auth/change-password` e que `current_password`, `password` e `confirm_password` estão marcados como dados sensíveis. Também informou que o fluxo foi testado com uma conta dedicada e funcionou. Esta confirmação não foi repetida nesta revisão documental.

Essas configurações não comprovam mascaramento em Error Logs, Run & Debug, middleware, extensões ou outras ferramentas de observabilidade. Não usar o debugger com senhas reais e não declarar proteção abrangente dos logs. A flag `NEXSTOCK_ACCOUNT_PASSWORD_ENABLED` permanece desligada por padrão e só é habilitada pelo launcher local explícito; ativação permanente ainda depende de decisão e revisão operacional.

O cliente omite chaves do objeto, mensagem e payload nas linhas de log desse endpoint. Códigos são limitados a categorias conhecidas e exceções sensíveis não produzem traceback bruto. O método público remove payloads das exceções e retorna apenas a confirmação; respostas inválidas não geram sucesso. Isso é testado com respostas simuladas que ecoam senhas em mensagem/payload e com JSON inválido.

As entradas sensitive e a visibilidade internal são necessárias, mas não comprovam todas as formas de captura do Xano. O estado atual de Request History foi confirmado pelo usuário como Disabled apenas para este endpoint, sem alteração do padrão global da branch. Conferir também Error Logs, middleware e ferramentas de observabilidade que possam capturar dados. Não usar Run & Debug, cURL exportado ou gravações de tráfego com credenciais reais. Desativar Request History não desativa o debugger. Não se declara garantia global de mascaramento de logs remotos.

Fonte oficial para configuração por objeto e reexecução pelo debugger: https://docs.xano.com/maintenance-monitoring-and-logging/request-history.md . Não foi adicionada propriedade XS de history sem confirmar o contrato da CLI/importador.

## Sessões: limite explícito

Não foram encontradas tabelas/versões de sessão, denylist ou chamadas de revogação nos scripts locais. O endpoint não revoga tokens. Encerrar LocalStorage/cache só encerra este navegador; tokens anteriores de outras sessões podem permanecer válidos até expirar. A emissão local tem duração de 24 horas; não se comprovou o comportamento nativo após trocar senha no workspace publicado.

A menor evolução estrutural plausível para invalidar outras sessões seria um campo de versão/marco por usuário, gravado no token ao autenticar e validado em todas as APIs protegidas. Isso exige revisar login, auth/me, helpers e endpoints que não usam o helper, e definir o tratamento de tokens antigos. Não basta consultar esse campo apenas em auth/me ou limpar LocalStorage. Essa evolução não foi implementada nem aprovada implicitamente nesta entrega. Nenhum schema ou mecanismo de autenticação foi substituído.

O Free pode aplicar limites de requisição e o coordenador local os preserva. Não há lockout durável por usuário implementado para várias senhas atuais incorretas; o cooldown local não protege chamadas diretas à API. Rate limiting por identidade no backend exige análise separada dos recursos efetivos do plano, sem presumir Redis disponível nem bloquear contas reais automaticamente. Esse risco permanece documentado para uso além da demonstração controlada.

## Comparação remota e publicação seletiva futura

A última exportação disponível em `nexstock-dashboard-atual-19e4787461234159a4224c738893a9f3` é de 12/11/2026 e não contém auth/change-password. Isso indica objeto novo naquela fotografia, não ausência no workspace atual. Os endpoints e schemas reais podem ter mudado depois.

Ao tentar consultar `xano.cmd workspace pull --help` nesta revisão, a CLI falhou com `uv_os_get_passwd returned ENOMEM`. Não foram repetidas tentativas, obtida nova exportação nem executados previews. A comparação com a exportação remota atual permanece bloqueada; não usar o backup antigo para sobrescrever trabalho recente.

Ordem segura, mediante autorização futura:

1. Exportar definições atuais de workspace 152211/branch v1 para pasta temporária externa ao projeto, sem registros/variáveis; comparar o endpoint por query + verb, não somente nome de arquivo. Conferir o tipo password real e o grupo Authentication. Não publicar tabelas.
2. Revisar a configuração de logs/middleware do endpoint e resolver eventual captura de segredos.
3. Executar preview somente do PATCH:

```powershell
xano.cmd workspace push --workspace 152211 --branch v1 --directory xano --include "api/authentication/auth/change_password_PATCH.xs" --no-guids --no-fast --no-writeback --dry-run
```

4. Publicar exclusivamente o endpoint após preview aprovado, preservando uma cópia atual para recuperação de código. Nenhum provisionamento ou grant é necessário.
5. A configuração específica de Request History e os campos sensíveis foram posteriormente confirmados pelo usuário. A flag permanece false nos arquivos e é habilitada somente pelo processo local explícito; essa ativação temporária não deve ser confundida com ativação permanente.

## Teste funcional reportado com conta dedicada e verificações restantes

O usuário informou que testou a alteração em conta dedicada: logout automático, login com a nova senha e rejeição da senha anterior funcionaram. Nenhuma senha foi compartilhada nesta revisão. Essa confirmação não substitui testes de todas as validações de entrada nem demonstra revogação de tokens em outras sessões.

Uma eventual verificação de sessão antiga deve usar apenas a conta de demonstração e um GET autorizado, sem copiar tokens para logs. Não interpretar logout local como revogação. Antes de qualquer novo teste com senha, confirmar que a observabilidade remota não captura os campos sensíveis; não usar Run & Debug com credenciais reais. Se houver timeout da alteração, testar login com a nova senha antes de qualquer repetição. Recuperação de conta deve seguir o procedimento administrativo existente, sem alterar contas de terceiros ou editar hashes manualmente.

Repetir a validação dos guards com contas de teste dos perfis necessários somente após autorização; testes locais já cobrem os quatro perfis com mocks. Nenhuma senha real, token remoto, cadastro, compra ou estoque foi modificado nesta entrega.

## Validações locais concluídas

121 testes direcionados/regressivos aprovados, abrangendo senha, autenticação, sessão, contratos do Dashboard, navegação por notificações e coordenador. PATCH válido no Xano Developer MCP; Reflex compile --dry e OpenSpec strict aprovados. Os testes de backend são estruturais e usam documentação do mecanismo nativo; os testes HTTP/state usam mocks. Não comprovam o hash persistido, respostas do importador/runtime, mascaramento remoto ou revogação de tokens no workspace live.
