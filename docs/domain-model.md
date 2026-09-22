# Domain Model — Sistema de Gerenciamento de Estoque

## 1. Visão geral do domínio

O domínio do sistema é composto por informações e processos relacionados ao gerenciamento de produtos e ao controle das movimentações de estoque de uma empresa.

Os principais conceitos do domínio são:

- Usuário;
- Perfil;
- Categoria;
- Produto;
- Fornecedor;
- Estoque;
- Movimentação de Estoque.

O modelo representa os conceitos do negócio e seus relacionamentos. Ele não define antecipadamente a estrutura física das tabelas ou a implementação do banco de dados.

---

## 2. Usuário

### Descrição

Representa uma pessoa autorizada a utilizar o sistema.

### Responsabilidade

- autenticar-se no sistema;
- acessar as funcionalidades permitidas;
- realizar operações de acordo com suas permissões;
- ser identificado como responsável pelas movimentações realizadas.

### Principais informações conceituais

- identificação;
- nome;
- e-mail;
- credenciais de acesso;
- status;
- perfil de acesso.

### Relacionamentos

- um usuário possui um perfil;
- um usuário pode realizar várias movimentações de estoque;
- cada movimentação de estoque é realizada por um usuário responsável.

---

## 3. Perfil

### Descrição

Representa um conjunto de permissões que determina quais funcionalidades podem ser acessadas por um usuário.

### Responsabilidade

Definir o nível de acesso do usuário às funcionalidades do sistema.

### Perfis iniciais

O sistema utilizará inicialmente três perfis conceituais:

- Administrador;
- Estoquista;
- Usuário de consulta.

### Relacionamentos

- um perfil pode estar associado a vários usuários;
- cada usuário possui um perfil.

### Regra estrutural

As permissões definidas pelo perfil devem ser respeitadas tanto pela interface quanto pelas regras de autorização do backend.

---

## 4. Categoria

### Descrição

Representa uma forma de classificação dos produtos.

### Responsabilidade

Organizar produtos segundo uma categoria de negócio.

### Exemplos

- Alimentos;
- Bebidas;
- Materiais de limpeza;
- Eletrônicos;
- Materiais de escritório.

### Relacionamentos

- uma categoria pode possuir vários produtos;
- um produto pertence a uma categoria.

---

## 5. Produto

### Descrição

Representa um item controlado pelo sistema de estoque.

### Responsabilidade

Armazenar as informações necessárias para identificação e controle do produto.

### Principais informações conceituais

- identificação;
- código;
- nome;
- descrição;
- categoria;
- unidade de medida;
- quantidade disponível;
- estoque mínimo;
- status.

### Relacionamentos

- um produto pertence a uma categoria;
- uma categoria pode possuir vários produtos;
- um produto pode possuir várias movimentações de estoque;
- um produto está associado ao seu estado atual de estoque;
- um produto pode estar relacionado a diferentes fornecedores por meio das operações de entrada.

---

## 6. Fornecedor

### Descrição

Representa uma empresa ou pessoa responsável pelo fornecimento de produtos à empresa.

### Responsabilidade

Identificar a origem dos produtos recebidos em operações de entrada de estoque.

### Principais informações conceituais

- identificação;
- nome ou razão social;
- documento de identificação;
- contato;
- endereço ou informações de localização;
- status.

### Relacionamentos

- um fornecedor pode participar de várias entradas de estoque;
- uma entrada de estoque pode estar associada a um fornecedor.

---

## 7. Estoque

### Descrição

Representa o estado atual da disponibilidade dos produtos controlados pelo sistema.

### Responsabilidade

Permitir o acompanhamento das quantidades disponíveis e da situação do estoque em relação aos níveis definidos.

### Principais informações conceituais

- quantidade atual;
- quantidade mínima;
- situação do estoque.

### Estados conceituais

Um produto poderá estar, por exemplo:

- com estoque normal;
- abaixo do estoque mínimo;
- sem estoque.

### Relacionamentos

- cada produto possui uma situação de estoque;
- entradas de estoque aumentam a quantidade disponível;
- saídas de estoque reduzem a quantidade disponível;
- a situação do estoque é influenciada pelas movimentações registradas.

---

## 8. Movimentação de Estoque

### Descrição

Representa uma operação que altera a quantidade disponível de um produto.

A movimentação poderá ser de dois tipos principais:

- Entrada;
- Saída.

### Responsabilidade

Registrar as alterações realizadas no estoque e permitir o acompanhamento do histórico das operações.

### Principais informações conceituais

- identificação;
- tipo da movimentação;
- produto;
- quantidade;
- data e hora;
- usuário responsável;
- motivo;
- observação;
- fornecedor, quando aplicável.

### Relacionamentos

- uma movimentação pertence a um produto;
- um produto pode possuir várias movimentações;
- uma movimentação é realizada por um usuário;
- um usuário pode realizar várias movimentações;
- uma entrada pode estar associada a um fornecedor;
- uma saída pode registrar um motivo para a operação.

---

## 9. Relacionamentos principais

O relacionamento entre os principais conceitos pode ser representado da seguinte forma:

```text
PERFIL
  │
  │ possui
  ▼
USUÁRIO
  │
  │ realiza
  ▼
MOVIMENTAÇÃO DE ESTOQUE
  │
  │ movimenta
  ▼
PRODUTO
  │
  ├──────── pertence a ────────► CATEGORIA
  │
  └──────── possui estado ─────► ESTOQUE

FORNECEDOR
  │
  │ participa de
  ▼
ENTRADA DE ESTOQUE
  │
  └──────── movimenta ─────────► PRODUTO