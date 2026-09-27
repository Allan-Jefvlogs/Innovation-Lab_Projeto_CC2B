query "categories" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text status?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.read"}
    } as $authorization

    precondition ($input.status == null || $input.status == "ativo" || $input.status == "inativo") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query category {
      where = $db.category.status ==? $input.status
      sort = {id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $categories
  }

  response = $categories
}
