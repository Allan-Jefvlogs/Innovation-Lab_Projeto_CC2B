// Query all STATUS_CLIENTE records
query status_cliente verb=GET {
  api_group = "Event Logs"

  input {
  }

  stack {
    db.query STATUS_CLIENTE {
      return = {type: "list"}
    } as $status_cliente
  }

  response = $status_cliente
  guid = "FdBMwTZlPjx_uo0YCm6EoPwg-y4"
}