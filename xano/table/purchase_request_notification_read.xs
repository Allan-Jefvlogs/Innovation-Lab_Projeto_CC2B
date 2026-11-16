table "purchase_request_notification_read" {
  auth = false

  schema {
    int id
    int user_id { table = "user" }
    int history_id { table = "purchase_request_history" }
    timestamp read_at?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "user_id"}, {name: "history_id"}]}
    {type: "btree", field: [{name: "history_id"}]}
  ]
}
