# Dashboard funcional

## Problema

O Dashboard contém uma busca sem função, um sino sem notificações reais, um menu de usuário sem ações e um gráfico que ainda depende de dados demonstrativos. A troca voluntária de senha também não possui fluxo próprio com validação da senha atual.

## Objetivo

Tornar esses elementos funcionais usando Reflex e os contratos do Xano, mantendo o layout aprovado, as permissões existentes e os dados reais. A mudança não publica scripts nem altera o workspace Xano.

## Escopo

- Remover o campo de busca inoperante.
- Exibir notificações internas derivadas exclusivamente de eventos persistidos em `purchase_request_history`, com recibo de leitura individual, escopo por solicitante/gestor e marco de ativação.
- Tornar o menu de usuário clicável com alteração voluntária de senha e o logout já existente.
- Usar saudação com primeiro nome autenticado e horário de São Paulo.
- Usar o gráfico de linhas existente com contagem de operações: últimos 7 dias (padrão), 30 dias ou 12 meses, agregado junto às cinco movimentações recentes. Preservar cores, dimensões, legenda e eixos.
- Reutilizar cache por sessão, coordenador e chamadas existentes; sem polling.

## Fora do escopo

Publicação no Xano, migração remota, disparo de e-mail, dispatcher, eventos de compra não persistidos, alteração de permissões, revogação remota de todos os tokens, mudanças de design não aprovadas e alterações nos endpoints de relatórios.

## Resultado esperado

Contratos e interface preparados localmente, com testes estruturais e simulados. A integração só é ativada após publicação seletiva e configuração do marco de notificações no Xano. Testes locais não comprovam execução, isolamento ou revogação de tokens no Xano remoto.
