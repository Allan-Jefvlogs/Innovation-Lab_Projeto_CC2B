table "inventory_stock" {
  auth = false

  schema {
    int id
    int product_id {
      table = "product"
    }
    decimal quantidade_disponivel filters=min:0
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "product_id"}]}
  ]
}
