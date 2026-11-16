table "inventory_audit_log" {
  auth = false

  schema {
    int id
    timestamp occurred_at?=now
    int actor_user_id {
      table = "user"
    }
    text actor_name
    text action_type
    text entity_type
    int? entity_id?
    text summary
    json? changes?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "occurred_at", op: "desc"}, {name: "id", op: "desc"}]}
    {type: "btree", field: [{name: "actor_user_id"}, {name: "occurred_at", op: "desc"}]}
    {type: "btree", field: [{name: "action_type"}, {name: "occurred_at", op: "desc"}]}
    {type: "btree", field: [{name: "entity_type"}, {name: "occurred_at", op: "desc"}]}
  ]
}
