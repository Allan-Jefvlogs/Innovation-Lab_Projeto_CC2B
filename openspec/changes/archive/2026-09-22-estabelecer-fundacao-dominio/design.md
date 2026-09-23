# Design

## Context

O frontend atual é um esqueleto padrão do Reflex e o backend Xano contém estruturas de exemplo de autenticação e de outro domínio. Não há specs consolidadas nem entidades específicas do estoque. A implementação futura deve preservar a separação definida em `AGENTS.md`: Reflex para apresentação e interação, Xano para persistência, autorização, integridade e regras de negócio.

## Goals / Non-Goals

**Goals:**

- Criar uma linguagem de domínio estável para orientar as próximas changes.
- Definir uma fronteira clara entre apresentação e interação no Reflex e autoridade de negócio e integridade no Xano.
- Permitir que validações de estoque e respostas de erro sejam testadas independentemente da interface.
- Evitar que as estruturas Xano existentes sejam tratadas como modelo definitivo sem avaliação.

**Non-Goals:**

- Criar tabelas, endpoints ou componentes nesta change.
- Escolher uma matriz final de perfis e permissões.
- Implementar login, cadastros, entradas, saídas, dashboard ou relatórios.
- Definir detalhes de implantação, paginação ou tecnologia adicional.

## Decisions

### Xano será a autoridade de negócio e integridade

As decisões que alteram dados, autorizam operações ou calculam a situação do estoque serão realizadas no backend Xano. O Reflex poderá representar estados e oferecer validações de usabilidade, mas não poderá ser a única barreira para autorização ou integridade.

**Alternativa considerada:** duplicar as regras no frontend para reduzir chamadas. Essa opção foi rejeitada porque permite bypass por chamadas diretas ao backend e cria risco de divergência.

### O contrato será orientado a conceitos e comportamentos

A spec define entidades, relações, estados, erros e invariantes observáveis. O schema físico do Xano e a organização dos módulos Reflex serão decididos nas changes que implementarem cada capability.

**Alternativa considerada:** fixar nesta change todas as tabelas e endpoints. Essa opção foi rejeitada porque mistura contrato de negócio com decisões de implementação e dificultaria ajustes antes da primeira operação funcional.

### Movimentação será o registro auditável da alteração de estoque

Entradas e saídas serão tratadas como tipos de uma movimentação comum, com campos obrigatórios compartilhados e contexto específico por tipo. O registro deverá manter o responsável e os dados necessários para preservar a rastreabilidade da movimentação.

**Alternativa considerada:** manter entradas e saídas sem um conceito comum. Essa opção foi rejeitada porque duplicaria regras e dificultaria consultas de histórico e relatórios.

### Erros terão categorias identificáveis

As respostas de integração deverão distinguir autenticação, autorização, validação e regra de negócio por dados estruturados. O texto exibido ao usuário será responsabilidade do frontend, mas a causa operacional não dependerá de mensagens livres.

**Alternativa considerada:** usar somente mensagens textuais. Essa opção foi rejeitada porque torna o comportamento frágil para traduções, mudanças de texto e tratamento consistente na interface.

## Risks / Trade-offs

- **[Risco]** As estruturas Xano atuais podem ser confundidas com o modelo do estoque. **Mitigação:** tratar esta capability como contrato novo e avaliar explicitamente cada reutilização em changes posteriores.

- **[Risco]** Uma regra conceitual de estoque pode não ser suficiente para lidar com concorrência. **Mitigação:** a change de movimentações deverá definir como a atualização do estoque e o registro da movimentação serão tratados de forma consistente no Xano, incluindo as medidas necessárias para evitar inconsistências em operações concorrentes.

- **[Risco]** Categorias de erro inconsistentes entre endpoints. **Mitigação:** definir exemplos e validações do contrato na change de integração/autenticação antes de criar múltiplas telas.

- **[Trade-off]** Adiar o schema físico reduz decisões prematuras, mas exige uma etapa explícita de modelagem antes da implementação do backend. **Mitigação:** incluir essa modelagem como tarefa da primeira change de implementação que consumir esta fundação.