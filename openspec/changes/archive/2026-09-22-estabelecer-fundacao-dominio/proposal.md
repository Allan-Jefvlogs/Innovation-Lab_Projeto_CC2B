# Proposal

## Why

O projeto possui uma visão de negócio e um modelo conceitual, ainda não possui uma definição de como as regras fundamentais do domínio de estoque devem funcionar. Sem essa fundação, o frontend Reflex e o backend Xano podem evoluir com nomes, estados, relacionamentos e contratos incompatíveis, aumentando o retrabalho nas mudanças de autenticação, cadastros e movimentações.

Esta mudança estabelece o vocabulário e os contratos comportamentais mínimos que as próximas changes deverão respeitar.


## What Changes

- Definir as entidades canônicas do domínio inicial: usuário, perfil, categoria, produto, fornecedor, estoque e movimentação de estoque.
- Definir os relacionamentos e estados relevantes para produtos, estoque e movimentações.
- Estabelecer regras conceituais de integridade para identificar o usuário responsável e preservar a consistência da quantidade disponível.
- Definir o contrato mínimo de integração entre o frontend Reflex e as APIs do Xano, incluindo autenticação de chamadas, respostas de sucesso e erros de validação/autorização.
- Registrar limites claros para que autenticação detalhada, gerenciamento de permissões, cadastros, operações de estoque, dashboard e relatórios sejam implementados em changes posteriores.

## Capacidades

### Novas Capacidades

- `domain-foundation`: vocabulário canônico, relacionamentos, estados e contratos comportamentais compartilhados pelo sistema de gerenciamento de estoque.

### Capacidades Modificadas

- Nenhuma.

## Impact

**OpenSpec:** cria a primeira capability consolidada para orientar as próximas changes.
- **Xano:** servirá como autoridade para persistência, validações e regras de negócio; as estruturas demonstrativas existentes deverão ser avaliadas antes de serem reutilizadas.
- **Reflex:** deverá consumir os contratos definidos sem duplicar regras de autorização ou integridade no frontend.
- **Autenticação e autorização:** serão dependências posteriores, mas o contrato desta change deverá reservar os pontos necessários para identidade e permissões.
- **Estoque e movimentações:** dependerão desta base para definir operações de entrada, saída, histórico e atualização consistente da quantidade.
- **Fora do escopo:** implementação de código, criação de tabelas ou endpoints Xano, telas Reflex, login completo, matriz final de permissões, dashboard e relatórios.