# Proposal

## Why

As specifications de cadastros básicos já definiram o contrato funcional de Categoria, Produto e Fornecedor, incluindo criação, consulta, alteração, inativação, relacionamentos e preservação da integridade histórica. O repositório, porém, ainda não possui uma fundação técnica de persistência para esses conceitos no Xano.

O projeto Reflex contém apenas páginas mockadas para categorias, produtos e fornecedores, sem estado persistido ou integração com backend. O diretório Xano contém principalmente estruturas de quick-start, autenticação, contas, logs e outro domínio, mas não possui entidades específicas dos cadastros básicos. A implementação futura precisa, portanto, estabelecer uma base física coerente antes da criação das operações de backend e da integração com o frontend.

Esta change propõe definir e implementar a fundação técnica de persistência para Categoria, Produto e Fornecedor no Xano, mantendo o Xano como autoridade de integridade e regras de negócio. A criação física ocorrerá somente no Apply, após a aprovação das decisões técnicas; Explore, Proposal e Review permanecem sem criação de estruturas.

O repositório contém 98 arquivos XanoScript existentes. A validação realizada no Explore identificou 97 arquivos válidos e um erro preexistente em `xano/workspace/meu_espaco.xs`. Esse erro não faz parte desta change e não deve ser corrigido sem decisão explícita.

## What Changes

- Definir a base técnica necessária para persistir Categoria, Produto e Fornecedor no Xano.
- Avaliar as entidades físicas correspondentes aos conceitos funcionais já consolidados.
- Definir, após revisão do grupo, quais campos conceituais precisam ser materializados.
- Definir as relações necessárias entre Produto e Categoria.
- Preservar a capacidade futura de relacionar Produto a Estoque e Movimentação.
- Preservar a relação contextual entre Fornecedor e entradas de estoque.
- Avaliar chaves, índices, unicidade e convenções de nomenclatura necessárias à persistência.
- Criar, no Apply, as estruturas físicas necessárias no Xano após aprovação das decisões sobre entidades, campos, tipos, chaves, índices, relacionamentos, status/inativação e unicidade.
- Definir uma estratégia técnica de ativo/inativo compatível com as specifications, sem transformar inativação em exclusão definitiva.
- Preservar referências históricas de registros já utilizados.
- Avaliar eventual isolamento por conta ou contexto organizacional, sem presumir que essa decisão já esteja definida.
- Estabelecer convenções para futura organização dos arquivos XanoScript.
- Validar a futura modelagem contra as specifications consolidadas antes de qualquer implementação de operações.
- Manter a compatibilidade com a autenticação/autorização existente, sem implementar autenticação nem redefinir permissões.

## Scope

### Incluído

- Definição e implementação, no Apply, da fundação física de persistência para Categoria.
- Definição e implementação, no Apply, da fundação física de persistência para Produto.
- Definição e implementação, no Apply, da fundação física de persistência para Fornecedor.
- Criação das estruturas físicas necessárias no Xano após aprovação das decisões sobre entidades, campos, tipos, chaves, índices, relacionamentos, status/inativação e unicidade.
- Definição dos relacionamentos necessários entre as entidades.
- Definição de chaves, índices e regras de unicidade.
- Definição da estratégia técnica de ativo/inativo.
- Avaliação da preservação de referências históricas.
- Avaliação da compatibilidade futura com Estoque e Movimentação.
- Avaliação da compatibilidade contextual entre Fornecedor e entradas de estoque.
- Definição das convenções de nomenclatura e organização dos arquivos XanoScript, após revisão do grupo.
- Validação da modelagem proposta contra as specifications consolidadas.
- Definição do uso futuro do Xano CLI e do Xano Developer MCP para validação e sincronização.

### Fora do escopo

- Implementação de operações de criação, consulta, alteração ou inativação.
- Criação de qualquer estrutura física antes do Apply aprovado; durante Explore, Proposal e Review nenhuma tabela, schema, campo, chave ou índice será criado.
- Criação de XanoScript durante Explore, Proposal ou Review; a criação ocorrerá somente no Apply após aprovação.
- Criação de endpoints ou APIs concretas.
- Sincronização do workspace Xano durante Explore, Proposal ou Review; qualquer sincronização no Apply deverá ocorrer somente após revisão e aprovação explícita.
- Integração com o frontend Reflex.
- Criação ou alteração de telas, componentes ou estados Reflex.
- Autenticação como implementação.
- Redefinição da matriz detalhada de permissões.
- Criação de novos perfis.
- Implementação de movimentação de estoque.
- Implementação de Estoque ou Histórico como operações independentes.
- Dashboard e relatórios.
- Vendas, pagamentos, notas fiscais e funcionalidades financeiras.
- Múltiplos depósitos ou filiais.
- Importação em massa.
- Integrações externas.
- Correção do erro preexistente em `xano/workspace/meu_espaco.xs`.
- Definição de política definitiva de exclusão.

## Impact

- **Cadastros básicos:** passam a ter uma base técnica planejada para futura persistência, sem alterar o contrato funcional consolidado.
- **Categoria:** deverá sustentar a organização dos Produtos e permitir a preservação da integridade quando houver Produtos relacionados.
- **Produto:** deverá manter referência à Categoria e permanecer compatível com futuras relações com Estoque e Movimentação.
- **Fornecedor:** deverá manter sua natureza contextual às entradas de estoque e preservar referências históricas quando aplicável.
- **Estoque futuro:** dependerá de uma representação de Produto que não impeça a associação posterior ao estado atual do estoque.
- **Movimentação futura:** dependerá da preservação da referência do Produto e da impossibilidade de destruir registros usados no histórico.
- **Autenticação/autorização:** a fundação técnica deverá ser compatível com a proteção backend já consolidada, mas não implementará autenticação, autorização ou permissões específicas.
- **Xano:** continuará como autoridade da persistência, integridade e regras de negócio; decisões técnicas deverão ser validadas antes de sincronização.
- **Reflex:** permanece inalterado nesta change e continuará mockado até uma change futura de integração.
- **Xano CLI:** poderá apoiar pull, validação, dry-run e futura sincronização, sem push nesta etapa.
- **Xano Developer MCP:** deverá apoiar consulta de documentação e validação de XanoScript quando a implementação for autorizada.
- **Git:** deverá versionar os artefatos técnicos futuros e permitir revisão antes de qualquer sincronização remota.

## Dependências

### Dependências funcionais

- A fundação do domínio define o vocabulário de Categoria, Produto, Fornecedor, Estoque e Movimentação.
- A specification de cadastros básicos exige Categoria válida para operação normal de Produto.
- Produto deve permanecer relacionável a Estoque e Movimentação.
- Fornecedor deve permanecer contextual às entradas de estoque.
- Registros já utilizados devem preservar sua integridade histórica.
- A exclusão definitiva permanece sujeita a decisão explícita e não deve ser presumida.

### Dependências de segurança

- A capability de autenticação/autorização exige usuário autenticado para operações protegidas.
- A autorização deverá ser aplicada no backend Xano.
- Esta change não define a matriz detalhada de permissões, mas a modelagem futura não deve impedir sua aplicação.
- Não devem ser criados novos perfis nesta change.

### Dependências técnicas

- Xano é o backend e a autoridade de persistência.
- Xano CLI está instalado na versão `1.3.0` e possui perfil local apontando para o workspace `152211`.
- O projeto possui MCP Xano configurado em `.vscode/mcp.json` usando `@xano/developer-mcp`.
- O diretório local `xano/` contém o snapshot atual de XanoScript e deve ser analisado antes de qualquer reutilização.
- O Reflex utiliza a versão `0.9.12`, mas não será alterado nesta change.
- A futura sincronização deve considerar a divergência entre arquivos locais e workspace remoto.

### Dependências de validação

- A futura modelagem deverá ser validada contra as specifications consolidadas.
- Os arquivos XanoScript futuros deverão ser validados pelo Xano Developer MCP.
- O Xano CLI deverá executar dry-run antes de qualquer push.
- O erro preexistente de `xano/workspace/meu_espaco.xs` deverá ser tratado como situação conhecida e separada, não como justificativa para alteração nesta change.

## Riscos

- **Estrutura incompatível com as specifications:** campos ou relações físicas podem não sustentar Produto–Categoria, Produto–Estoque, Produto–Movimentação ou Fornecedor–entrada. **Mitigação:** validar a modelagem contra todas as specifications antes do Apply.
- **Reutilização indevida do quick-start:** entidades como `user`, `account`, `cliente` ou `transacao` podem possuir semântica diferente do domínio de estoque. **Mitigação:** reutilizar somente convenções técnicas comprovadamente compatíveis.
- **Perda de histórico:** remoção ou alteração estrutural pode quebrar referências futuras. **Mitigação:** priorizar referências estáveis e inativação, mantendo exclusão definitiva pendente.
- **Inativação inadequada:** uma estratégia de status pode ser confundida com exclusão ou bloquear histórico válido. **Mitigação:** separar estado ativo/inativo de remoção e revisar impactos sobre registros relacionados.
- **Isolamento incorreto:** assumir ou omitir conta/contexto organizacional pode comprometer a separação dos dados. **Mitigação:** decidir explicitamente se o domínio exige isolamento antes de definir relacionamentos físicos.
- **Nomenclatura inconsistente:** nomes divergentes entre XanoScript, APIs futuras e Reflex podem gerar retrabalho. **Mitigação:** aprovar convenção de nomes antes da criação dos arquivos.
- **Campos desnecessários:** materializar campos não sustentados pelo contrato pode congelar decisões prematuras. **Mitigação:** limitar a modelagem ao necessário e documentar campos pendentes.
- **Índices inadequados:** índices ausentes ou prematuros podem prejudicar consultas futuras ou impor unicidade incorreta. **Mitigação:** justificar cada índice pela consulta, relação ou regra aprovada.
- **Impacto na movimentação futura:** uma modelagem que permita desvincular Produto ou apagar referências poderá comprometer estoque e histórico. **Mitigação:** revisar a compatibilidade com `movimentacao-estoque` antes do Apply.
- **Divergência local/remota:** o snapshot local pode não representar integralmente o workspace Xano. **Mitigação:** usar `xano workspace pull` em etapa autorizada e revisar diferenças antes de push.
- **Alteração do descritor com erro:** corrigir `meu_espaco.xs` incidentalmente pode ampliar o escopo e ocultar a origem do problema. **Mitigação:** manter o erro registrado e tratá-lo em change separada, se necessário.
- **Segurança insuficiente:** uma modelagem sem suporte à identificação de usuário/contexto pode dificultar autorização e auditoria futuras. **Mitigação:** manter compatibilidade com a capability de autenticação/autorização sem inventar a matriz de permissões.

## Decisões de escopo a serem revisadas pelo grupo

As decisões abaixo precisam ser tomadas antes do Apply e não devem ser congeladas apenas por conveniência técnica:

- nomes finais das entidades Categoria, Produto e Fornecedor;
- convenção final de nomes dos campos e arquivos XanoScript;
- quais informações conceituais de Categoria devem ser materializadas;
- quais informações conceituais de Produto devem ser materializadas;
- quais informações conceituais de Fornecedor devem ser materializadas;
- tipos físicos dos campos;
- estratégia de chaves primárias e referências;
- relacionamentos físicos entre Produto e Categoria;
- forma de preservar relações futuras entre Produto, Estoque e Movimentação;
- forma de preservar a relação contextual entre Fornecedor e entradas;
- índices necessários para consultas e referências;
- regras de unicidade para cada entidade;
- estratégia de ativo/inativo;
- comportamento de alterações em registros já referenciados;
- possibilidade de exclusão definitiva, que permanece fora do contrato até decisão explícita;
- necessidade de isolamento por conta ou contexto organizacional;
- compatibilidade da modelagem com usuários, perfis e autorização;
- organização final dos diretórios `xano/table/`, `xano/api/` e `xano/function/`;
- estratégia de validação dos arquivos `.xs`;
- estratégia de sincronização pelo Xano CLI;
- tratamento do erro preexistente em `xano/workspace/meu_espaco.xs`;
- critérios de revisão antes de qualquer push para o workspace remoto;
- estratégia de testes da modelagem e das futuras operações;
- separação entre esta fundação física e as changes futuras de operações backend e integração Reflex.

Essas decisões devem ser revisadas pelo grupo antes da criação de qualquer tabela, schema, arquivo XanoScript, endpoint ou integração.

## Status

Proposal da change `fundacao-tecnica-cadastros` preparada para revisão do grupo. Até este momento, não houve criação de Specification, Design ou Tasks, nem alteração no Xano, Reflex ou implementação de código.
