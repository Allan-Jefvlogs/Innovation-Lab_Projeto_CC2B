# Design: identidade visual com paleta natural

## Decisões

- Os tokens ficam em `Meu_projeto/components/theme.py`, evitando repetir os códigos da paleta.
- O tema global Reflex permanece claro, com acento Jade e base Sage do sistema de temas Radix; os elementos de marca usam os códigos fornecidos pelo grupo.
- O verde sálvia é a cor das ações principais e da marca. O verde menta identifica fundos positivos e destaques suaves. O amarelo pêssego destaca estoque baixo. O rosa pêssego é usado em elementos secundários. Taupe e tons derivados cobrem bordas e texto secundário.
- Textos sobre superfícies coloridas usam tons escuros derivados para manter contraste. Vermelho fica reservado a erro, saída e estados de falha.
- A mudança é somente visual: estados, chamadas, rotas, grants e autorização backend não são alterados.

## Aplicação

- Login e alteração de senha: fundos neutros, marca em sálvia/menta, campos com bordas taupe suaves e foco sálvia.
- Sidebar em verde salvia com navegacao escura; area de trabalho quase branca para descanso visual.
- Estoque e Dashboard: menta para estado normal/positivo; pêssego para abaixo do mínimo; vermelho semântico para ausência de estoque quando já representada como alerta crítico.
- Formulários, filtros e tabelas: tema claro compartilhado, cabeçalhos discretos e feedbacks positivos/de atenção com rótulos e ícones existentes.

- Paineis alternam fundos menta, pessego e rosa suave, com faixas de titulo na cor correspondente; indicadores usam cor, texto e icone para manter o significado claro. Tabelas usam cabecalho menta e divisorias taupe. Formularios e modais permanecem claros, com foco salvia.

## Compatibilidade e riscos

O tema Radix oferece nomes de cores discretos próximos da paleta; os componentes com cores explícitas usam os tokens do projeto para manter fidelidade. A compilação Reflex deve confirmar a compatibilidade das propriedades globais. A confirmação visual final depende de inspeção no navegador em desktop e viewport estreito.

## Reconciliação com a capability oficial

O delta altera somente `Paleta global centralizada`, usando o nome canônico e preservando o cenário oficial de aplicação da paleta. A alteração torna explícito o mapeamento semântico já definido nesta change e a abrangência das telas, sem criar uma capability paralela.

Os requisitos originais `Estados semanticamente legíveis` e `Preservação funcional e responsiva` não precisam de deltas: estão cobertos, respectivamente, por `Estados visuais acessíveis` e `Identidade visual preserva funcionamento e responsividade` em `openspec/specs/identidade-visual/spec.md`. Seus cenários oficiais permanecem inalterados. Essa correspondência evita reaplicar requisitos equivalentes durante o futuro arquivamento.

A abrangência inclui login e alteração de senha, navegação e layout compartilhado, Dashboard, produtos, categorias, fornecedores, estoque, entradas e saídas, usuários e perfis, relatórios e reposição. A menção a movimentações não reintroduz a antiga página de Histórico de Movimentações.
