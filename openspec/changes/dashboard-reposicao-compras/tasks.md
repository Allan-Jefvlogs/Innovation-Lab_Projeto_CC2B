## 1. Preparação

- [ ] 1.1 Aguardar revisão/publicação dos contratos de `backend-solicitacoes-compras` e concluir separadamente a validação manual de `integracao-dashboard-real`.
- [ ] 1.2 Confirmar grants de leitura e criação definidos no catálogo Xano, sem presumir nem conceder grants.
- [x] 1.3 Aprovar regra visual das duas listas, estados sem acesso e cancelamento de rascunho versus pedido persistido.

## 2. Interface compartilhada e Dashboard

- [x] 2.1 Extrair marca geométrica do Login para componente compartilhado e reutilizá-la na sidebar sem alteração visual.
- [x] 2.2 Remover apenas os cards de Categorias e Fornecedores e manter Produtos ativos, Movimentações recentes e Alertas.
- [ ] 2.3 Integrar contagem de estoque insuficiente incluindo saldo zero, somente Produtos ativos.
- [x] 2.4 Integrar contagem de solicitações abertas sujeita a `purchase_request.read`.
- [x] 2.5 Tornar o card Estoque insuficiente navegável para Reposição e ajustar as colunas Quantidade/Data.

## 3. Reposição e solicitações

- [x] 3.1 Implementar seções distintas “A solicitar” e “Compra já solicitada”, sem duplicidade.
- [x] 3.2 Implementar elegibilidade visual e ação Solicitar compra sujeitas a sessão e grants atuais.
- [x] 3.3 Implementar formulário com Produto preenchido, quantidade sugerida/editável, urgência e descarte local de rascunho.
- [x] 3.4 Conectar criação idempotente ao endpoint publicado; tratar ambiguidade sem gerar nova chave automaticamente.
- [x] 3.5 Apresentar estado de e-mail pendente sem afirmar envio.
- [x] 3.6 Implementar acompanhamento e cancelamento persistido em fluxo separado, conforme endpoint e autorização publicados.

## 4. Cache e verificação

- [x] 4.1 Reutilizar coordenador/cache existentes com isolamento de sessão, TTL limitado e invalidação após escrita confirmada.
- [x] 4.2 Adicionar testes simulados de indicadores, elegibilidade, listas, grants, idempotência da UI, cache, erros e 429.
- [x] 4.3 Executar suíte automatizada, compilação Reflex, OpenSpec strict e `git diff --check`.
- [ ] 4.4 Validar visualmente Dashboard, duas listas, formulário e acompanhamento com Xano publicado e usuário de teste autorizado.
- [ ] 4.5 Validar fluxos reais de criação, cancelamento, rejeição e recebimento, registrando que somente Entrada confirmada altera saldo.

## 5. Destinatário de e-mail — preparação local

- [x] 5.1 Adicionar ao formulário o campo de destinatário, validação e texto explicativo, sem alterar o layout aprovado.
- [x] 5.2 Manter o payload legado enquanto a flag estiver desativada; bloquear endereço preenchido nesse modo e preparar assinatura idempotente com o destinatário quando habilitado.
- [x] 5.3 Testar compatibilidade antiga/nova, validação, estado em andamento e invalidação de cache sem chamadas reais.
- [ ] 5.4 Validar no navegador após publicar o POST de transição: fluxo legado sem campo, formulário habilitado com endereço persistido e pedidos antigos com NULL; manter a obrigatoriedade backend para etapa posterior.
- [ ] 5.5 Implementar envio original e aviso de cancelamento somente após desenho/aprovação de entrega e validação de envio inicial confirmado.
