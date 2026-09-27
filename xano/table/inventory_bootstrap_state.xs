table "inventory_bootstrap_state" {
  auth = false

  schema {
    int id
    text code
    int first_leader_user_id {
      table = "user"
    }
    timestamp completed_at?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "code"}]}
  ]
}
