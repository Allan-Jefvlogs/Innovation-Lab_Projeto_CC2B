table "inventory_profile_permission" {
  auth = false

  schema {
    int id
    int profile_id {
      table = "inventory_profile"
    }
    int permission_id {
      table = "inventory_permission"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "profile_id"}, {name: "permission_id"}]}
    {type: "btree", field: [{name: "permission_id"}]}
  ]
}
