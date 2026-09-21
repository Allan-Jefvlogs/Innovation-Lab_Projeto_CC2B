// Add TRANSACAO record
query transacao verb=POST {
  api_group = "Event Logs"

  input {
    dblink {
      table = "TRANSACAO"
    }
  }

  stack {
    db.add TRANSACAO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $transacao
  }

  response = $transacao
  guid = "TbgDEFEE4UQCKKE3jKu3dZF_toc"
}