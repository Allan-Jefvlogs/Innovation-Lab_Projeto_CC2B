// Query all PAPEL records
query papel verb=GET {
  api_group = "Event Logs"

  input {
  }

  stack {
    db.query PAPEL {
      return = {type: "list"}
    } as $papel
  }

  response = $papel
  guid = "Hn9oH6afV6uQ3HcgrEW2OZEi5eE"
}