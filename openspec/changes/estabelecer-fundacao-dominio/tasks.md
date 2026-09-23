# Tasks

## 1. Consolidar o contrato de domínio

- [x] 1.1 Revisar os conceitos, relacionamentos, estados e invariantes descritos em `specs/spec.md` com o modelo de domínio do projeto e verificar que cada requisito possui cenários observáveis.

- [x] 1.2 Definir um glossário e uma convenção de nomes para os conceitos e tipos de movimentação, verificando que não há conflito com as próximas capabilities previstas.

## 2. Preparar as orientações para o Xano

- [x] 2.1 Registrar as orientações conceituais para futura modelagem no Xano, considerando entidades, relacionamentos, estados e dados necessários à rastreabilidade, sem definir ainda tabelas, endpoints ou schema físico definitivo.

- [x] 2.2 Consultar a documentação do Xano Developer MCP quando houver dúvida sobre conceitos ou recursos necessários às próximas changes, sem implementar XanoScript nesta change.

## 3. Estabelecer os contratos de integração

- [x] 3.1 Definir as categorias estruturadas de sucesso e de erro para autenticação, autorização, validação e regras de negócio, verificando que cada categoria pode ser distinguida sem depender de texto livre.

- [x] 3.2 Documentar os limites de responsabilidade entre Xano e Reflex, verificando que operações protegidas e regras de integridade permanecem aplicadas no backend.

## 4. Validar a fundação

- [x] 4.1 Revisar os cenários de quantidade, situação do estoque, responsável obrigatório e saída acima do disponível, verificando que cada comportamento esperado está claramente definido e que uma operação rejeitada não deve alterar o estado confirmado do estoque nem do histórico.

- [x] 4.2 Executar a validação da change e as verificações relevantes do projeto, corrigindo inconsistências entre `proposal.md`, `spec.md`, `design.md` e `tasks.md` antes de concluir o planejamento.