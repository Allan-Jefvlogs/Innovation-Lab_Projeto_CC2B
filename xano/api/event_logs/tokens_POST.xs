// Add TOKENS record
query tokens verb=POST {
  api_group = "Event Logs"

  input {
    dblink {
      table = "TOKENS"
    }
  }

  stack {
    db.add TOKENS {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $tokens
  }

  response = $tokens
  guid = "Ows0klTf872q-J5fn6PNWoaUpqs"
}