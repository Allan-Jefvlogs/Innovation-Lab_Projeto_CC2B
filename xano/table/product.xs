table "product" {
  auth = false

  schema {
    int id
    text codigo
    text nome
    text descricao?
    int categoria_id {
      table = "category"
    }
    text unidade_medida
    decimal estoque_minimo filters=min:0
    enum status?="ativo" {
      values = ["ativo", "inativo"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "codigo"}]}
  ]
  guid = "UvSbWOipkJW_l3AvuF0hjORoxg0"
}
