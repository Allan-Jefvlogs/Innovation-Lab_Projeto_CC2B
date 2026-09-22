<!-- reflex managed begin (do not edit inside this block; add custom content outside the markers) -->
# Agents

This project uses the **Reflex agent skills** � up-to-date knowledge for building full-stack Python web apps with [Reflex](https://reflex.dev). Install them first, then use them as described below.

## Installing the Skills

Before working on this project, make sure the Reflex skills are available to you.

### Claude Code

If the skills are not already available, install them yourself by running these shell commands:

```bash
claude plugin marketplace add reflex-dev/agent-skills
claude plugin install reflex@reflex-agent-skills
```

Newly installed plugins load on the next session. After installing, tell the user to restart the session so the skills auto-load; until then, read the skill files directly from `~/.claude/plugins/` when you need them.

### Other agents (Cursor, OpenCode, Codex, Pi)

```
npx skills add reflex-dev/agent-skills
```

Or clone https://github.com/reflex-dev/agent-skills and copy the `skills/` folders into your agent's skill directory (see the repo README for paths).

### Verifying

Before writing or editing any Reflex code, confirm these three skills are available: `reflex-docs`, `setup-python-env`, and `reflex-process-management`. If they are not, STOP and run the install step above � do not proceed without them.

## Using the Skills

### Reflex documentation

For anything about Reflex APIs � components, state management, events, styling, database, routing, authentication � use the **reflex-docs** skill rather than relying on memory. It carries current, version-accurate docs.

### Initializing a new Reflex project

When starting a new Reflex project or setting up a development environment, you **must** follow the **setup-python-env** skill before doing anything else.

Do not skip any steps. Do not assume a virtual environment or Reflex is already available � always verify first by following the skill's instructions in order.

After the environment is ready and Reflex is installed, run:

```bash
reflex init
```

Then proceed with the user's request.

### Managing a Reflex process

When you need to compile, run, reload, or debug a Reflex application, follow the **reflex-process-management** skill for the correct sequence and error investigation steps.
<!-- reflex managed end -->
# Regras do Projeto — Sistema de Gerenciamento de Estoque

## 1. Contexto do projeto

Este projeto consiste em um Sistema de Gerenciamento de Estoque destinado ao controle de produtos e movimentações de estoque de uma empresa.

O sistema possui como principais áreas:

- autenticação e acesso de usuários;
- perfis e permissões;
- categorias;
- produtos;
- fornecedores;
- estoque;
- entradas de estoque;
- saídas de estoque;
- histórico de movimentações;
- dashboard;
- relatórios.

Consulte `docs/project-overview.md` para a visão geral do projeto e `docs/domain-model.md` para o modelo conceitual do domínio.

## 2. Arquitetura

- O frontend deve ser implementado exclusivamente com Reflex.
- O backend deve utilizar Xano.
- Não introduzir outra tecnologia de frontend sem uma alteração arquitetural explicitamente aprovada pelo grupo.
- Respeitar as decisões arquiteturais registradas na documentação do projeto.

## 3. Documentação

Antes de realizar alterações significativas:

1. consultar `docs/project-overview.md`;
2. consultar `docs/domain-model.md`;
3. consultar `openspec/config.yaml`, quando já estiver disponível;
4. considerar as especificações e changes existentes do OpenSpec.

Não duplicar indiscriminadamente nos arquivos de contexto informações que já estejam documentadas em outros arquivos.

## 4. OpenSpec

- Mudanças relevantes no sistema devem utilizar OpenSpec.
- Não implementar funcionalidades grandes diretamente sem passar pelo processo de especificação correspondente.
- Antes de implementar uma mudança, analisar seu escopo, dependências e impactos.
- Respeitar o ciclo de desenvolvimento definido pelo projeto:
  Explore → Propose → Review → Apply → Archive.
- Não criar ou alterar especificações para justificar uma implementação já realizada sem revisar o processo.

## 5. Xano e XanoScript

- O Xano é o backend do projeto.
- Utilizar o Xano Developer MCP para consultar documentação e validar XanoScript quando necessário.
- Não presumir sintaxe de XanoScript quando houver dúvida.
- Consultar a documentação atual do Xano antes de implementar funcionalidades relacionadas ao backend.
- Utilizar o Xano CLI para sincronização entre os arquivos locais e o workspace Xano.
- Não realizar alterações destrutivas no workspace sem revisão e confirmação apropriadas.

## 6. Frontend com Reflex

- Utilizar exclusivamente os mecanismos próprios do Reflex para componentes, páginas, estado, eventos e navegação.
- Consultar as Agent Skills do Reflex quando a tarefa envolver APIs, componentes, State, eventos, roteamento, configuração ou execução da aplicação.
- Não introduzir React, Vue, Angular, Streamlit, Next.js ou outro framework de frontend para substituir ou complementar o Reflex sem aprovação arquitetural explícita.
- Manter a estrutura gerada pelo Reflex, alterando-a somente quando houver necessidade justificada.

## 7. Regras de negócio e segurança

- As regras de autorização devem ser aplicadas no backend.
- A interface frontend não deve ser considerada mecanismo suficiente de segurança.
- Usuários somente devem acessar funcionalidades compatíveis com seus perfis e permissões.
- Toda movimentação de entrada ou saída deve identificar o usuário responsável.
- Uma saída de estoque não deve resultar em quantidade de estoque negativa.
- Alterações que possam comprometer a integridade dos dados devem ser analisadas antes da implementação.

## 8. Código

- Reutilizar código existente quando apropriado.
- Evitar duplicação desnecessária.
- Não modificar funcionalidades não relacionadas à mudança atual sem justificativa.
- Seguir os padrões já utilizados no projeto.
- Preferir soluções simples e coerentes com a arquitetura existente.
- Não introduzir dependências desnecessárias.

## 9. Testes e validação

Toda mudança funcional deve possuir uma estratégia de verificação.

Antes de considerar uma alteração concluída:

- validar o comportamento implementado;
- verificar erros de sintaxe e execução;
- revisar as alterações realizadas;
- verificar possíveis impactos em funcionalidades relacionadas.

Quando a mudança envolver XanoScript, utilizar os recursos apropriados de validação e documentação.

## 10. Git

Antes de realizar um commit:

1. executar `git status`;
2. revisar as alterações com `git diff`;
3. confirmar que somente as alterações relacionadas à mudança atual serão registradas.

Os commits devem possuir mensagens claras e relacionadas ao objetivo da alteração.

Não versionar credenciais, tokens, segredos ou ambientes virtuais.

## 11. Comportamento esperado do agente

O agente deve:

- analisar o contexto antes de implementar;
- fazer perguntas ou solicitar esclarecimentos quando uma decisão importante não estiver definida;
- apresentar riscos ou impactos relevantes antes de realizar alterações significativas;
- evitar assumir decisões arquiteturais sem justificativa;
- não implementar funcionalidades fora do escopo da mudança atual;
- manter documentação, código e especificações coerentes entre si.

O agente deve tratar a Inteligência Artificial como assistente de desenvolvimento. As decisões finais do projeto permanecem sob responsabilidade do nosso grupo.