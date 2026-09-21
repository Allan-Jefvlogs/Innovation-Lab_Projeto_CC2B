// Delete STATUS_CLIENTE record.
query "status_cliente/{status_cliente_id}" verb=DELETE {
  api_group = "Event Logs"

  input {
    int status_cliente_id? filters=min:1
  }

  stack {
    db.del STATUS_CLIENTE {
      field_name = "id"
      field_value = $input.status_cliente_id
    }
  }

  response = null
  guid = "YO-VP88uJQYszEuY6v71x53NEt0"
}