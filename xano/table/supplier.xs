table "supplier" {
  auth = false

  schema {
    int id
    text nome_razao_social
    enum tipo_documento {
      values = ["CPF", "CNPJ"]
    }
    text documento
    text contato?
    text endereco?
    enum status?="ativo" {
      values = ["ativo", "inativo"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "documento"}]}
  ]
  guid = "L_j12qeUGVm5TN-1zOQ9coyea1U"
}
