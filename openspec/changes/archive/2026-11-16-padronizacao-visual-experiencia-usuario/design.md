# Design: padronização visual e experiência do usuário

## Abordagem

Reutilizar a paleta e os estilos compartilhados de `Meu_projeto/components/theme.py`. Um componente Reflex comum recebe título, mensagem, estado aberto e evento de fechamento; os estados das páginas controlam sua abertura somente após validarem a resposta da operação existente.

Os handlers permanecem responsáveis por autenticação, autorização, validação, chamadas ao cliente Xano, reconciliação e invalidação de cache. A mudança apenas transforma o feedback de sucesso já confirmado em uma apresentação modal. Erros e resultados ambíguos continuam em seus estados atuais e nunca abrem confirmação de sucesso.

## Formulários e justificativas

Os formulários existentes recebem largura máxima adequada ao contexto, centralização na área de conteúdo, grids responsivos quando os campos forem independentes e botões dimensionados pelo conteúdo. Nenhum campo, binding, validação ou payload será alterado.

Os diálogos de cancelamento e justificativa mantêm campos obrigatórios, confirmação explícita e bloqueios durante a operação. O texto explica o efeito de negócio em linguagem direta. Mensagens de falha continuam visíveis e diferenciadas.

## Movimentações de estoque

Após confirmação de entrada ou saída pelo serviço atual, o resumo mostra tipo, produto, quantidade e unidade a partir dos valores submetidos e da resposta validada. O saldo final só é apresentado quando a resposta confiável contiver esse campo; não será inferido no cliente.

## Recuperação de senha demonstrativa

A rota `/recuperar-senha` valida localmente o preenchimento e o formato do e-mail, descarta o valor após a validação e apresenta um modal de confirmação com retorno explícito ao login. Trata-se somente de uma demonstração visual: não consulta usuários, não envia e-mails, não gera tokens, não armazena solicitações e não altera senhas. Não há integração com Xano ou serviço de e-mail.

## Validação

Testes locais com clientes remotos mockados verificam que somente resultados confirmados abrem o modal, falhas não o abrem, as mensagens e dados de movimentação não são presumidos, e os campos/bindings existentes permanecem. A compilação Reflex confirma a composição dos componentes, mas não comprova comportamento no Xano publicado nem substitui a aceitação manual registrada em `qa-visual.md`.
