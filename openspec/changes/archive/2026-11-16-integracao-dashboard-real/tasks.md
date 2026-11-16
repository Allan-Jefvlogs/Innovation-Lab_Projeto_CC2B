## 1. Auditoria

- [x] 1.1 Conferir os contratos locais de listagem e paginação necessários aos indicadores e às seções do Dashboard.
- [x] 1.2 Mapear grants, chamadas iniciais, cache de sessão e limite do coordenador.

## 2. Integração

- [x] 2.1 Carregar contagens reais de Produtos ativos, Categorias e Fornecedores por metadados paginados.
- [x] 2.2 Carregar contagem e amostra de Produtos abaixo do mínimo e as movimentações recentes.
- [x] 2.3 Integrar autorização dinâmica, estados de erro, indisponibilidade e recuperação manual.
- [x] 2.4 Reutilizar o cache existente com isolamento por sessão, TTL limitado e invalidação após escritas bem-sucedidas.
- [x] 2.5 Atualizar a apresentação sem dados de protótipo nem gráficos sem fonte real.

## 3. Verificação

- [x] 3.1 Adicionar testes simulados de respostas, permissões, isolamento, cache, falhas e ausência de dados fictícios.
- [x] 3.2 Executar suíte automatizada, compilação Reflex e `git diff --check`.
- [x] 3.3 Confirmar no navegador os indicadores reais, alertas, movimentações recentes e os estados sem permissão/erro; aceitação manual informada pelo usuário em 2026-11-16 para Dashboard com dados reais e com restrições de acesso/falhas. Não foram fornecidas capturas, medições ou logs independentes.
