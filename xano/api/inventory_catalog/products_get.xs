query "products" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text status?
    int categoria_id?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.read"}
    } as $authorization

    precondition ($input.status == null || $input.status == "ativo" || $input.status == "inativo") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query product {
      where = $db.product.status ==? $input.status && $db.product.categoria_id ==? $input.categoria_id
      sort = {id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $products
  }

  response = $products
}
