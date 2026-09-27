table "inventory_permission_audit" {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    int actor_user_id {
      table = "user"
    }
    int target_profile_id {
      table = "inventory_profile"
    }
    int revision_before
    int revision_after
    json permissions_added
    json permissions_removed
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "target_profile_id"}, {name: "revision_before"}]}
    {type: "btree", field: [{name: "target_profile_id"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "actor_user_id"}, {name: "created_at", op: "desc"}]}
  ]
}
