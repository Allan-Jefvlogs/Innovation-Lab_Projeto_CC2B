# Proposal

## Why

As capabilities consolidadas de cadastros básicos e fundação técnica definem o contrato funcional e as estruturas persistentes de Categoria, Produto e Fornecedor. O snapshot local do Xano já contém as tabelas `category`, `product` e `supplier`, mas não contém operações de backend para esses cadastros. As APIs existentes são de autenticação, contas, membros e logs do quick-start ou de outro domínio.

Sem operações protegidas no Xano, o sistema ainda não pode criar, consultar, alterar ou inativar esses registros com validação centralizada. Também falta um mecanismo backend para aplicar a matriz de permissões aprovada e permitir que o Líder altere as permissões dos outros dois perfis. Deixar essas decisões apenas no Reflex permitiria contornar as regras chamando as APIs diretamente.

Esta change propõe implementar no Xano as operações de cadastro e a consulta e alteração das permissões de Almoxarife e Auxiliar de almoxarifado. O Xano continuará responsável por autenticação, resolução do perfil, autorização, validação e integridade. A interface visual de gerenciamento de permissões e as telas de cadastro serão tratadas em mudanças futuras do Reflex.

## What Changes

- Implementar operações protegidas de criação, consulta, alteração e inativação de Categoria, Produto e Fornecedor no Xano.
- Aplicar a matriz inicial de permissões aprovada pelo grupo e verificar no backend a permissão específica exigida por cada operação.
- Disponibilizar operações backend para consultar e alterar as permissões de Almoxarife e Auxiliar de almoxarifado, acessíveis somente ao Líder.
- Garantir que o Líder mantenha acesso integral e que suas permissões não possam ser removidas ou restringidas por essas operações.
- Resolver e implementar o vínculo necessário entre a identidade autenticada existente e um dos três perfis do projeto, sem adotar `admin`/`member` do quick-start como modelo final de autorização.
- Aplicar as regras já consolidadas para unicidade, referências, status ativo/inativo e preservação histórica dos cadastros.
- Manter distinguíveis as falhas de autenticação, autorização, validação e regra de negócio, conforme o contrato de integração existente.

## Scope

### Incluído

- Operações backend no Xano para criar, consultar, alterar e inativar Categoria, Produto e Fornecedor. A forma das consultas — incluindo listagem, detalhe, filtros e paginação — será definida no Design.
- Autenticação e autorização no backend para todas as operações protegidas, inclusive consultas.
- Aplicação da matriz inicial aprovada:

| Cadastro | Operação | Líder (Administrador) | Almoxarife (Estoquista) | Auxiliar de almoxarifado (Usuário de consulta) |
| --- | --- | --- | --- | --- |
| Categoria | Consultar | Permitido | Permitido | Permitido |
| Categoria | Criar | Permitido | Negado | Negado |
| Categoria | Alterar | Permitido | Negado | Negado |
| Categoria | Inativar | Permitido | Negado | Negado |
| Produto | Consultar | Permitido | Permitido | Permitido |
| Produto | Criar | Permitido | Permitido | Negado |
| Produto | Alterar | Permitido | Permitido | Negado |
| Produto | Inativar | Permitido | Permitido | Negado |
| Fornecedor | Consultar | Permitido | Permitido | Permitido |
| Fornecedor | Criar | Permitido | Permitido | Negado |
| Fornecedor | Alterar | Permitido | Permitido | Negado |
| Fornecedor | Inativar | Permitido | Permitido | Negado |

- Persistência e operações backend necessárias para consultar e alterar as permissões atribuídas aos perfis Almoxarife e Auxiliar de almoxarifado.
- Acesso integral do Líder às funcionalidades e proteção contra alterações que restrinjam as permissões do próprio Líder.
- Definição e implementação do vínculo necessário para resolver o perfil do usuário autenticado, mantendo separados o perfil conceitual e os papéis `admin`/`member` do quick-start.
- Validação de unicidade de `category.nome`, `product.codigo` e `supplier.documento`.
- Validação de referência a Categoria existente em Produto e rejeição de novas associações a Categoria inativa.
- Inativação por estado, preservando IDs e referências existentes; nenhuma exclusão física de Categoria, Produto ou Fornecedor será implementada.
- Preservação do saldo de estoque: esta capability não altera quantidade disponível nem executa movimentações.
- Estratégia de verificação das operações e revisão de compatibilidade com as specs e estruturas existentes.

### Fora do escopo

- Interface visual de cadastro ou gerenciamento de permissões em Reflex; será implementada em change futura.
- Alterações às páginas, componentes, estado ou navegação Reflex, ou integração do frontend com estas APIs.
- Implementação ou substituição do fluxo de autenticação, login, recuperação de senha ou gerenciamento geral de usuários.
- Atribuição administrativa de perfil a usuários além do vínculo mínimo necessário para que o backend identifique o perfil autenticado; os detalhes desse vínculo serão definidos no Design.
- Alteração da fundação física já criada para Categoria, Produto e Fornecedor, salvo se o Design identificar necessidade justificada e a mudança for aprovada no escopo desta change.
- Exclusão física de cadastros.
- Alteração de saldo, criação de estoque, movimentações, entradas, saídas ou histórico operacional.
- Definição de permissões para funcionalidades fora dos cadastros básicos e do gerenciamento das permissões cobertas por esta change.
- Dashboard, relatórios, importação em massa e integrações externas.
- Push, sync ou commit como parte desta proposal.

## Decisões aprovadas pelo grupo

- Os perfis conceituais são Administrador, Estoquista e Usuário de consulta, apresentados na interface como Líder, Almoxarife e Auxiliar de almoxarifado, respectivamente.
- As permissões são atribuídas por perfil, não individualmente por usuário.
- O Líder tem acesso integral a todas as funcionalidades e suas permissões não podem ser removidas ou restringidas.
- O Líder pode adicionar ou remover permissões dos perfis Almoxarife e Auxiliar de almoxarifado.
- O Líder pode remover todas as permissões editáveis de Almoxarife ou Auxiliar de almoxarifado; não existe uma quantidade mínima obrigatória de permissões para esses perfis nesta etapa.
- A matriz apresentada nesta proposal é a matriz inicial para as doze combinações de cadastro e operação listadas no escopo.
- A autorização deve ser aplicada no Xano e não pode depender somente do frontend.
- Esta change inclui o backend para consultar e alterar as permissões dos dois perfis não-Líder.
- A interface Reflex para gerenciamento de permissões será implementada posteriormente, fora desta change.
- As operações respeitarão autenticação, autorização, unicidade, integridade referencial, dependência Produto–Categoria e preservação histórica; não haverá exclusão física nem alteração do saldo de estoque.

## Dependências

### Dependências funcionais

- `cadastros-basicos` define o ciclo de criação, consulta, alteração e inativação e as regras de integridade para Categoria, Produto e Fornecedor.
- `fundacao-tecnica-cadastros` define as tabelas locais `category`, `product` e `supplier`, os campos, status, relação Produto–Categoria e índices únicos. A implementação deve validar se o estado do workspace Xano corresponde ao snapshot antes de qualquer sincronização futura.
- `estabelecer-fundacao-dominio` fornece o vocabulário de domínio e o contrato de respostas distinguíveis para sucesso, autenticação, autorização, validação e regra de negócio.
- `autenticacao-autorizacao` exige identidade autenticada, associação do usuário a um perfil e autorização no backend. O papel quick-start `admin`/`member` existente não representa os três perfis aprovados e não deve ser usado como modelo final.
- `movimentacao-estoque` depende da preservação de Produto e Fornecedor, mas a operação de movimentação e a alteração de saldo permanecem fora desta change.

### Dependências técnicas

- Xano é a autoridade para APIs, persistência e aplicação das regras de autorização e integridade.
- O snapshot local contém `user` como tabela de autenticação com `role` quick-start (`admin`/`member`), além das três tabelas de cadastro. O modelo definitivo de perfil e o vínculo com a identidade autenticada ainda precisam ser desenhados.
- A interface Reflex consumirá contratos backend futuros, mas não participa da decisão final de autorização.
- O Xano Developer MCP e o Xano CLI poderão ser usados em etapas de Design e Apply para documentar, validar e, quando aprovado, sincronizar XanoScript. Esta proposal não autoriza alteração remota.

## Impact

- **Xano:** passará a oferecer operações de cadastro protegidas e operações para consultar e alterar permissões dos perfis não-Líder. Será necessário representar os perfis, permissões e vínculo com usuário autenticado de forma compatível com as decisões do grupo.
- **Segurança:** cada operação deverá verificar autenticação e permissão específica no backend. A alteração da matriz deverá ser exclusiva do Líder; a autorização do Líder será protegida contra autolimitação.
- **Integridade:** Produto deverá referenciar Categoria existente e ativa ao criar ou alterar sua associação. Inativar preservará o registro e suas referências. Índices únicos existentes devem ser tratados como restrições funcionais e produzir falhas distinguíveis.
- **Frontend futuro:** Reflex poderá consultar e exibir os cadastros e a matriz de permissões por meio dos contratos do Xano. A interface de gerenciamento, apresentação dos nomes de perfil e controles correspondentes pertencem a uma change futura.
- **Estoque:** nenhuma quantidade ou movimentação será alterada. Produto inativo e regras de uso nas operações de estoque permanecem sob as capabilities correspondentes.

## Riscos

- **Mapeamento incorreto de perfil:** o papel quick-start `admin`/`member` não distingue os perfis aprovados. Reutilizá-lo diretamente poderia conceder acesso indevido ou negar acesso válido. O Design deve resolver o vínculo com a identidade autenticada sem assumir equivalência semântica.
- **Autorização somente na interface:** ocultar ações no Reflex sem verificar a permissão em cada endpoint permitiria chamadas diretas não autorizadas. A verificação backend por operação é requisito desta mudança.
- **Líder sem acesso integral:** armazenar permissões do Líder em dados editáveis sem proteção poderia removê-las por erro ou chamada indevida. A regra de acesso integral deve ser garantida pelo backend.
- **Permissões removidas em excesso:** o Líder pode retirar todas as permissões editáveis de qualquer um dos perfis não-Líder, deixando-o sem operações de cadastro permitidas. O backend deve tratar esse estado sem conceder permissões implícitas.
- **Concorrência ou substituição acidental da matriz:** atualizações em lote podem sobrescrever mudanças recentes ou permissões não enviadas. O Design deve definir como aplicar alterações e validar o estado resultante.
- **Integridade de Categoria:** permitir associação nova a Categoria inativa ou inexistente deixaria Produto fora do contrato. O backend deve validar a referência em criação e alteração sem romper vínculos existentes em inativação.
- **Unicidade e formato:** o schema assegura unicidade dos campos aprovados, mas normalização de texto/documento e validações de formato além dos campos existentes precisam ser explicitadas antes da implementação, sem presumir regras novas.
- **Permissões desatualizadas em token:** incluir permissões no token pode deixar decisões antigas válidas após uma alteração. O Design deve definir como evitar ou limitar essa defasagem.
- **Ausência de auditoria definida:** ainda não há decisão sobre registrar quem alterou permissões, o que mudou e por quanto tempo manter o histórico. Essa decisão precisa ser avaliada no Design.

## Decisões técnicas a resolver no Design

- Estrutura técnica de perfis e permissões, incluindo a representação da matriz inicial e das alterações posteriores.
- Relação entre cada usuário autenticado e exatamente um dos três perfis; tratamento de usuário sem perfil ou com perfil inválido.
- Tratamento do campo `role` quick-start existente e compatibilidade com a tabela `user` e o fluxo de autenticação atuais.
- Persistência de permissões e limites do catálogo de permissões que o Líder pode alterar.
- Como garantir o acesso integral e não removível do Líder, inclusive diante de alterações malformadas ou concorrentes.
- Quais respostas o backend deve produzir quando o perfil não puder executar nenhuma operação de cadastro após a remoção de todas as suas permissões editáveis.
- Estratégia para avaliar permissões: leitura do estado atual no backend, claims/token ou outra abordagem, incluindo efeito de alterações sobre sessões e tokens já emitidos.
- Se e como auditar alterações de permissões: eventos registrados, autor, perfil afetado, permissões anteriores e posteriores, retenção e acesso aos registros.
- Contratos das operações backend: grupos, nomes e verbos dos endpoints, consultas de lista/detalhe, filtros, paginação, campos atualizáveis e formato das respostas e erros.
- Normalização e tratamento de conflitos de unicidade para `nome`, `codigo` e `documento`, além de validações de formato dos dados sem introduzir regras não aprovadas.
- Estratégia de validação dos arquivos XanoScript e compatibilidade do snapshot local com o workspace remoto antes de qualquer sincronização autorizada.

## Status

Proposal da capability `operacoes-backend-cadastros` preparada para revisão do grupo. Esta etapa não cria Design, Specification ou Tasks, não implementa operações e não altera o Xano ou o frontend Reflex.
