# Project Overview — Sistema de Gerenciamento de Estoque

## 1. Visão geral

O Sistema de Gerenciamento de Estoque será uma aplicação destinada ao controle de produtos e das movimentações de estoque de uma empresa.

O sistema permitirá o cadastro e a consulta de produtos, categorias e fornecedores, o registro de entradas e saídas de estoque, o acompanhamento dos níveis de estoque, a consulta do histórico de movimentações e a disponibilização de informações gerenciais.

O acesso às funcionalidades será controlado de acordo com os perfis e permissões dos usuários.

O projeto será desenvolvido de forma incremental, utilizando OpenSpec para especificação e organização das mudanças e ferramentas de desenvolvimento assistido por Inteligência Artificial como apoio ao processo.

---

## 2. Problema

Empresas que trabalham com produtos precisam manter informações atualizadas sobre seu estoque e controlar as movimentações realizadas.

Quando essas informações não são centralizadas, pode ser difícil identificar a quantidade disponível de cada produto, acompanhar entradas e saídas, verificar produtos com estoque reduzido e identificar quais usuários realizaram determinadas operações.

O sistema tem como objetivo centralizar essas informações, facilitando o controle do estoque e estabelecendo diferentes níveis de acesso às funcionalidades conforme o perfil de cada usuário.

---

## 3. Objetivos

### 3.1 Objetivo geral

Desenvolver um sistema para gerenciamento de produtos e controle das movimentações de estoque de uma empresa.

### 3.2 Objetivos específicos

- Permitir o cadastro e a consulta de produtos.
- Organizar produtos por categorias.
- Permitir o cadastro e a consulta de fornecedores.
- Registrar entradas de estoque.
- Registrar saídas de estoque.
- Permitir o acompanhamento do estoque atual.
- Permitir o acompanhamento do estoque mínimo definido para os produtos.
- Manter histórico das movimentações realizadas.
- Permitir o gerenciamento de usuários.
- Controlar o acesso às funcionalidades conforme os perfis e permissões.
- Disponibilizar informações gerenciais por meio de dashboard e relatórios.
- Manter o desenvolvimento organizado de forma incremental utilizando OpenSpec.

---

## 4. Público-alvo / usuários

O sistema será destinado a empresas que necessitam controlar seus produtos e movimentações de estoque.

Os principais usuários do sistema serão:

### Administrador

Responsável pelo gerenciamento geral do sistema, incluindo usuários, perfis, produtos, categorias, fornecedores, movimentações e informações gerenciais, de acordo com as permissões definidas.

### Estoquista

Responsável principalmente pelo controle operacional do estoque, incluindo consulta de produtos, registro de entradas, registro de saídas e consulta das movimentações.

### Usuário de consulta

Responsável pela consulta das informações disponibilizadas pelo sistema, sem acesso às operações de alteração e movimentação quando essas permissões não estiverem atribuídas ao seu perfil.

As permissões detalhadas de cada perfil serão especificadas nas respectivas mudanças do projeto.

---

## 5. Escopo

### 5.1 Funcionalidades incluídas no escopo inicial

- Autenticação de usuários.
- Gerenciamento de usuários.
- Gerenciamento de perfis e permissões.
- Cadastro e consulta de categorias.
- Cadastro e consulta de produtos.
- Cadastro e consulta de fornecedores.
- Consulta do estoque atual.
- Definição e acompanhamento de estoque mínimo.
- Registro de entradas de estoque.
- Registro de saídas de estoque.
- Consulta do histórico de movimentações.
- Dashboard com informações resumidas do estoque.
- Relatórios relacionados às movimentações e à situação do estoque.

### 5.2 Funcionalidades fora do escopo inicial

Não fazem parte do escopo inicial:

- emissão de notas fiscais;
- controle financeiro;
- processamento de pagamentos;
- sistema completo de vendas;
- integração com bancos;
- integração com transportadoras;
- aplicativo mobile;
- gerenciamento de múltiplos depósitos ou múltiplas filiais.

Novas funcionalidades poderão ser avaliadas posteriormente e, quando aprovadas, deverão ser tratadas como mudanças específicas no OpenSpec.

---

## 6. Principais funcionalidades

### 6.1 Autenticação

Permitir que usuários autorizados acessem o sistema de acordo com suas credenciais e permissões.

### 6.2 Usuários e perfis

Permitir o gerenciamento dos usuários do sistema e a definição de seus perfis de acesso.

### 6.3 Categorias

Permitir a organização dos produtos em categorias.

### 6.4 Produtos

Permitir o cadastro, consulta e manutenção das informações dos produtos controlados pelo estoque.

### 6.5 Fornecedores

Permitir o cadastro e a consulta dos fornecedores relacionados às entradas de produtos.

### 6.6 Entradas de estoque

Permitir o registro da entrada de produtos no estoque, mantendo informações sobre o produto, a quantidade, a data, o usuário responsável e, quando aplicável, o fornecedor.

### 6.7 Saídas de estoque

Permitir o registro da saída de produtos do estoque, mantendo informações sobre o produto, a quantidade, a data, o usuário responsável e o motivo da operação.

### 6.8 Consulta de estoque

Permitir visualizar a situação atual dos produtos e suas respectivas quantidades disponíveis.

### 6.9 Estoque mínimo

Permitir definir um nível mínimo de estoque para os produtos e identificar situações em que a quantidade disponível esteja abaixo desse nível.

### 6.10 Histórico de movimentações

Permitir consultar as operações de entrada e saída realizadas no sistema.

### 6.11 Dashboard

Apresentar informações resumidas e relevantes sobre a situação do estoque, como quantidade de produtos, movimentações recentes e produtos abaixo do estoque mínimo.

### 6.12 Relatórios

Disponibilizar informações consolidadas relacionadas ao estoque e às movimentações registradas.

---

## 7. Requisitos e restrições importantes

- O acesso às funcionalidades deverá respeitar o perfil e as permissões do usuário.
- As regras de autorização deverão ser aplicadas no backend.
- Operações de entrada e saída deverão ser registradas.
- O sistema deverá manter o histórico das movimentações realizadas.
- Uma saída de estoque não deverá permitir quantidade superior ao estoque disponível.
- As movimentações deverão identificar o usuário responsável pela operação.
- O desenvolvimento deverá ocorrer de forma incremental.
- Mudanças relevantes deverão ser especificadas antes da implementação.
- O sistema deverá respeitar as tecnologias definidas para o projeto.
- As decisões permanentes do projeto deverão ser registradas na documentação apropriada.

---

## 8. Arquitetura tecnológica

### 8.1 Frontend

**Reflex**

O Reflex será utilizado como tecnologia exclusiva para implementação do frontend da aplicação.

### 8.2 Backend

**Xano**

O Xano será utilizado como backend da aplicação, sendo responsável pela lógica de negócio, persistência dos dados e implementação das regras de autorização.

### 8.3 Especificação e organização das mudanças

**OpenSpec**

O OpenSpec será utilizado para especificar, planejar, revisar e organizar o desenvolvimento incremental do sistema.

### 8.4 Inteligência Artificial

**GitHub Copilot**

O GitHub Copilot será utilizado como agente de Inteligência Artificial para auxiliar na análise, planejamento e implementação do projeto.

### 8.5 Conhecimento especializado para Xano

**Xano Developer MCP**

O Xano Developer MCP será utilizado para fornecer ao agente documentação, referências e recursos de validação relacionados ao XanoScript.

### 8.6 Controle de versão

**Git e GitHub**

O Git será utilizado para controle de versão local e histórico das alterações. O GitHub será utilizado como repositório remoto e para colaboração.

---

## 9. Princípios de desenvolvimento

- Desenvolver o sistema de forma incremental.
- Utilizar OpenSpec para organizar mudanças relevantes.
- Consultar a documentação do projeto antes de realizar alterações significativas.
- Utilizar o Xano Developer MCP para consultar e validar informações relacionadas ao XanoScript quando necessário.
- Respeitar a arquitetura tecnológica definida para o projeto.
- Reutilizar código existente quando apropriado.
- Evitar duplicação desnecessária.
- Evitar alterações não relacionadas à mudança atual.
- Revisar as alterações realizadas com apoio da Inteligência Artificial.
- Utilizar Git para registrar o histórico das alterações.

---

## 10. Segurança e integridade

O sistema deverá possuir controle de acesso baseado em perfis e permissões.

As regras de autorização deverão ser aplicadas no backend, não dependendo exclusivamente da interface frontend.

As operações de estoque deverão ser registradas para permitir o acompanhamento das movimentações realizadas.

As informações necessárias para identificar o usuário responsável por uma movimentação deverão ser mantidas no registro da operação.

A integridade das informações de estoque deverá ser preservada durante as operações de entrada e saída.

---

## 11. Estratégia de desenvolvimento

O sistema será desenvolvido de forma incremental.

As funcionalidades serão divididas em mudanças menores, planejáveis e verificáveis, utilizando o ciclo definido pelo OpenSpec:

Explore → Propose → Review → Apply → Archive.

Cada mudança deverá ser analisada antes da implementação e revisada antes de ser considerada concluída.

Decisões que alterem significativamente o domínio, a arquitetura ou o escopo deverão ser avaliadas pelo grupo antes de sua implementação.

---

## 12. Fonte de verdade e documentação

Os documentos de contexto do projeto serão utilizados como referência durante o desenvolvimento.

Serão utilizados:

- `AGENTS.md` para as regras de trabalho dos agentes.
- `docs/project-overview.md` para a visão geral do projeto.
- `docs/domain-model.md` para o modelo conceitual do domínio.
- `openspec/config.yaml` para o contexto, regras e orientações dos workflows do OpenSpec.
- `openspec/specs/` para as especificações consolidadas do sistema.
- `openspec/changes/` para as mudanças em desenvolvimento.

As mudanças permanentes no projeto deverão ser refletidas na documentação correspondente.