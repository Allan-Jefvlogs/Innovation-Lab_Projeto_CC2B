table "purchase_request_history" {
  auth = false

  schema {
    int id
    int purchase_request_id {
      table = "purchase_request"
    }
    int actor_user_id {
      table = "user"
    }
    enum evento {
      values = ["criada", "status_alterado", "cancelada", "rejeitada", "email_status_alterado", "recebimento_registrado"]
    }
    text? justificativa?
    json dados?
    timestamp data_evento?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "purchase_request_id"}, {name: "data_evento", op: "desc"}]}
    {type: "btree", field: [{name: "actor_user_id"}, {name: "data_evento", op: "desc"}]}
    {type: "btree", field: [{name: "evento"}, {name: "data_evento", op: "desc"}]}
  ]
}
