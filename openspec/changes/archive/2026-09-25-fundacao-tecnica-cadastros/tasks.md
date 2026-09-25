# Tasks

## 1. Validar contexto e decisões físicas

- [x] 1.1 Confirmar que a Specification desta change está alinhada às specifications de domínio, autenticação, cadastros básicos e movimentação de estoque.
- [x] 1.2 Confirmar os nomes técnicos `category`, `product` e `supplier`, ou registrar decisão revisada antes do Apply.
- [x] 1.3 Confirmar os campos conceituais a materializar sem adicionar campos não sustentados pelo domínio.
- [x] 1.4 Confirmar tipos, chaves, índices, unicidade, status/inativação e estratégia de referências.
- [x] 1.5 Confirmar a decisão aprovada sobre a adoção ou não de isolamento por conta ou contexto organizacional.

## 2. Criar estrutura persistente de Categoria

- [x] 2.1 Criar a estrutura física de Categoria no Xano conforme as decisões aprovadas.
- [x] 2.2 Materializar somente os campos aprovados: `id`, `nome` e `status`, sendo `nome` obrigatório e único, e `status` uma enumeração com `ativo` e `inativo`, com padrão `ativo`, não nulo no registro persistido e omitível na entrada porque o Xano aplica automaticamente o padrão.
- [x] 2.3 Configurar a identificação estável e a unicidade aprovada de `nome`, mantendo `id` como chave primária gerada pela plataforma.
- [x] 2.4 Configurar o estado ativo/inativo sem usar exclusão física como inativação.

## 3. Criar estrutura persistente de Produto

- [x] 3.1 Criar a estrutura física de Produto no Xano conforme as decisões aprovadas.
- [x] 3.2 Materializar somente os campos aprovados: `id`, `codigo`, `nome`, `descricao`, `categoria_id`, `unidade_medida`, `estoque_minimo` e `status`. `codigo`, `nome`, `categoria_id`, `unidade_medida` e `estoque_minimo` são obrigatórios; `descricao` é opcional; `codigo` deve ser único; `unidade_medida` deve ser texto; `estoque_minimo` deve aceitar valores inteiros ou fracionados, ser maior ou igual a `0` e não possuir valor padrão; `status` deve ser enumeração com `ativo` e `inativo`, com padrão `ativo`, não nulo no registro persistido e omitível na entrada porque o Xano aplica automaticamente o padrão.
- [x] 3.3 Configurar a referência persistente e obrigatória `categoria_id` para uma Categoria válida, mantendo a integridade referencial.
- [x] 3.4 Configurar `id` como chave primária estável gerada pela plataforma e `codigo` como campo único, sem criar outras regras de unicidade não aprovadas.
- [x] 3.5 Preservar a compatibilidade da identidade de Produto com futuras estruturas de Estoque e Movimentação.
- [x] 3.6 Não criar `estoque_atual` dentro de Produto; o estoque atual será controlado pela futura estrutura de Estoque e pelas operações de entrada e saída.

## 4. Criar estrutura persistente de Fornecedor

- [x] 4.1 Criar a estrutura física de Fornecedor no Xano conforme as decisões aprovadas.
- [x] 4.2 Materializar somente os campos aprovados: `id`, `nome_razao_social`, `tipo_documento`, `documento`, `contato`, `endereco` e `status`. `nome_razao_social`, `tipo_documento` e `documento` são obrigatórios; `contato` e `endereco` são opcionais; `tipo_documento` deve aceitar apenas `CPF` ou `CNPJ`; `documento` deve ser único; `status` deve ser enumeração com `ativo` e `inativo`, com padrão `ativo`, não nulo no registro persistido e omitível na entrada porque o Xano aplica automaticamente o padrão.
- [x] 4.3 Configurar `id` como chave primária estável gerada pela plataforma e `documento` como campo único, sem criar outras regras de unicidade não aprovadas.
- [x] 4.4 Preservar a estrutura para futura referência contextual por entradas de estoque.

## 5. Configurar relacionamentos e integridade

- [x] 5.1 Configurar o relacionamento Produto–Categoria com integridade referencial.
- [x] 5.2 Confirmar que nenhuma relação criada transforma Fornecedor em requisito universal de Produto ou movimentação.
- [x] 5.3 Preparar a identidade de Produto para futuras referências Produto–Estoque.
- [x] 5.4 Preparar a identidade de Produto para futuras referências Produto–Movimentação.
- [x] 5.5 Preparar a referência futura Fornecedor–entrada de estoque sem criar a operação de entrada.
- [x] 5.6 Validar que referências inexistentes não possam ser confirmadas.

## 6. Preservar histórico e estado dos registros

- [x] 6.1 Configurar `status` como enumeração com `ativo` e `inativo` em Categoria, Produto e Fornecedor, utilizando `ativo` como padrão para novos registros; o campo não deve permanecer nulo no registro persistido e pode ser omitido na entrada, pois o Xano aplica automaticamente o padrão.
- [x] 6.2 Confirmar que a inativação preserva a identificação e referências existentes.
- [x] 6.3 Confirmar que esta change não implementa exclusão definitiva e não cria mecanismo de remoção destrutiva para registros já utilizados; a política definitiva de exclusão permanece fora do escopo.
- [x] 6.4 Confirmar que a política definitiva de exclusão permanece fora do escopo até decisão explícita.

## 7. Validar segurança e compatibilidade futura

- [x] 7.1 Confirmar compatibilidade das estruturas com usuário autenticado e autorização backend futura.
- [x] 7.2 Confirmar que nenhuma matriz detalhada de permissões ou perfil novo foi criada.
- [x] 7.3 Confirmar compatibilidade da modelagem com futuras operações de cadastro.
- [x] 7.4 Confirmar compatibilidade com a futura movimentação de estoque sem implementar sua operação.
- [x] 7.5 Confirmar que Reflex permanece inalterado nesta change.

## 8. Validar XanoScript e sincronização

- [x] 8.1 Validar todos os novos arquivos XanoScript pelo Xano Developer MCP.
- [x] 8.2 Manter `xano/workspace/meu_espaco.xs` inalterado e registrar seu erro preexistente separadamente.
- [x] 8.3 Revisar o diff dos arquivos XanoScript antes de qualquer sincronização.
- [x] 8.4 Executar dry-run do Xano CLI antes de qualquer push aprovado.
- [x] 8.5 Confirmar que o perfil e workspace alvo correspondem ao ambiente aprovado.

## 9. Testar e revisar a fundação

- [x] 9.1 Testar a existência e identificação estável das três estruturas.
- [x] 9.2 Testar o relacionamento Produto–Categoria.
- [x] 9.3 Testar estados ativo/inativo e preservação de referências.
- [x] 9.4 Testar índices, unicidade e integridade referencial aprovados.
- [x] 9.5 Revisar o diff final e confirmar que nenhuma estrutura fora do escopo foi criada.
- [x] 9.6 Confirmar que endpoints, APIs, operações de cadastro, Reflex e movimentação permanecem fora desta change.