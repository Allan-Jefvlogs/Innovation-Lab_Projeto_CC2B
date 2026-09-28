# Proposal

## Why

O Sistema de Gerenciamento de Estoque ainda não possui projeto. Antes de qualquer integração com backend, o grupo precisa de um ponto de partida navegável para validar telas, fluxos de navegação e vocabulário de domínio (Produto, Categoria, Fornecedor, Estoque, Movimentações, Usuários e Perfis). Sem esse projeto base, não há onde aplicar changes posteriores, inclusive as que dependem de uma interface Reflex.

Esta change propõe criar o projeto `Meu_projeto` como um protótipo frontend em Reflex (Python): um pacote com layout compartilhado, treze páginas registradas em rotas e dados totalmente fictícios. O protótipo não autentica, não persiste e não chama serviços externos. O backend Xano é tratado por changes próprias, como `operacoes-backend-cadastros`, que declara a interface Reflex fora do seu escopo.

## What Changes

- Criar o pacote Python raiz com `__init__.py` e os subpacotes `components` e `pages`, cada um com `__init__.py` vazio.
- Criar `Meu_projeto.py` com `app = rx.App()` e o registro das treze rotas do protótipo, cada uma com título no formato `<Nome> | Estoque`.
- Criar `components/layout.py` com o menu de onze itens, a sidebar, a moldura de página `page` e os componentes `card`, `section`, `mock_table` e `form_input`.
- Criar `pages/login.py` com `LoginState` e a tela de login mockada, que apenas navega para `/dashboard`.
- Criar as páginas de cadastros: Produtos (lista e formulário de novo produto), Categorias e Fornecedores.
- Criar as páginas operacionais: Estoque, Histórico de movimentações, Registrar entrada e Registrar saída.
- Criar as páginas gerenciais e administrativas: Dashboard, Relatórios, Usuários e Perfis e permissões.
- Manter todos os dados como literais fictícios no código, sem estado de domínio, persistência ou integração.

## Scope

### Incluído

- Os quinze arquivos abaixo, criados com o conteúdo reproduzido no apêndice do Design:

| Arquivo | Papel |
| --- | --- |
| `__init__.py` | Marca a raiz do projeto como pacote Python; arquivo vazio. |
| `Meu_projeto.py` | Ponto de entrada: cria `rx.App()` e registra as 13 rotas. |
| `components/__init__.py` | Marca `components` como subpacote; arquivo vazio. |
| `components/layout.py` | Menu, sidebar, moldura de página e componentes de apresentação. |
| `pages/__init__.py` | Marca `pages` como subpacote; arquivo vazio. |
| `pages/categorias.py` | Página `categorias` (lista de Categorias). |
| `pages/dashboard.py` | Página `dashboard` (visão geral). |
| `pages/estoque.py` | Página `estoque` (situação atual). |
| `pages/fornecedores.py` | Página `fornecedores` (lista de Fornecedores). |
| `pages/login.py` | `LoginState` e página `login` (autenticação mockada). |
| `pages/movimentacoes.py` | Páginas `historico`, `entrada` e `saida`. |
| `pages/perfis.py` | Página `perfis` (perfis e matriz de permissões mockados). |
| `pages/produtos.py` | Páginas `produtos` (lista) e `novo_produto` (formulário). |
| `pages/relatorios.py` | Página `relatorios` (consultas gerenciais mockadas). |
| `pages/usuarios.py` | Página `usuarios` (lista de usuários). |

- O registro das treze rotas:

| Rota | Função | Arquivo | Título |
| --- | --- | --- | --- |
| `/` | `login` | `pages/login.py` | Login | Estoque |
| `/dashboard` | `dashboard` | `pages/dashboard.py` | Dashboard | Estoque |
| `/produtos` | `produtos` | `pages/produtos.py` | Produtos | Estoque |
| `/produtos/novo` | `novo_produto` | `pages/produtos.py` | Novo produto | Estoque |
| `/categorias` | `categorias` | `pages/categorias.py` | Categorias | Estoque |
| `/fornecedores` | `fornecedores` | `pages/fornecedores.py` | Fornecedores | Estoque |
| `/estoque` | `estoque` | `pages/estoque.py` | Estoque | Estoque |
| `/movimentacoes` | `historico` | `pages/movimentacoes.py` | Histórico | Estoque |
| `/movimentacoes/entradas` | `entrada` | `pages/movimentacoes.py` | Entrada | Estoque |
| `/movimentacoes/saidas` | `saida` | `pages/movimentacoes.py` | Saída | Estoque |
| `/usuarios` | `usuarios` | `pages/usuarios.py` | Usuários | Estoque |
| `/perfis` | `perfis` | `pages/perfis.py` | Perfis | Estoque |
| `/relatorios` | `relatorios` | `pages/relatorios.py` | Relatórios | Estoque |

- Menu lateral com onze itens (Dashboard, Produtos, Categorias, Fornecedores, Estoque, Entradas, Saídas, Histórico, Relatórios, Usuários e Perfis e permissões) e link `Sair` para `/`.
- Componentes reutilizáveis de apresentação: `card`, `section`, `mock_table` e `form_input`.
- Estado Reflex restrito a `LoginState` (`email`, `password` e seus setters).
- Fluxos de navegação por link: `Entrar` para `/dashboard`, `Novo produto` para `/produtos/novo`, `Cancelar` para `/produtos` (formulário de produto) ou `/movimentacoes` (formulários de entrada e saída).
- Estratégia de verificação estática do conteúdo criado (compilação, resolução de imports, consistência entre menu e rotas, ausência de integração externa e igualdade de conteúdo).

### Fora do escopo

- Arquivos de configuração do Reflex (por exemplo `rxconfig.py`), arquivo de dependências, `assets/`, `.gitignore`, README e demais arquivos auxiliares: não existem no estado atual do projeto e não são criados por esta change.
- Testes automatizados: não existem no estado atual do projeto.
- Autenticação real, controle de sessão, proteção de rotas e autorização por perfil.
- Integração com o Xano ou qualquer outro backend, chamadas HTTP e persistência.
- Funcionamento de busca, filtros, botões de ação (`Buscar`, `Filtrar`, `Gerar relatório`, `Exportar CSV`, `Exportar PDF`, `Nova categoria`, `Novo fornecedor`, `Novo usuário`, `Salvar produto`, `Registrar entrada`, `Registrar saída`) e formulários além da renderização.
- Cálculo de saldo, regras de estoque mínimo, movimentações reais e relatórios reais.
- A pasta `operacoes-backend-cadastros`: é uma change com artefatos próprios, não código do projeto.
- Push, sync, commit ou Archive como parte desta proposal.

## Decisões de reconstrução

Esta change foi reconstruída retroativamente a partir do estado atual do projeto. As decisões abaixo pertencem à reconstrução e não substituem aprovações de grupo.

- O nome da change e o da capability são `criar-projeto-inicial`, seguindo o padrão da referência, em que ambos coincidem.
- Os caminhos dos arquivos são relativos à raiz do projeto, o diretório `Meu_projeto` recebido; `Meu_projeto.py` e `__init__.py` ficam nessa raiz.
- O conteúdo dos arquivos é reproduzido sem alteração no apêndice do `design.md`, incluindo os terminadores de linha CRLF, porque o formato da change não tem diretório para código-fonte.
- Os três arquivos `__init__.py` são criados vazios, como no estado atual.
- Arquivos ausentes do estado atual (configuração, dependências, testes, assets) não são criados nem sugeridos como parte da criação inicial.

## Dependências

### Dependências funcionais

- Nenhuma. Esta é a primeira change e não depende de capabilities anteriores.
- Changes posteriores, como `operacoes-backend-cadastros`, dependem apenas de o backend Xano existir; ela não altera páginas, componentes ou estado Reflex.

### Dependências técnicas

- Python com suporte à anotação `list[str]` usada em `components/layout.py` (Python 3.9 ou superior).
- Pacote `reflex`, importado como `rx` em todos os módulos. O projeto atual não fixa versão nem declara dependências.
- Os módulos usam imports relativos (`.pages...`, `..components.layout`), então o diretório do projeto precisa ser carregado como pacote.

## Impact

- **Frontend:** passa a existir um app Reflex com treze rotas e navegação lateral comum.
- **Segurança:** o login é mockado e nenhuma rota é protegida; qualquer rota pode ser aberta diretamente. O texto `Admin • Usuário mock` no cabeçalho é fixo e não reflete um usuário real.
- **Dados:** nenhum dado persistente. Todos os valores exibidos são literais no código.
- **Backend:** nenhum impacto; não há chamadas ao Xano.
- **Changes futuras:** ligar telas a APIs, substituir o login mockado e implementar ações de formulários exigirão changes próprias.

## Riscos

- **Protótipo tomado por implementação:** o login aceita qualquer valor e as páginas exibem dados fixos. O texto `Protótipo: autenticação totalmente mockada.` sinaliza isso apenas na tela de login.
- **Execução dependente de arquivos ausentes:** o estado atual não contém `rxconfig.py` nem arquivo de dependências. A execução do app depende de configuração fornecida fora desta change, e a versão do Reflex não é definida.
- **Dados fictícios inconsistentes entre páginas:** por exemplo, a lista de Categorias usa `Materiais de limpeza` e `Materiais de escritório`, enquanto Produtos e o formulário de novo produto usam `Limpeza` e `Escritório`; o Dashboard indica 12 Categorias e 24 Fornecedores, mas as listas exibem 5 e 3 linhas. Os valores são preservados como estão.
- **Matriz de permissões mockada divergente do backend:** a página Perfis usa os nomes `Administrador`, `Estoquista` e `Usuário de consulta` e uma matriz por funcionalidade de tela, que não coincide com a matriz aprovada em `operacoes-backend-cadastros` (Líder, Almoxarife e Auxiliar de almoxarifado, com permissões por operação). A página não deve ser tratada como fonte de verdade de autorização.
- **Código sem uso:** `form_input` é definido em `components/layout.py`, mas nenhuma página o usa. É preservado porque faz parte do estado atual.
- **Rota `/produtos/novo` fora do menu:** só é alcançada pelo botão `Novo produto` da página de Produtos.
- **Sem controle de sessão:** o link `Sair` apenas navega para `/`.

## Decisões técnicas a resolver no Design

- Convenção de caminhos e representação do conteúdo dos arquivos dentro do formato da change.
- Inventário completo de arquivos, com papel de cada um e tratamento dos arquivos vazios.
- Tabela de rotas e o contrato de `page`, `card`, `section`, `mock_table` e `form_input`.
- Escopo do estado Reflex (`LoginState`) e tratamento dos dados fictícios.
- Fronteira com backend e com changes futuras.
- Estratégia de verificação sem depender do Reflex instalado.

## Status

Proposal da capability `criar-projeto-inicial`, reconstruída retroativamente a partir do estado atual de `Meu_projeto` para representar a change que teria criado o projeto. Esta etapa não altera o projeto original, o Xano, a change `operacoes-backend-cadastros` nem executa push, sync ou commit.
