# criar-projeto-inicial Specification

## Purpose

Esta capability define o contrato verificável da criação inicial do projeto `Meu_projeto`: um protótipo frontend do Sistema de Gerenciamento de Estoque em Reflex, com layout compartilhado, treze páginas navegáveis e dados fictícios estáticos. Autenticação real, autorização, persistência, integração com o Xano e lógica de estoque permanecem fora desta capability.

## ADDED Requirements

### Requirement: O projeto MUST ser criado como pacote Python com a estrutura de diretórios definida

A raiz do projeto MUST conter `__init__.py`, `Meu_projeto.py`, o diretório `components` (com `__init__.py` e `layout.py`) e o diretório `pages` (com `__init__.py` e os módulos de página). Os três `__init__.py` MUST ser criados vazios. Imports entre módulos do projeto MUST ser relativos.

#### Scenario: Aplicação sobre projeto inexistente

- **WHEN** a change é aplicada sobre um diretório vazio
- **THEN** MUST existir exatamente os quinze arquivos do inventário do Design, nos caminhos indicados
- **AND** os três `__init__.py` MUST ter 0 bytes
- **AND** nenhum arquivo de configuração, dependências, teste ou asset MUST ser criado

#### Scenario: Resolução de imports

- **WHEN** cada módulo do projeto é analisado estaticamente
- **THEN** todo import relativo MUST resolver para um arquivo existente e para um nome nele definido

### Requirement: O ponto de entrada MUST registrar as treze rotas do protótipo

`Meu_projeto.py` MUST importar `reflex as rx`, importar as funções de página, criar `app = rx.App()` e registrar cada página com `app.add_page`, informando `route` e `title`. O título de cada página MUST terminar em ` | Estoque`.

#### Scenario: Registro das rotas

- **WHEN** o ponto de entrada é analisado
- **THEN** MUST haver exatamente treze chamadas a `app.add_page`
- **AND** as rotas, funções e títulos MUST ser: `/` `login` `Login | Estoque`; `/dashboard` `dashboard` `Dashboard | Estoque`; `/produtos` `produtos` `Produtos | Estoque`; `/produtos/novo` `novo_produto` `Novo produto | Estoque`; `/categorias` `categorias` `Categorias | Estoque`; `/fornecedores` `fornecedores` `Fornecedores | Estoque`; `/estoque` `estoque` `Estoque | Estoque`; `/movimentacoes` `historico` `Histórico | Estoque`; `/movimentacoes/entradas` `entrada` `Entrada | Estoque`; `/movimentacoes/saidas` `saida` `Saída | Estoque`; `/usuarios` `usuarios` `Usuários | Estoque`; `/perfis` `perfis` `Perfis | Estoque`; `/relatorios` `relatorios` `Relatórios | Estoque`

#### Scenario: Função de página existente

- **WHEN** cada função registrada é resolvida
- **THEN** MUST existir um módulo em `pages` que a defina e devolva um componente Reflex

### Requirement: O layout compartilhado MUST fornecer menu, moldura de página e componentes de apresentação

`components/layout.py` MUST definir `MENU`, `nav_item`, `sidebar`, `page`, `card`, `section`, `mock_table` e `form_input`, com as assinaturas e o comportamento descritos no Design. As páginas, exceto `login`, MUST usar `page` como moldura.

#### Scenario: Menu de navegação

- **WHEN** a sidebar é renderizada
- **THEN** MUST exibir, nesta ordem, onze itens: Dashboard `/dashboard`, Produtos `/produtos`, Categorias `/categorias`, Fornecedores `/fornecedores`, Estoque `/estoque`, Entradas `/movimentacoes/entradas`, Saídas `/movimentacoes/saidas`, Histórico `/movimentacoes`, Relatórios `/relatorios`, Usuários `/usuarios` e Perfis e permissões `/perfis`
- **AND** MUST exibir o link `Sair` para `/`

#### Scenario: Itens do menu apontam para rotas registradas

- **WHEN** os `href` de `MENU` são comparados com as rotas do ponto de entrada
- **THEN** cada `href` MUST corresponder a uma rota registrada

#### Scenario: Moldura de página

- **WHEN** uma página usa `page(title, content)`
- **THEN** MUST exibir a sidebar, o título, o texto fixo `Admin • Usuário mock`, um divisor e o conteúdo informado

#### Scenario: Componentes de apresentação

- **WHEN** `card`, `section`, `mock_table` ou `form_input` são chamados
- **THEN** cada um MUST devolver um componente Reflex sem callbacks nem estado
- **AND** `card` MUST omitir o detalhe quando ele for vazio
- **AND** `form_input` MUST estar disponível mesmo sem uso pelas páginas

### Requirement: A tela de login MUST ser mockada

`pages/login.py` MUST definir `LoginState` com `email` e `password` e a página `login`, sem sidebar. A página MUST NOT validar credenciais nem chamar serviços.

#### Scenario: Entrar sem validação

- **WHEN** a pessoa aciona `Entrar`, com ou sem valores nos campos
- **THEN** o link MUST navegar para `/dashboard`
- **AND** nenhuma credencial MUST ser verificada

#### Scenario: Estado dos campos

- **WHEN** a pessoa digita em `E-mail` ou `Senha`
- **THEN** `LoginState.email` ou `LoginState.password` MUST ser atualizado por `set_email` ou `set_password`
- **AND** o campo de senha MUST usar o tipo `password`

#### Scenario: Aviso de protótipo

- **WHEN** a tela de login é exibida
- **THEN** MUST exibir o texto `Protótipo: autenticação totalmente mockada.`

### Requirement: As páginas de cadastros MUST exibir dados fictícios e controles sem persistência

`pages/produtos.py`, `pages/categorias.py` e `pages/fornecedores.py` MUST definir as páginas `produtos`, `novo_produto`, `categorias` e `fornecedores`, com os campos, colunas e linhas descritos no Design.

#### Scenario: Lista de Produtos

- **WHEN** `/produtos` é exibida
- **THEN** MUST mostrar busca, botão `Buscar` e a tabela com colunas `Código`, `Nome`, `Categoria`, `Unidade`, `Qtd.`, `Mínimo` e `Status`, com quatro linhas fictícias
- **AND** `Novo produto` MUST ser um link para `/produtos/novo`

#### Scenario: Formulário de novo Produto

- **WHEN** `/produtos/novo` é exibida
- **THEN** MUST mostrar os campos `Código`, `Nome`, `Descrição`, `Categoria`, `Unidade de medida` e `Estoque mínimo`
- **AND** `Cancelar` MUST ser um link para `/produtos`
- **AND** `Salvar produto` MUST NOT persistir dados

#### Scenario: Lista de Categorias

- **WHEN** `/categorias` é exibida
- **THEN** MUST mostrar a busca, os botões `Buscar` e `Nova categoria` e a tabela `ID`, `Nome`, `Produtos`, `Status` com cinco linhas fictícias

#### Scenario: Lista de Fornecedores

- **WHEN** `/fornecedores` é exibida
- **THEN** MUST mostrar a busca, os botões `Buscar` e `Novo fornecedor` e a tabela `ID`, `Nome / Razão social`, `Documento`, `Contato`, `Status` com três linhas fictícias

### Requirement: As páginas de estoque e movimentações MUST exibir dados fictícios sem alterar saldo

`pages/estoque.py` e `pages/movimentacoes.py` MUST definir as páginas `estoque`, `historico`, `entrada` e `saida`. Nenhuma delas MUST calcular ou alterar saldo.

#### Scenario: Situação atual do estoque

- **WHEN** `/estoque` é exibida
- **THEN** MUST mostrar quatro cartões de resumo e a tabela `Código`, `Produto`, `Atual`, `Mínimo`, `Situação` com cinco linhas fictícias

#### Scenario: Histórico de movimentações

- **WHEN** `/movimentacoes` é exibida
- **THEN** MUST mostrar os filtros de tipo (`Todos`, `Entrada`, `Saída`), produto e duas datas, o botão `Filtrar` e a tabela de sete colunas com quatro linhas fictícias
- **AND** o botão `Filtrar` MUST NOT filtrar os dados

#### Scenario: Registrar entrada

- **WHEN** `/movimentacoes/entradas` é exibida
- **THEN** MUST mostrar produto, quantidade, fornecedor, data, motivo pré-preenchido com `Compra` e observação
- **AND** `Cancelar` MUST ser um link para `/movimentacoes`
- **AND** `Registrar entrada` MUST NOT registrar movimentação

#### Scenario: Registrar saída

- **WHEN** `/movimentacoes/saidas` é exibida
- **THEN** MUST mostrar produto, quantidade, data, motivo (`Consumo interno`, `Perda`, `Avaria`, `Doação`, `Outro`) e observação
- **AND** `Cancelar` MUST ser um link para `/movimentacoes`
- **AND** `Registrar saída` MUST NOT registrar movimentação

### Requirement: Dashboard e relatórios MUST exibir indicadores fictícios estáticos

`pages/dashboard.py` e `pages/relatorios.py` MUST definir as páginas `dashboard` e `relatorios` com indicadores escritos como literais.

#### Scenario: Dashboard

- **WHEN** `/dashboard` é exibida
- **THEN** MUST mostrar os cartões `Produtos`, `Categorias`, `Fornecedores` e `Estoque baixo`, a seção `Movimentações recentes` com três linhas e a seção `Alertas de estoque` com quatro alertas

#### Scenario: Relatórios

- **WHEN** `/relatorios` é exibida
- **THEN** MUST mostrar três cartões, a seção de período com duas datas e `Gerar relatório`, a tabela `Resumo por produto` com quatro linhas e os botões `Visualizar relatório`, `Exportar CSV` e `Exportar PDF`
- **AND** nenhum desses botões MUST gerar ou exportar arquivo

### Requirement: Usuários e Perfis MUST exibir dados fictícios sem controle de acesso

`pages/usuarios.py` e `pages/perfis.py` MUST definir as páginas `usuarios` e `perfis`. A matriz de permissões exibida MUST ser identificada como mock e MUST NOT ser usada para autorização.

#### Scenario: Lista de Usuários

- **WHEN** `/usuarios` é exibida
- **THEN** MUST mostrar a busca, os botões `Buscar` e `Novo usuário` e a tabela `ID`, `Nome`, `E-mail`, `Perfil`, `Status` com quatro linhas fictícias

#### Scenario: Perfis e matriz mockada

- **WHEN** `/perfis` é exibida
- **THEN** MUST mostrar a tabela `Perfis cadastrados` com três perfis e a seção `Matriz de permissões (mock)` com dez funcionalidades
- **AND** a exibição da matriz MUST NOT conceder ou negar acesso a qualquer rota

### Requirement: O protótipo MUST NOT integrar backend nem implementar lógica de domínio

Nenhum módulo MUST chamar serviços externos, referenciar o Xano ou persistir dados. O único estado Reflex MUST ser `LoginState`. Botões que não sejam links MUST NOT declarar `on_click` nem `on_submit`.

#### Scenario: Ausência de integração externa

- **WHEN** o código do projeto é inspecionado
- **THEN** MUST NOT existir chamada HTTP, importação de cliente HTTP ou referência ao Xano

#### Scenario: Dados estáticos

- **WHEN** qualquer tabela, cartão ou lista é renderizado
- **THEN** os valores MUST vir de literais no código-fonte

### Requirement: A change MUST NOT criar arquivos de configuração, dependências, testes ou assets

A change MUST criar somente os quinze arquivos do inventário. Arquivos como `rxconfig.py`, arquivo de dependências, `assets/`, `.gitignore`, README e testes MUST NOT ser criados, porque não existem no estado atual.

#### Scenario: Ausência de arquivos auxiliares

- **WHEN** o resultado da aplicação é listado
- **THEN** MUST NOT haver arquivos além dos quinze do inventário

### Requirement: A change MUST preservar o conteúdo dos arquivos e excluir a change existente

O conteúdo de cada arquivo criado MUST ser idêntico ao reproduzido no apêndice do Design, byte a byte, inclusive terminadores CRLF. A pasta `operacoes-backend-cadastros` MUST NOT fazer parte do inventário.

#### Scenario: Conteúdo idêntico

- **WHEN** cada bloco do apêndice é extraído e comparado com o arquivo correspondente do projeto
- **THEN** os bytes MUST ser idênticos

#### Scenario: Change existente fora do inventário

- **WHEN** o inventário é comparado com o conteúdo do projeto atual
- **THEN** MUST NOT incluir arquivos de `operacoes-backend-cadastros`

## Acceptance Criteria

- O inventário do Design lista exatamente os quinze arquivos do projeto, com caminhos e tamanhos corretos, e nenhum arquivo gerado ou auxiliar.
- Os três `__init__.py` são vazios e todos os imports relativos resolvem para arquivos e nomes existentes.
- As treze rotas e títulos correspondem à tabela do Design, e todo `href` do menu e dos links de navegação aponta para rota registrada.
- O menu tem onze itens na ordem especificada e o link `Sair` aponta para `/`.
- O login navega para `/dashboard` sem validar credenciais, e `LoginState` é o único estado.
- Nenhuma página faz chamada externa, persiste dados, altera saldo ou tem ação em botões que não sejam links.
- Cada bloco do apêndice do Design é idêntico ao arquivo do projeto, e `operacoes-backend-cadastros` não é incluída.
- A execução do app e a verificação visual, que dependem de Reflex instalado e de configuração ausente do estado atual, não fazem parte dos critérios verificados por esta change.
