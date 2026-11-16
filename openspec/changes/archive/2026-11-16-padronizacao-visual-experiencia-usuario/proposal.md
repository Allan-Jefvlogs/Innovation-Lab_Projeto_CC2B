# Proposta: padronização visual e experiência do usuário

## Problema

As telas operacionais usam feedbacks de sucesso, formulários e diálogos com apresentações diferentes. Alguns textos exibem detalhes de implementação ao usuário, e as operações de estoque não resumem os dados confirmados de forma consistente.

## Objetivo

Padronizar esses elementos com os componentes e tokens existentes do NextStock, sem alterar regras de negócio, permissões, contratos de API ou operações remotas.

## Escopo

- Criar um componente reutilizável de confirmação visual de sucesso, exibido somente depois de uma resposta válida.
- Aplicar o componente a criações, edições, mudanças de status e cancelamentos autorizados.
- Melhorar a apresentação e a linguagem dos diálogos de justificativa.
- Harmonizar dimensões, alinhamento e responsividade dos formulários existentes.
- Resumir entradas e saídas confirmadas com os dados retornados pelo servidor, sem calcular saldos presumidos.
- Revisar mensagens visíveis nas páginas afetadas, preservando mensagens importantes de validação, segurança e falha.
- Documentar a página `/recuperar-senha` como demonstração visual, sem iniciar um fluxo real de recuperação.

## Fora de escopo

- Alterar XanoScripts, endpoints, contratos, dados, permissões, regras de negócio ou autenticação.
- Enviar e-mails, gerar tokens, consultar ou armazenar solicitações de recuperação, ou alterar senhas pela página demonstrativa.
- Modificar o envio de e-mail, Dashboard, compras e recebimentos além da apresentação de justificativas e confirmações já existentes.
- Adicionar dependências ou executar operações de escrita remotas.
