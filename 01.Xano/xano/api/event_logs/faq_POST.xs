// Add FAQ record
query faq verb=POST {
  api_group = "Event Logs"

  input {
    dblink {
      table = "FAQ"
    }
  }

  stack {
    db.add FAQ {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $faq
  }

  response = $faq
  guid = "7HomE6R7wcWtA2rI-8MW3q8pFiU"
}