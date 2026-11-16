# Spec Delta: identidade visual

## MODIFIED Requirements

### Requirement: Paleta global centralizada

O sistema MUST centralizar as cores de marca em tokens reutilizáveis e aplicar um tema claro consistente nas páginas existentes. A paleta de referência é verde menta `#BEEADB`, verde sálvia `#8DBAA6`, amarelo pêssego `#F7C683`, rosa pêssego `#F0CBB9` e taupe `#9E8D85`, com estes papéis: sálvia para elementos estruturais e navegação; menta para estados positivos; amarelo pêssego para estados de atenção; rosa para destaques secundários; e taupe para elementos neutros. Os acentos devem ser usados de forma moderada e manter leitura adequada. Esta capability define cores globais, não a disposição específica dos componentes do Dashboard. Aplica-se às telas existentes de login e alteração de senha, navegação e layout compartilhado, Dashboard, produtos, categorias, fornecedores, estoque, entradas e saídas, usuários, perfis, relatórios e reposição de estoque. A referência a movimentações não recria uma página de Histórico de Movimentações removida do produto.

#### Scenario: Aplicação da paleta
- **WHEN** uma página existente abrangida por esta capability é renderizada
- **THEN** as cores da interface seguem os tokens globais e a cor sálvia identifica os elementos estruturais e de navegação
- **AND** estados positivos usam menta, estados de atenção usam amarelo pêssego, destaques secundários usam rosa e elementos neutros usam taupe
- **AND** fundos de destaque usam tons suaves sem prejudicar a leitura.
