// Query all ENDERECO records
query endereco verb=GET {
  api_group = "Event Logs"

  input {
  }

  stack {
    db.query ENDERECO {
      return = {type: "list"}
    } as $endereco
  }

  response = $endereco
  guid = "6s-ZThGascIereqfWBy-1zCa4mw"
}