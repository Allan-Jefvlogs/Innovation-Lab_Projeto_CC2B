# Design

## Context

A proposal reúne uma única entrega: criar do zero o protótipo frontend do Sistema de Gerenciamento de Estoque em Reflex. Não há código, configuração ou change anterior. O resultado é o conjunto de quinze arquivos do estado atual do projeto `Meu_projeto`, sem acrescentar arquivos, funcionalidades ou configurações que não existam nele.

O formato de change adotado segue `operacoes-backend-cadastros`: `proposal.md`, `design.md`, `tasks.md` e `specs/<capability>/spec.md`. Como esse formato não reserva diretório para código-fonte, o conteúdo de cada arquivo do projeto é reproduzido sem alteração no apêndice deste Design. Os caminhos usados aqui são relativos à raiz do projeto, o diretório `Meu_projeto` recebido.

Esta change foi reconstruída retroativamente. Ela descreve o estado atual como se fosse o resultado de uma primeira aplicação e não registra a história real do projeto.

## Goals / Non-Goals

### Goals

- Criar um pacote Python importável, com a raiz e os subpacotes `components` e `pages`.
- Registrar em `Meu_projeto.py` as treze rotas do protótipo, cada uma ligada a uma função de página.
- Centralizar menu, sidebar, moldura de página e componentes de apresentação em `components/layout.py`.
- Cobrir as telas do domínio: login, dashboard, Produtos, Categorias, Fornecedores, Estoque, movimentações, relatórios, Usuários e Perfis.
- Manter os dados como literais fictícios, para permitir revisão visual e de fluxo sem backend.
- Permitir a verificação do resultado por meio de análise estática e comparação de conteúdo.

### Non-Goals

- Criar `rxconfig.py`, arquivo de dependências, `assets/`, `.gitignore`, README ou testes, que não existem no estado atual.
- Implementar autenticação, sessão, autorização, persistência ou integração com o Xano.
- Implementar busca, filtros, formulários funcionais, exportação, cálculo de saldo ou regras de estoque mínimo.
- Alterar ou incluir a change `operacoes-backend-cadastros`.
- Definir versão do Reflex ou ambiente de execução.

## Architecture

O projeto é um pacote Python com três níveis:

```
(raiz do projeto)
├── __init__.py
├── Meu_projeto.py          # app e rotas
├── components/
│   ├── __init__.py
│   └── layout.py           # menu, sidebar, page, card, section, mock_table, form_input
└── pages/
    ├── __init__.py
    ├── categorias.py
    ├── dashboard.py
    ├── estoque.py
    ├── fornecedores.py
    ├── login.py
    ├── movimentacoes.py
    ├── perfis.py
    ├── produtos.py
    ├── relatorios.py
    └── usuarios.py
```

`Meu_projeto.py` importa cada função de página com imports relativos (`from .pages.login import login`, por exemplo), cria `app = rx.App()` e chama `app.add_page(<função>, route=..., title=...)` treze vezes. Cada módulo de página importa de `..components.layout` apenas os componentes que usa e devolve `page("<título>", <conteúdo>)`, exceto `login`, que monta a própria tela com `rx.center`, sem a sidebar.

Não existe camada de serviços, cliente HTTP, modelo de dados ou estado além de `LoginState`.

## Inventário de arquivos

| Arquivo | Bytes | Papel |
| --- | --- | --- |
| `__init__.py` | 0 | Marca a raiz do projeto como pacote Python; arquivo vazio. |
| `Meu_projeto.py` | 1436 | Ponto de entrada: cria `rx.App()` e registra as 13 rotas. |
| `components/__init__.py` | 0 | Marca `components` como subpacote; arquivo vazio. |
| `components/layout.py` | 4475 | Menu, sidebar, moldura de página e componentes de apresentação. |
| `pages/__init__.py` | 0 | Marca `pages` como subpacote; arquivo vazio. |
| `pages/categorias.py` | 1010 | Página `categorias` (lista de Categorias). |
| `pages/dashboard.py` | 1841 | Página `dashboard` (visão geral). |
| `pages/estoque.py` | 1154 | Página `estoque` (situação atual). |
| `pages/fornecedores.py` | 1044 | Página `fornecedores` (lista de Fornecedores). |
| `pages/login.py` | 2093 | `LoginState` e página `login` (autenticação mockada). |
| `pages/movimentacoes.py` | 3498 | Páginas `historico`, `entrada` e `saida`. |
| `pages/perfis.py` | 1645 | Página `perfis` (perfis e matriz de permissões mockados). |
| `pages/produtos.py` | 2236 | Páginas `produtos` (lista) e `novo_produto` (formulário). |
| `pages/relatorios.py` | 1728 | Página `relatorios` (consultas gerenciais mockadas). |
| `pages/usuarios.py` | 1085 | Página `usuarios` (lista de usuários). |

Total: quinze arquivos. Os três `__init__.py` têm 0 bytes. Todos os arquivos usam UTF-8 sem BOM e terminadores CRLF; os que têm conteúdo terminam com uma quebra de linha.

Fora do inventário, por decisão desta change: a pasta `operacoes-backend-cadastros` (artefatos de outra change) e qualquer arquivo gerado, cache ou artefato de build. O estado atual não contém `__pycache__`, arquivos ocultos nem artefatos de build.

## Rotas e páginas

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

Conteúdo de cada página, todo fictício e estático:

- **`login`:** título `Sistema de Gerenciamento de Estoque`, texto `Acesso ao sistema`, campos `E-mail` e `Senha` ligados a `LoginState`, botão `Entrar` dentro de um `rx.link` para `/dashboard` e o aviso `Protótipo: autenticação totalmente mockada.`.
- **`dashboard`:** texto de apresentação; quatro cartões (`Produtos` 128 com `4 abaixo do mínimo`, `Categorias` 12, `Fornecedores` 24, `Estoque baixo` 4 com `Atenção necessária`); seção `Movimentações recentes` (tabela de 3 linhas) e seção `Alertas de estoque` (4 textos).
- **`produtos`:** busca `Buscar por código ou nome...` (largura `350px`), botão `Buscar`, link `Novo produto` para `/produtos/novo` e tabela `Produtos cadastrados` com 7 colunas e 4 linhas.
- **`novo_produto`:** formulário com `Código`, `Nome`, `Descrição` (área de texto), `Categoria` (5 opções), `Unidade de medida` (`UN`, `KG`, `L`, `CX`, `PC`) e `Estoque mínimo` (numérico); `Cancelar` volta para `/produtos` e `Salvar produto` não tem ação.
- **`categorias`:** busca por nome, botões `Buscar` e `Nova categoria`, tabela de 4 colunas e 5 linhas.
- **`fornecedores`:** busca, botões `Buscar` e `Novo fornecedor`, tabela de 5 colunas e 3 linhas.
- **`estoque`:** quatro cartões de resumo e a tabela `Situação atual` com 5 linhas.
- **`historico`:** filtros (seleção de tipo, produto, duas datas, botão `Filtrar`) e tabela de 7 colunas com 4 linhas.
- **`entrada`:** formulário com produto, quantidade, fornecedor, data, motivo pré-preenchido com `Compra` e observação; `Cancelar` para `/movimentacoes` e `Registrar entrada` sem ação.
- **`saida`:** formulário com produto, quantidade, data, motivo (`Consumo interno`, `Perda`, `Avaria`, `Doação`, `Outro`) e observação; `Cancelar` para `/movimentacoes` e `Registrar saída` sem ação.
- **`relatorios`:** três cartões, seção de período com duas datas e `Gerar relatório`, tabela `Resumo por produto` com 4 linhas e seção `Ações` com `Visualizar relatório`, `Exportar CSV` e `Exportar PDF`.
- **`usuarios`:** busca, botões `Buscar` e `Novo usuário`, tabela de 5 colunas com 4 linhas.
- **`perfis`:** tabela `Perfis cadastrados` (3 perfis) e tabela `Matriz de permissões (mock)` (10 funcionalidades).

## Contratos de layout e componentes

`components/layout.py` exporta:

| Nome | Assinatura | Comportamento |
| --- | --- | --- |
| `MENU` | lista de tuplas `(rótulo, href)` | Onze itens, na ordem: Dashboard `/dashboard`, Produtos `/produtos`, Categorias `/categorias`, Fornecedores `/fornecedores`, Estoque `/estoque`, Entradas `/movimentacoes/entradas`, Saídas `/movimentacoes/saidas`, Histórico `/movimentacoes`, Relatórios `/relatorios`, Usuários `/usuarios`, Perfis e permissões `/perfis`. |
| `nav_item` | `(label: str, href: str)` | `rx.link` de largura total com padding, borda arredondada e cor de fundo no hover. |
| `sidebar` | `()` | Coluna de `250px` com o título `Estoque`, o texto `Sistema de Gerenciamento`, um item por entrada de `MENU` e o link `Sair` para `/`. |
| `page` | `(title: str, content: rx.Component)` | Sidebar ao lado de uma área com o título, o texto fixo `Admin • Usuário mock`, um divisor e o conteúdo. |
| `card` | `(title: str, value: str, detail: str = "")` | Caixa com título, valor em destaque e, se `detail` não for vazio, texto de detalhe. |
| `section` | `(title: str, body: rx.Component)` | Caixa com título, divisor e corpo. |
| `mock_table` | `(headers: list[str], rows: list[list[str]])` | Cabeçalho e linhas construídos com `rx.hstack`; cada célula tem `flex="1"` e `min_width="120px"`; o contêiner rola na horizontal. |
| `form_input` | `(label: str, placeholder: str = "", value: str = "")` | Rótulo em negrito e `rx.input`. Não é usado por nenhuma página do estado atual. |

Todas as páginas, exceto `login`, compõem o conteúdo por `page(...)`, `section(...)`, `card(...)` e `mock_table(...)`. Os componentes não recebem callbacks nem estado.

## Estado e navegação

O único estado é `LoginState(rx.State)`, com `email` e `password` (`str`, valor inicial `""`) e os setters explícitos `set_email` e `set_password`, ligados a `on_change` dos dois campos. Os valores não são validados, enviados ou guardados fora do estado da sessão Reflex.

A navegação é feita somente por `rx.link`. Botões sem link não têm `on_click` nem `on_submit`. A tela de login não protege as demais rotas.

## Fronteira com backend e changes futuras

Esta change não lê nem escreve dados em nenhum serviço. Nenhum módulo importa cliente HTTP ou faz referência ao Xano. Os cadastros, o estoque e as permissões exibidos são literais. `operacoes-backend-cadastros` define contratos e permissões no backend; esta change não os consome e não os altera.

As diferenças de vocabulário e de matriz entre a página Perfis e os perfis do backend (Administrador, Estoquista e Usuário de consulta contra Líder, Almoxarife e Auxiliar de almoxarifado) não são resolvidas aqui. A reconciliação pertence a uma change futura de integração.

## Estratégia de verificação

Como o app não é executado durante a reconstrução, a verificação é estática e cobre:

1. Comparar a estrutura de artefatos com `operacoes-backend-cadastros`: mesmos arquivos e mesma organização de diretórios, com o nome da capability trocado.
2. Confirmar que os quinze arquivos do inventário existem no projeto atual, com os mesmos caminhos e tamanhos, e que nada relevante ficou de fora.
3. Compilar os quinze arquivos com o interpretador Python (`py_compile`).
4. Resolver todos os imports relativos para arquivo e nome realmente definidos.
5. Conferir que os treze registros de rota correspondem à tabela deste Design e que todo `href` de `MENU` e de `rx.link` aponta para rota registrada.
6. Procurar marcadores de integração externa (HTTP, Xano, `on_click`, `on_submit`) e confirmar que o único estado é `LoginState`.
7. Extrair cada bloco do apêndice e compará-lo byte a byte com o arquivo correspondente do projeto.
8. Confirmar que `operacoes-backend-cadastros` e artefatos gerados não fazem parte do inventário.

Execução do app (`reflex run` ou exportação) e verificação visual dependem de ambiente com Reflex e de configuração que o estado atual não inclui; ficam fora desta verificação.

## Validação manual posterior do NexStock integrado

**Confirmação manual do usuário:** o usuário percorreu as treze rotas originais desta change no NexStock, confirmou o carregamento e a renderização das páginas e inspecionou visualmente layout, sidebar, navegação e conteúdo. A inspeção considerou as permissões de acesso e o layout atual. Nenhuma alteração de dados foi realizada durante esses testes. Não foram fornecidos logs, capturas de tela ou resultados individuais por rota; este registro preserva somente o escopo e o resultado geral confirmados pelo usuário.

As treze rotas originais continuam implementadas com os mesmos caminhos registrados nesta change. O protótipo, entretanto, evoluiu para o NexStock integrado: a autenticação mockada foi substituída pelo login atual, os títulos antigos com sufixo `| Estoque` foram substituídos pelos títulos atuais do NexStock e os dados fictícios foram substituídos pela implementação integrada. A validação manual foi feita considerando esse estado atual, sem exigir que comportamentos originais já superados fossem restaurados.

Esta evidência posterior complementa o registro histórico da reconstrução acima: naquela etapa as tarefas 10.5 e 10.6 não haviam sido executadas; a confirmação atual do usuário sustenta sua conclusão sem alterar esse histórico.

## Riscos / Trade-offs

- **Código dentro do Design:** reproduzir o código no apêndice mantém a change autossuficiente, mas duplica o conteúdo e exige que o apêndice seja mantido igual ao projeto.
- **Dados inconsistentes preservados:** nomes de categoria e contadores divergem entre páginas; corrigi-los mudaria o projeto e foge de uma criação inicial fiel.
- **`form_input` sem uso:** mantido para não alterar o estado atual.
- **Ausência de configuração e dependências:** a change não cria o que o projeto não tem; quem aplicá-la precisa de `rxconfig.py` e do Reflex instalado por outro meio.
- **Rotas abertas:** sem sessão nem guarda de rota, a navegação direta funciona para qualquer página.
- **Convenção de caminhos:** a raiz do projeto coincide com o diretório do pacote; quem aplicar a change em outro layout precisa manter os imports relativos válidos.

## Decisões de reconstrução

- O nome da change e o da capability são `criar-projeto-inicial`.
- Caminhos relativos à raiz do projeto recebido.
- Conteúdo dos arquivos preservado sem alteração, com CRLF, no apêndice deste Design.
- Arquivos `__init__.py` vazios permanecem vazios.
- `operacoes-backend-cadastros` fica fora do inventário.
- Nenhum arquivo, funcionalidade ou configuração ausente do estado atual é criado.

## Conteúdo dos arquivos

Cada bloco abaixo reproduz o arquivo indicado exatamente como está no projeto, com terminadores CRLF. Aplicar a change consiste em criar cada arquivo com esse conteúdo, no caminho do título.

### `__init__.py`

_Arquivo vazio (0 bytes); nenhum conteúdo a reproduzir._

### `Meu_projeto.py`

```python
import reflex as rx

from .pages.login import login
from .pages.dashboard import dashboard
from .pages.produtos import produtos, novo_produto
from .pages.categorias import categorias
from .pages.fornecedores import fornecedores
from .pages.estoque import estoque
from .pages.movimentacoes import historico, entrada, saida
from .pages.usuarios import usuarios
from .pages.perfis import perfis
from .pages.relatorios import relatorios


app = rx.App()

app.add_page(login, route="/", title="Login | Estoque")
app.add_page(dashboard, route="/dashboard", title="Dashboard | Estoque")
app.add_page(produtos, route="/produtos", title="Produtos | Estoque")
app.add_page(novo_produto, route="/produtos/novo", title="Novo produto | Estoque")
app.add_page(categorias, route="/categorias", title="Categorias | Estoque")
app.add_page(fornecedores, route="/fornecedores", title="Fornecedores | Estoque")
app.add_page(estoque, route="/estoque", title="Estoque | Estoque")
app.add_page(historico, route="/movimentacoes", title="Histórico | Estoque")
app.add_page(entrada, route="/movimentacoes/entradas", title="Entrada | Estoque")
app.add_page(saida, route="/movimentacoes/saidas", title="Saída | Estoque")
app.add_page(usuarios, route="/usuarios", title="Usuários | Estoque")
app.add_page(perfis, route="/perfis", title="Perfis | Estoque")
app.add_page(relatorios, route="/relatorios", title="Relatórios | Estoque")
```

### `components/__init__.py`

_Arquivo vazio (0 bytes); nenhum conteúdo a reproduzir._

### `components/layout.py`

```python
import reflex as rx


MENU = [
    ("Dashboard", "/dashboard"),
    ("Produtos", "/produtos"),
    ("Categorias", "/categorias"),
    ("Fornecedores", "/fornecedores"),
    ("Estoque", "/estoque"),
    ("Entradas", "/movimentacoes/entradas"),
    ("Saídas", "/movimentacoes/saidas"),
    ("Histórico", "/movimentacoes"),
    ("Relatórios", "/relatorios"),
    ("Usuários", "/usuarios"),
    ("Perfis e permissões", "/perfis"),
]


def nav_item(label: str, href: str) -> rx.Component:
    return rx.link(
        label,
        href=href,
        width="100%",
        padding="0.6rem 0.8rem",
        border_radius="0.4rem",
        _hover={"background": "#f1f1f1"},
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Estoque", size="6"),
            rx.text("Sistema de Gerenciamento", size="2", color="#666"),
            rx.divider(),
            rx.vstack(
                *[nav_item(label, href) for label, href in MENU],
                width="100%",
                align="stretch",
                spacing="1",
            ),
            rx.spacer(),
            rx.link("Sair", href="/", width="100%"),
            width="100%",
            height="100%",
            align="stretch",
            spacing="3",
        ),
        width="250px",
        min_width="250px",
        min_height="100vh",
        padding="1.25rem",
        border_right="1px solid #ddd",
        background="#fafafa",
    )


def page(title: str, content: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading(title, size="7"),
                    rx.spacer(),
                    rx.text("Admin • Usuário mock", color="#666"),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                content,
                width="100%",
                align="stretch",
                spacing="5",
            ),
            padding="2rem",
            width="100%",
            min_height="100vh",
        ),
        width="100%",
        align="stretch",
        spacing="0",
    )


def card(title: str, value: str, detail: str = "") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, color="#666", size="2"),
            rx.heading(value, size="7"),
            rx.text(detail, color="#777", size="2") if detail else rx.fragment(),
            align="start",
            spacing="1",
        ),
        border="1px solid #ddd",
        border_radius="0.5rem",
        padding="1.25rem",
        flex="1",
        min_width="180px",
    )


def section(title: str, body: rx.Component) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(title, size="5"),
            rx.divider(),
            body,
            width="100%",
            align="stretch",
            spacing="3",
        ),
        border="1px solid #ddd",
        border_radius="0.5rem",
        padding="1.25rem",
        width="100%",
    )


def mock_table(headers: list[str], rows: list[list[str]]) -> rx.Component:
    header = rx.hstack(
        *[
            rx.text(h, weight="bold", flex="1", min_width="120px")
            for h in headers
        ],
        width="100%",
        padding="0.75rem",
        background="#f5f5f5",
        border_bottom="1px solid #ddd",
    )

    body = rx.vstack(
        *[
            rx.hstack(
                *[
                    rx.text(cell, flex="1", min_width="120px")
                    for cell in row
                ],
                width="100%",
                padding="0.75rem",
                border_bottom="1px solid #eee",
            )
            for row in rows
        ],
        width="100%",
        spacing="0",
    )

    return rx.box(
        header,
        body,
        width="100%",
        overflow_x="auto",
        border="1px solid #ddd",
        border_radius="0.4rem",
    )


def form_input(label: str, placeholder: str = "", value: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(label, weight="bold"),
        rx.input(value=value, placeholder=placeholder, width="100%"),
        width="100%",
        align="stretch",
        spacing="1",
    )
```

### `pages/__init__.py`

_Arquivo vazio (0 bytes); nenhum conteúdo a reproduzir._

### `pages/categorias.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def categorias() -> rx.Component:
    return page(
        "Categorias",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Nome da categoria..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Nova categoria"),
                width="100%",
            ),
            section(
                "Categorias cadastradas",
                mock_table(
                    ["ID", "Nome", "Produtos", "Status"],
                    [
                        ["1", "Alimentos", "38", "Ativa"],
                        ["2", "Bebidas", "21", "Ativa"],
                        ["3", "Materiais de limpeza", "17", "Ativa"],
                        ["4", "Eletrônicos", "12", "Ativa"],
                        ["5", "Materiais de escritório", "40", "Ativa"],
                    ],
                ),
            ),
        ),
    )
```

### `pages/dashboard.py`

```python
import reflex as rx
from ..components.layout import page, card, section, mock_table


def dashboard() -> rx.Component:
    return page(
        "Dashboard",
        rx.vstack(
            rx.text("Visão geral do estoque e das movimentações recentes.", color="#666"),
            rx.hstack(
                card("Produtos", "128", "4 abaixo do mínimo"),
                card("Categorias", "12"),
                card("Fornecedores", "24"),
                card("Estoque baixo", "4", "Atenção necessária"),
                width="100%",
                spacing="4",
                wrap="wrap",
            ),
            rx.hstack(
                section(
                    "Movimentações recentes",
                    mock_table(
                        ["Tipo", "Produto", "Quantidade", "Data", "Usuário"],
                        [
                            ["Entrada", "Arroz 5kg", "50", "22/09/2026 14:32", "Ana"],
                            ["Saída", "Café 500g", "8", "22/09/2026 13:10", "Carlos"],
                            ["Entrada", "Detergente", "30", "22/09/2026 11:45", "Ana"],
                        ],
                    ),
                ),
                section(
                    "Alertas de estoque",
                    rx.vstack(
                        rx.text("• Café 500g — atual: 6 / mínimo: 10"),
                        rx.text("• Açúcar 1kg — atual: 4 / mínimo: 8"),
                        rx.text("• Papel A4 — atual: 12 / mínimo: 20"),
                        rx.text("• Caneta azul — atual: 5 / mínimo: 15"),
                        align="start",
                    ),
                ),
                width="100%",
                align="start",
                spacing="4",
            ),
        ),
    )
```

### `pages/estoque.py`

```python
import reflex as rx
from ..components.layout import page, card, mock_table, section


def estoque() -> rx.Component:
    return page(
        "Estoque",
        rx.vstack(
            rx.hstack(
                card("Itens em estoque", "128"),
                card("Estoque normal", "124"),
                card("Abaixo do mínimo", "4"),
                card("Sem estoque", "0"),
                width="100%",
                wrap="wrap",
                spacing="4",
            ),
            section(
                "Situação atual",
                mock_table(
                    ["Código", "Produto", "Atual", "Mínimo", "Situação"],
                    [
                        ["P001", "Arroz 5kg", "50", "20", "Normal"],
                        ["P002", "Café 500g", "6", "10", "Abaixo do mínimo"],
                        ["P003", "Detergente", "30", "10", "Normal"],
                        ["P004", "Papel A4", "12", "20", "Abaixo do mínimo"],
                        ["P005", "Caneta azul", "5", "15", "Abaixo do mínimo"],
                    ],
                ),
            ),
        ),
    )
```

### `pages/fornecedores.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def fornecedores() -> rx.Component:
    return page(
        "Fornecedores",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar fornecedor..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Novo fornecedor"),
                width="100%",
            ),
            section(
                "Fornecedores cadastrados",
                mock_table(
                    ["ID", "Nome / Razão social", "Documento", "Contato", "Status"],
                    [
                        ["F001", "Distribuidora São Paulo", "12.345.678/0001-00", "(11) 99999-1111", "Ativo"],
                        ["F002", "Comercial Brasil Ltda.", "23.456.789/0001-11", "(11) 98888-2222", "Ativo"],
                        ["F003", "Office Supply", "34.567.890/0001-22", "(11) 97777-3333", "Ativo"],
                    ],
                ),
            ),
        ),
    )
```

### `pages/login.py`

```python
import reflex as rx


class LoginState(rx.State):
    email: str = ""
    password: str = ""

    def set_email(self, value: str):
        self.email = value

    def set_password(self, value: str):
        self.password = value


def login() -> rx.Component:
    return rx.center(
        rx.box(
            rx.vstack(
                rx.heading("Sistema de Gerenciamento de Estoque", size="7"),
                rx.text("Acesso ao sistema", color="#666"),
                rx.divider(),
                rx.vstack(
                    rx.text("E-mail", weight="bold"),
                    rx.input(
                        placeholder="usuario@empresa.com",
                        value=LoginState.email,
                        on_change=LoginState.set_email,
                        width="100%",
                    ),
                    rx.text("Senha", weight="bold"),
                    rx.input(
                        placeholder="••••••••",
                        type="password",
                        value=LoginState.password,
                        on_change=LoginState.set_password,
                        width="100%",
                    ),
                    rx.link(
                        rx.button("Entrar", width="100%"),
                        href="/dashboard",
                        width="100%",
                    ),
                    rx.text(
                        "Protótipo: autenticação totalmente mockada.",
                        size="2",
                        color="#777",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
                width="100%",
                align="stretch",
                spacing="4",
            ),
            width="420px",
            max_width="90vw",
            padding="2rem",
            border="1px solid #ddd",
            border_radius="0.6rem",
        ),
        min_height="100vh",
        padding="2rem",
    )
```

### `pages/movimentacoes.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def historico() -> rx.Component:
    return page(
        "Histórico de movimentações",
        rx.vstack(
            rx.hstack(
                rx.select(["Todos", "Entrada", "Saída"], placeholder="Tipo"),
                rx.input(placeholder="Produto"),
                rx.input(type="date"),
                rx.input(type="date"),
                rx.button("Filtrar"),
                width="100%",
                wrap="wrap",
            ),
            section(
                "Movimentações",
                mock_table(
                    ["ID", "Tipo", "Produto", "Qtd.", "Data/hora", "Usuário", "Motivo"],
                    [
                        ["MOV-104", "Entrada", "Arroz 5kg", "50", "22/09/2026 14:32", "Ana", "Compra"],
                        ["MOV-103", "Saída", "Café 500g", "8", "22/09/2026 13:10", "Carlos", "Consumo interno"],
                        ["MOV-102", "Entrada", "Detergente", "30", "22/09/2026 11:45", "Ana", "Compra"],
                        ["MOV-101", "Saída", "Papel A4", "5", "22/09/2026 09:20", "Carlos", "Uso administrativo"],
                    ],
                ),
            ),
        ),
    )


def entrada() -> rx.Component:
    return page(
        "Registrar entrada de estoque",
        rx.vstack(
            section(
                "Dados da entrada",
                rx.vstack(
                    rx.select(["Arroz 5kg", "Café 500g", "Detergente", "Papel A4"], placeholder="Produto"),
                    rx.input(placeholder="Quantidade", type="number"),
                    rx.select(
                        ["Distribuidora São Paulo", "Comercial Brasil Ltda.", "Office Supply"],
                        placeholder="Fornecedor",
                    ),
                    rx.input(type="date"),
                    rx.input(placeholder="Motivo", value="Compra"),
                    rx.text_area(placeholder="Observação"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button("Registrar entrada"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )


def saida() -> rx.Component:
    return page(
        "Registrar saída de estoque",
        rx.vstack(
            section(
                "Dados da saída",
                rx.vstack(
                    rx.select(["Arroz 5kg", "Café 500g", "Detergente", "Papel A4"], placeholder="Produto"),
                    rx.input(placeholder="Quantidade", type="number"),
                    rx.input(type="date"),
                    rx.select(
                        ["Consumo interno", "Perda", "Avaria", "Doação", "Outro"],
                        placeholder="Motivo",
                    ),
                    rx.text_area(placeholder="Observação"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/movimentacoes"),
                        rx.button("Registrar saída"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )
```

### `pages/perfis.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def perfis() -> rx.Component:
    return page(
        "Perfis e permissões",
        rx.vstack(
            section(
                "Perfis cadastrados",
                mock_table(
                    ["Perfil", "Descrição", "Usuários", "Permissões"],
                    [
                        ["Administrador", "Acesso administrativo", "1", "Todas"],
                        ["Estoquista", "Operações de estoque", "2", "Produtos, estoque, entradas e saídas"],
                        ["Usuário de consulta", "Somente consulta", "1", "Dashboard, estoque e relatórios"],
                    ],
                ),
            ),
            section(
                "Matriz de permissões (mock)",
                mock_table(
                    ["Funcionalidade", "Administrador", "Estoquista", "Consulta"],
                    [
                        ["Dashboard", "Sim", "Sim", "Sim"],
                        ["Usuários", "Sim", "Não", "Não"],
                        ["Produtos", "Sim", "Sim", "Não"],
                        ["Categorias", "Sim", "Sim", "Não"],
                        ["Fornecedores", "Sim", "Sim", "Não"],
                        ["Estoque", "Sim", "Sim", "Sim"],
                        ["Entrada", "Sim", "Sim", "Não"],
                        ["Saída", "Sim", "Sim", "Não"],
                        ["Histórico", "Sim", "Sim", "Sim"],
                        ["Relatórios", "Sim", "Sim", "Sim"],
                    ],
                ),
            ),
        ),
    )
```

### `pages/produtos.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def produtos() -> rx.Component:
    return page(
        "Produtos",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar por código ou nome...", width="350px"),
                rx.button("Buscar"),
                rx.spacer(),
                rx.link(rx.button("Novo produto"), href="/produtos/novo"),
                width="100%",
            ),
            section(
                "Produtos cadastrados",
                mock_table(
                    ["Código", "Nome", "Categoria", "Unidade", "Qtd.", "Mínimo", "Status"],
                    [
                        ["P001", "Arroz 5kg", "Alimentos", "UN", "50", "20", "Normal"],
                        ["P002", "Café 500g", "Alimentos", "UN", "6", "10", "Baixo"],
                        ["P003", "Detergente", "Limpeza", "UN", "30", "10", "Normal"],
                        ["P004", "Papel A4", "Escritório", "CX", "12", "20", "Baixo"],
                    ],
                ),
            ),
        ),
    )


def novo_produto() -> rx.Component:
    return page(
        "Novo produto",
        rx.vstack(
            section(
                "Dados do produto",
                rx.vstack(
                    rx.input(placeholder="Código"),
                    rx.input(placeholder="Nome"),
                    rx.text_area(placeholder="Descrição"),
                    rx.select(
                        ["Alimentos", "Bebidas", "Limpeza", "Eletrônicos", "Escritório"],
                        placeholder="Categoria",
                    ),
                    rx.select(["UN", "KG", "L", "CX", "PC"], placeholder="Unidade de medida"),
                    rx.input(placeholder="Estoque mínimo", type="number"),
                    rx.hstack(
                        rx.link(rx.button("Cancelar"), href="/produtos"),
                        rx.button("Salvar produto"),
                        spacing="3",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
            ),
        ),
    )
```

### `pages/relatorios.py`

```python
import reflex as rx
from ..components.layout import page, section, card, mock_table


def relatorios() -> rx.Component:
    return page(
        "Relatórios",
        rx.vstack(
            rx.text("Consultas gerenciais com dados fictícios para o protótipo.", color="#666"),
            rx.hstack(
                card("Entradas no período", "234", "01/09 a 22/09"),
                card("Saídas no período", "187", "01/09 a 22/09"),
                card("Produtos abaixo do mínimo", "4"),
                width="100%",
                wrap="wrap",
                spacing="4",
            ),
            section(
                "Movimentações por período",
                rx.hstack(
                    rx.input(type="date"),
                    rx.text("até"),
                    rx.input(type="date"),
                    rx.button("Gerar relatório"),
                ),
            ),
            section(
                "Resumo por produto",
                mock_table(
                    ["Produto", "Entradas", "Saídas", "Saldo atual"],
                    [
                        ["Arroz 5kg", "120", "70", "50"],
                        ["Café 500g", "45", "39", "6"],
                        ["Detergente", "80", "50", "30"],
                        ["Papel A4", "60", "48", "12"],
                    ],
                ),
            ),
            section(
                "Ações",
                rx.hstack(
                    rx.button("Visualizar relatório"),
                    rx.button("Exportar CSV"),
                    rx.button("Exportar PDF"),
                    spacing="3",
                ),
            ),
        ),
    )
```

### `pages/usuarios.py`

```python
import reflex as rx
from ..components.layout import page, mock_table, section


def usuarios() -> rx.Component:
    return page(
        "Usuários",
        rx.vstack(
            rx.hstack(
                rx.input(placeholder="Buscar por nome ou e-mail..."),
                rx.button("Buscar"),
                rx.spacer(),
                rx.button("Novo usuário"),
                width="100%",
            ),
            section(
                "Usuários cadastrados",
                mock_table(
                    ["ID", "Nome", "E-mail", "Perfil", "Status"],
                    [
                        ["U001", "Ana Souza", "ana@empresa.com", "Administrador", "Ativo"],
                        ["U002", "Carlos Lima", "carlos@empresa.com", "Estoquista", "Ativo"],
                        ["U003", "Mariana Alves", "mariana@empresa.com", "Usuário de consulta", "Ativo"],
                        ["U004", "João Silva", "joao@empresa.com", "Estoquista", "Inativo"],
                    ],
                ),
            ),
        ),
    )
```
