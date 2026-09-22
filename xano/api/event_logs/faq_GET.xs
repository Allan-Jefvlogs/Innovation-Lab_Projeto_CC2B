// Query all FAQ records
query faq verb=GET {
  api_group = "Event Logs"

  input {
  }

  stack {
    db.query FAQ {
      return = {type: "list"}
    } as $faq
  }

  response = $faq
  guid = "WBGV5HSUl4t45gdwufSR44EYVsI"
}