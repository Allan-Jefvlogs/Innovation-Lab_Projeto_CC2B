table "inventory_movement" {
  auth = false

  schema {
    int id
    int product_id {
      table = "product"
    }
    enum tipo {
      values = ["entrada", "saida"]
    }
    decimal quantidade filters=min:0
    timestamp data_hora
    int user_id {
      table = "user"
    }
    int? supplier_id? {
      table = "supplier"
    }
    text motivo filters=trim
    text? observacao?
    int? purchase_request_id? {
      table = "purchase_request"
    }
    text? chave_recebimento?
    text? unidade_medida?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "product_id"}, {name: "data_hora", op: "desc"}]}
    {type: "btree", field: [{name: "data_hora", op: "desc"}, {name: "id", op: "desc"}]}
    {type: "btree", field: [{name: "user_id"}]}
    {type: "btree", field: [{name: "supplier_id"}]}
    {type: "btree", field: [{name: "purchase_request_id"}]}
    {type: "btree|unique", field: [{name: "chave_recebimento"}]}
  ]
}
