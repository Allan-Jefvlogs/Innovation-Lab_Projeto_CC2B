# Design

## Context

As specifications consolidadas definem Categoria, Produto e Fornecedor como cadastros básicos relacionados ao catálogo, ao estoque e ao histórico. O repositório ainda não possui entidades técnicas específicas para esses conceitos no Xano; os arquivos existentes são majoritariamente quick-start, autenticação, contas, logs e outro domínio.

Esta change é a primeira change técnica de implementação dos cadastros básicos. O Design prepara a criação física no Apply, mas não cria tabelas, arquivos XanoScript, endpoints ou sincronização durante Explore, Proposal ou Review.

## Goals / Non-Goals

### Goals

- Criar no Apply uma base persistente distinta para Categoria, Produto e Fornecedor.
- Preservar Produto–Categoria como relação persistente obrigatória para operação normal.
- Manter Produto compatível com futuras relações com Estoque e Movimentação.
- Manter Fornecedor como relação contextual de entradas de estoque.
- Preservar identificação e referências de registros já utilizados.
- Definir convenções físicas suficientes para uma implementação futura revisável.
- Manter compatibilidade com autenticação/autorização sem criar matriz detalhada.

### Non-Goals

- Implementar operações de criação, consulta, alteração ou inativação.
- Criar endpoints, APIs, telas ou integração Reflex.
- Implementar movimentação de estoque, Estoque ou Histórico.
- Alterar autenticação, autorização ou perfis.
- Criar dashboard, relatórios, integrações externas ou funcionalidades financeiras.
- Corrigir `xano/workspace/meu_espaco.xs`.
- Definir política definitiva de exclusão.

## Decisions

### Entidades persistentes próprias

**Decisão:** criar estruturas próprias para `category`, `product` e `supplier` no Apply.

**Motivo:** o contrato define três conceitos distintos e os arquivos quick-start existentes possuem semântica de outros domínios.

**Alternativa considerada:** reutilizar `cliente`, `account` ou outra entidade existente. Foi rejeitada porque nomes semelhantes não comprovam compatibilidade semântica e aumentariam o acoplamento entre domínios.

**Impacto:** haverá uma base técnica clara para futuras operações de cadastro e relações de estoque.

### Convenção de nomenclatura

**Decisão:** usar nomes técnicos em `snake_case`, no singular, alinhados aos conceitos do domínio: `category`, `product` e `supplier`. Arquivos de tabela deverão seguir a mesma convenção, como `xano/table/category.xs`, `xano/table/product.xs` e `xano/table/supplier.xs`.

**Motivo:** a organização atual usa nomes de recursos em minúsculas e o XanoScript existente utiliza identificadores simples em inglês.

**Alternativa considerada:** usar nomes em português ou plural. Foi rejeitada nesta etapa para evitar misturar convenções no XanoScript existente; os nomes públicos de negócio continuam sendo Categoria, Produto e Fornecedor na documentação.

**Impacto:** endpoints e integrações futuras deverão mapear os nomes técnicos sem alterar o vocabulário funcional.

### Identificação estável

**Decisão:** cada entidade deverá possuir uma chave primária estável gerada pela plataforma, seguindo a convenção já observada no XanoScript existente.

**Motivo:** referências futuras Produto–Estoque, Produto–Movimentação e Fornecedor–entrada precisam sobreviver a alterações não destrutivas.

**Alternativa considerada:** usar código de negócio como chave primária. Foi rejeitada porque o domínio não definiu sua estabilidade, formato ou unicidade definitiva.

**Impacto:** códigos de negócio, se aprovados posteriormente, poderão ser índices ou atributos sem substituir a identidade técnica.

### Campos conceituais a materializar

**Decisão:** materializar somente os conceitos já sustentados pelo domínio e necessários à fundação:

- Categoria: identificação estável, nome conceitual obrigatório e estado ativo/inativo.
- Produto: identificação estável, código conceitual, nome, descrição, Categoria relacionada, unidade de medida conceitual, estoque mínimo e estado ativo/inativo. O `estoque_minimo` é obrigatório, aceita valores inteiros ou fracionados e deve ser maior ou igual a 0. Não possui valor padrão; o usuário deve informar o valor no cadastro. O estoque atual do produto inicia em 0 e será controlado pelas futuras movimentações de entrada e saída.
- Fornecedor:
  - identificação estável;
  - `nome_razao_social` obrigatório;
  - `tipo_documento` obrigatório, com valores controlados `CPF` ou `CNPJ`;
  - `documento` obrigatório e único;
  - `contato` opcional;
  - `endereco` opcional;
  - `status` com valores `ativo` ou `inativo`, sem permanecer nulo no registro persistido. Na entrada, o campo pode ser omitido porque o Xano aplica automaticamente o padrão `ativo`.

A forma física e o tipo final de cada campo deverão estar definidos e aprovados antes do Apply e apenas serão materializados durante essa etapa.

**Motivo:** os conceitos aparecem no modelo de domínio e sustentam as specifications de cadastros básicos.

**Alternativa considerada:** criar somente identificadores e nomes mínimos. Foi rejeitada porque Produto exige Categoria e estoque mínimo no contrato conceitual, enquanto Fornecedor possui informações de identificação e contato no domínio.

**Risco:** alguns conceitos, como documento, contato e endereço, podem exigir refinamento de formato. A implementação não deve adicionar subcampos ou regras não aprovados.

### Unidade de medida

**Decisão:** a unidade de medida do Produto será representada como texto, permitindo valores flexíveis conforme o tipo de produto.

**Exemplos:** `unidade`, `kg`, `g`, `litro`, `ml`, `pacote`, `caixa`, `rolo`.

**Motivo:** o sistema ainda não possui um nicho de produtos definido e, portanto, não deve limitar previamente as unidades aceitas.

**Impacto:** Produtos poderão utilizar diferentes unidades de medida sem exigir alteração da estrutura sempre que surgir uma nova unidade.

### Tipos físicos

**Decisão:** utilizar tipos físicos compatíveis com a natureza de cada campo:

- Identificadores (`id`): chave primária inteira gerada pela plataforma.
- Campos textuais (`nome`, `codigo`, `descricao`, `unidade_medida`, `nome_razao_social`, `documento`, `contato` e `endereco`): texto.
- `tipo_documento`: enumeração com os valores `CPF` e `CNPJ`.
- `status`: enumeração com os valores `ativo` e `inativo`.
- `estoque_minimo`: tipo numérico capaz de armazenar valores inteiros e fracionados, com valor mínimo permitido de `0`.

**Motivo:** os tipos devem representar corretamente a natureza dos dados e preservar compatibilidade com as necessidades futuras do sistema.

**Impacto:** o Apply deverá materializar exatamente os tipos definidos nesta seção, sem introduzir novos tipos ou alterar as regras aprovadas.

### Status e inativação

**Decisão:** Categoria, Produto e Fornecedor possuirão um campo de status representado por enumeração controlada com os valores `ativo` e `inativo`, usando `ativo` como valor padrão. O campo não deve permanecer nulo no registro persistido. Na entrada, `status` pode ser omitido, pois o Xano aplica automaticamente o valor padrão `ativo`. A inativação não utilizará remoção física.

**Motivo:** manter registros identificáveis preserva referências históricas e permite distinguir cadastros disponíveis dos que não devem mais ser utilizados.

**Alternativa considerada:** utilizar valor booleano, ausência de estado ou remoção física. Foram rejeitados porque não representam adequadamente os estados definidos ou poderiam comprometer referências e histórico.

**Impacto:** o campo de status deverá ser criado como enumeração com os valores `ativo` e `inativo`, iniciando como `ativo` para novos registros. A representação XanoScript `enum status?="ativo"` permite omitir o campo na entrada e aplica o default sem deixar o campo nulo no registro persistido.

### Produto–Categoria

**Decisão:** Produto manterá uma referência persistente e obrigatória à Categoria, com integridade referencial aplicada no Xano. Produtos já relacionados a uma Categoria que posteriormente seja inativada deverão continuar preservando essa referência.

**Motivo:** a Categoria é obrigatória para o Produto e a preservação da relação evita quebra de histórico e de referências existentes.

**Alternativa considerada:** remover ou romper automaticamente a referência dos Produtos quando uma Categoria fosse inativada. Foi rejeitada porque poderia produzir Produtos sem Categoria válida e comprometer referências existentes.

**Impacto:** a inativação de uma Categoria não deverá remover nem quebrar as referências dos Produtos já associados. A regra operacional para impedir novas associações de Produtos a Categorias inativas deverá ser aplicada nas futuras operações de cadastro.

### Relações futuras com Estoque e Movimentação

**Decisão:** não criar estruturas de Estoque ou Movimentação nesta change, mas preservar a identidade estável de Produto e evitar decisões que impeçam referências futuras.

**Motivo:** essas entidades pertencem a capabilities próprias e já possuem contratos consolidados.

**Alternativa considerada:** criar relacionamentos físicos antecipados para entidades inexistentes. Foi rejeitada porque inventaria estrutura fora do escopo e poderia congelar o design da movimentação.

### Fornecedor–entrada de estoque

**Decisão:** não criar relação direta universal entre Fornecedor e Produto. A futura entrada de estoque deverá poder referenciar Fornecedor quando aplicável.

**Motivo:** Fornecedor é contextual às entradas e não requisito universal de Produto ou movimentação.

**Alternativa considerada:** vincular Fornecedor diretamente a Produto como relação obrigatória. Foi rejeitada porque contradiz a natureza contextual consolidada.


### Chaves, índices e unicidade

**Decisão:** todas as entidades utilizarão uma chave primária estável gerada pela plataforma.

As regras de unicidade aprovadas são:

- Categoria: `nome` deve ser único.
- Produto: `codigo` deve ser único.
- Fornecedor: `documento` deve ser único.

Não deverão ser criadas outras regras de unicidade sem decisão específica do domínio.

**Motivo:** essas regras evitam duplicidade nos identificadores de negócio definidos para cada cadastro sem substituir a identidade técnica gerada pela plataforma.

**Alternativa considerada:** criar índices únicos para outros campos ou combinações de campos. Foi rejeitada porque não existe decisão de negócio aprovada para essas outras unicidades.

**Impacto:** o Apply deverá materializar somente as regras de unicidade aprovadas para `nome`, `codigo` e `documento`, mantendo as chaves primárias geradas pela plataforma.


### Isolamento por conta ou contexto organizacional

**Decisão:** não haverá isolamento por conta ou contexto organizacional nesta versão do sistema.

**Motivo:** o sistema será utilizado por uma única empresa/organização, portanto Categoria, Produto e Fornecedor não precisam possuir uma referência a `account` ou a outra entidade organizacional para separar dados entre empresas.

**Alternativa considerada:** adicionar referência obrigatória a `account` por reutilização do quick-start. Foi rejeitada porque introduziria uma estrutura e uma regra de isolamento desnecessárias ao escopo atual.

**Impacto:** as estruturas de Categoria, Produto e Fornecedor serão criadas sem vínculo obrigatório com `account` ou outra entidade de isolamento organizacional. Uma eventual necessidade futura de suporte a múltiplas empresas deverá ser tratada em uma change específica.

### Organização dos arquivos XanoScript

**Decisão:** os futuros arquivos de persistência deverão seguir `xano/table/` e a convenção `snake_case` singular, sem criar os arquivos nesta etapa. Endpoints e funções permanecerão para changes posteriores.

**Motivo:** mantém a organização existente e separa persistência de operações.

**Impacto:** a futura implementação deverá validar os arquivos individualmente e revisar o diff antes do push.

### Quick-start e descritor com erro

**Decisão:** não reutilizar automaticamente entidades quick-start e não alterar `xano/workspace/meu_espaco.xs`.

**Motivo:** o Explore identificou semânticas de outros domínios e um erro preexistente no descritor de workspace.

**Impacto:** a modelagem será criada como base específica e o erro deverá ser tratado separadamente, se o grupo aprovar uma change própria.

## Architecture Boundaries

- **Xano:** persistência, integridade referencial, estado ativo/inativo e autoridade das futuras operações backend.
- **Reflex:** permanece fora desta change; nenhuma tela, estado ou integração será criada.
- **Autenticação/autorização:** continuará sendo aplicada no backend conforme capability consolidada.
- **OpenSpec:** mantém o contrato e rastreia decisões aprovadas e pendentes.
- **Xano CLI/MCP:** apoiarão validação e sincronização somente em etapas autorizadas.
- **Git:** versionará os arquivos técnicos após revisão; nenhum commit faz parte desta etapa.

## Apply Boundary

Durante Explore, Proposal e Review não devem ser criados tabelas, schemas, campos, chaves, índices, arquivos XanoScript ou alterações remotas.

Nenhuma decisão física ou arquitetural importante deverá ser tomada durante o Apply. Todas as decisões sobre entidades, campos, tipos, chaves, índices, relacionamentos, unicidade, estratégia de estado, referências e isolamento deverão estar previamente definidas e aprovadas antes do início do Apply.

O Apply deverá apenas materializar, validar e sincronizar as decisões previamente aprovadas, sem introduzir decisões físicas novas por iniciativa própria.

## Risks / Trade-offs

- **[Risco]** Materializar campos que ainda não possuem decisão de formato. **Mitigação:** limitar os campos aos conceitos justificados e manter tipos/precisão pendentes quando não aprovados.
- **[Risco]** Introduzir isolamento por conta sem decisão de domínio. **Mitigação:** não importar `account` automaticamente e exigir revisão explícita.
- **[Risco]** Criar unicidade incompatível com o negócio. **Mitigação:** só criar índices únicos aprovados.
- **[Risco]** Quebrar histórico com remoção física. **Mitigação:** manter identificação estável e status de inativação.
- **[Risco]** Reutilizar quick-start por semelhança nominal. **Mitigação:** manter entidades próprias do domínio.
- **[Risco]** Falha preexistente bloquear a validação do snapshot. **Mitigação:** não alterar `meu_espaco.xs`; registrar o problema e separar seu tratamento.
- **[Trade-off]** Adiar tipos detalhados de precisão preserva decisões abertas, mas exige confirmação antes do Apply.
- **[Trade-off]** Não criar Estoque ou Movimentação agora reduz acoplamento, mas exige que a modelagem seja revisada antes das changes futuras.

## Scope Boundaries

Esta change prepara e, no Apply aprovado, cria somente a fundação física de persistência de Categoria, Produto e Fornecedor. Não implementa operações de cadastro, endpoints, APIs, Reflex, movimentação de estoque, dashboard, relatórios, autenticação, permissões detalhadas, integrações externas ou estruturas de Estoque e Movimentação.
