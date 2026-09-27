table "inventory_permission" {
  auth = false

  schema {
    int id
    text code
    text resource
    text action
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "code"}]}
  ]
}
