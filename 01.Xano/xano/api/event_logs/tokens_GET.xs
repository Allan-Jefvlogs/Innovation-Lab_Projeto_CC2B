// Query all TOKENS records
query tokens verb=GET {
  api_group = "Event Logs"

  input {
  }

  stack {
    db.query TOKENS {
      return = {type: "list"}
    } as $tokens
  }

  response = $tokens
  guid = "m9jXVB3qdWva4Q0SOMhS8jIP_Vg"
}