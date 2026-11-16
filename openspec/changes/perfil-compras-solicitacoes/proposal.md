# Perfil Compras e gestão de solicitações

## Problema

O NexStock já permite criar, consultar e cancelar solicitações, mas não oferece uma área exclusiva para a equipe de Compras nem um escritor dos eventos gerenciais de `purchase_request_history`. O login atual direciona todos ao Dashboard e a Reposição exige `stock.read`, incompatível com o acesso restrito do novo perfil.

## Objetivo

Criar o perfil `compras` e a área **Compras solicitadas**, com consulta e detalhe, transições gerenciais controladas pelo Xano e cancelamento pelas regras existentes. Manter as demais áreas inacessíveis a esse perfil, inclusive por URL direta e por seus endpoints protegidos.

## Decisão vigente: entrega acadêmica

O uso previsto é uma apresentação com um único operador alterando compras por vez. O PATCH local usa db.get e db.edit nativos com comparação do status lido, mantendo atualização e histórico em db.transaction. Não oferece garantia contra atualizações simultâneas. Versão, reivindicação UNIQUE, Lock avançado e testes concorrentes não são requisitos desta entrega. Autenticação, grants, isolamento de leitura, transições, justificativa, histórico e validação funcional no Xano Free continuam obrigatórios.

## Escopo

- Provisionar seletivamente perfil, código `purchase_request.status.update` e grants do módulo, sem privilégios administrativos gerais.
- Adaptar login, guards, menu e matriz de perfis sem criar outro sistema de autorização.
- Reutilizar listagem, detalhe, histórico e cancelamento; restringir no Xano a leitura própria/global conforme os grants.
- Criar contrato Xano local para atualização de status com validação de transições, ator autenticado e histórico na mesma transação.
- Preparar listagem, detalhe, seletor com salvamento automático e feedback fiel ao estado confirmado pelo servidor.
- Reutilizar o histórico persistido como origem das notificações já especificadas em `dashboard-funcional`.

## Fora do escopo

Publicar no Xano, alterar registros reais, enviar e-mails, executar dispatcher, conceder grants a usuários automaticamente, criar eventos na Auditoria geral, permitir seleção manual de `recebimento_parcial`/`concluida` ou implementar o recebimento vinculado ao estoque. A change `dashboard-funcional` não será alterada.

## Resultado desta etapa

Implementação local preparada para revisão e dry-run seletivo, sem publicação ou execução de provisionamento. A liberação para demonstração depende dos testes funcionais autorizados descritos em publicacao-academica.md.
