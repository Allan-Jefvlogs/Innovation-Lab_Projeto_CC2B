# Tasks

## 1. Preparar e confirmar escopo de criação

- [x] 1.1 Conferir a Specification desta change com `design.md` e a proposal.
- [x] 1.2 Inventariar os arquivos do projeto atual e confirmar os quinze arquivos do Design, com caminhos e tamanhos.
- [x] 1.3 Confirmar que `operacoes-backend-cadastros`, arquivos gerados, caches e artefatos de build ficam fora do inventário.
- [x] 1.4 Confirmar que o projeto atual não contém `rxconfig.py`, arquivo de dependências, `assets/`, `.gitignore`, README nem testes, e que a change não os cria.

## 2. Criar a estrutura de pacotes

- [x] 2.1 Criar `__init__.py` vazio na raiz do projeto.
- [x] 2.2 Criar `components/__init__.py` vazio.
- [x] 2.3 Criar `pages/__init__.py` vazio.

## 3. Criar o layout compartilhado

- [x] 3.1 Criar `components/layout.py` com `MENU` de onze itens e `nav_item`.
- [x] 3.2 Implementar `sidebar` com título, subtítulo, itens do menu e link `Sair` para `/`.
- [x] 3.3 Implementar `page(title, content)` com sidebar, título, texto fixo `Admin • Usuário mock`, divisor e conteúdo.
- [x] 3.4 Implementar `card`, `section` e `mock_table`.
- [x] 3.5 Implementar `form_input`, mantendo-o sem uso pelas páginas, como no estado atual.

## 4. Criar a tela de login

- [x] 4.1 Criar `pages/login.py` com `LoginState` (`email`, `password`, `set_email`, `set_password`).
- [x] 4.2 Implementar a página `login` sem sidebar, com campos ligados ao estado e o aviso `Protótipo: autenticação totalmente mockada.`.
- [x] 4.3 Implementar `Entrar` como link para `/dashboard`, sem validação de credenciais.

## 5. Criar as páginas de cadastros

- [x] 5.1 Criar `pages/produtos.py` com `produtos` (busca, `Novo produto` para `/produtos/novo`, tabela de 4 linhas).
- [x] 5.2 Implementar `novo_produto` com os seis campos, `Cancelar` para `/produtos` e `Salvar produto` sem ação.
- [x] 5.3 Criar `pages/categorias.py` com busca, `Nova categoria` e tabela de 5 linhas.
- [x] 5.4 Criar `pages/fornecedores.py` com busca, `Novo fornecedor` e tabela de 3 linhas.

## 6. Criar as páginas de estoque e movimentações

- [x] 6.1 Criar `pages/estoque.py` com quatro cartões e a tabela `Situação atual`.
- [x] 6.2 Criar `pages/movimentacoes.py` com `historico` (filtros e tabela de 4 linhas).
- [x] 6.3 Implementar `entrada` com motivo pré-preenchido `Compra` e `Cancelar` para `/movimentacoes`.
- [x] 6.4 Implementar `saida` com os cinco motivos e `Cancelar` para `/movimentacoes`.

## 7. Criar páginas gerenciais e administrativas

- [x] 7.1 Criar `pages/dashboard.py` com quatro cartões, movimentações recentes e alertas de estoque.
- [x] 7.2 Criar `pages/relatorios.py` com cartões, período, resumo por produto e botões de ação sem efeito.
- [x] 7.3 Criar `pages/usuarios.py` com busca, `Novo usuário` e tabela de 4 linhas.
- [x] 7.4 Criar `pages/perfis.py` com a tabela de perfis e a matriz de permissões identificada como mock.

## 8. Criar o ponto de entrada e registrar rotas

- [x] 8.1 Criar `Meu_projeto.py` importando `reflex as rx` e as funções de página por imports relativos.
- [x] 8.2 Criar `app = rx.App()` e registrar as treze rotas com os títulos `<Nome> | Estoque`.
- [x] 8.3 Confirmar que todo `href` de `MENU` e de links de navegação corresponde a rota registrada.

## 9. Aplicar limites de escopo

- [x] 9.1 Confirmar que nenhum módulo faz chamada HTTP, referencia o Xano ou persiste dados.
- [x] 9.2 Confirmar que `LoginState` é o único estado e que nenhum botão sem link declara `on_click` ou `on_submit`.
- [x] 9.3 Confirmar que nenhuma página calcula ou altera saldo, filtra dados, exporta arquivos ou registra movimentações.
- [x] 9.4 Confirmar que os dados fictícios foram preservados como estão, inclusive as inconsistências entre páginas descritas na proposal.

## 10. Verificar o resultado e revisar os artefatos

- [x] 10.1 Comparar a estrutura desta change com `operacoes-backend-cadastros`: arquivos, diretórios, codificação e terminadores de linha.
- [x] 10.2 Compilar os quinze arquivos com `py_compile` e resolver todos os imports relativos.
- [x] 10.3 Extrair cada bloco do apêndice do Design e confirmar igualdade byte a byte com o arquivo do projeto.
- [x] 10.4 Revisar especificação, cobertura de cenários e conteúdo dos artefatos; não executar sincronização, commit nem Archive nesta change.
- [x] 10.5 Executar o app com o Reflex (`reflex run` ou exportação) e percorrer as treze rotas.
- [x] 10.6 Verificar visualmente layout, sidebar e tabelas no navegador.

## Apply review execution notes

- A verificação foi estática. O Reflex não está instalado no ambiente da reconstrução e não havia acesso à rede para instalá-lo; por isso as tarefas 10.5 e 10.6 não foram executadas e nenhuma execução foi simulada.
- O projeto atual não contém `rxconfig.py` nem arquivo de dependências. Executar o app depende de configuração externa a esta change, e a versão do Reflex não é definida.
- `form_input` é definido em `components/layout.py` e não é usado por nenhuma página; foi preservado.
- Os dados fictícios apresentam inconsistências entre páginas (nomes de categoria e contadores do Dashboard); foram preservados sem correção.
- A matriz de permissões da página Perfis é ilustrativa e usa nomes de perfil diferentes dos aprovados em `operacoes-backend-cadastros`; a reconciliação fica para uma change de integração.
- O conteúdo dos arquivos está reproduzido no apêndice do `design.md`, com CRLF, e foi comparado byte a byte com o projeto antes da entrega.
