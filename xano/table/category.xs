table "category" {
  auth = false

  schema {
    int id
    text nome
    enum status?="ativo" {
      values = ["ativo", "inativo"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "nome"}]}
  ]
  guid = "FFsPejxcxcfZBlTsIoNcQ_zCkcQ"
}
