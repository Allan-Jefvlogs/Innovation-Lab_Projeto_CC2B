table "inventory_profile" {
  auth = false

  schema {
    int id
    text code
    text display_name
    int permission_revision?=1 filters=min:1
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "code"}]}
  ]
}
