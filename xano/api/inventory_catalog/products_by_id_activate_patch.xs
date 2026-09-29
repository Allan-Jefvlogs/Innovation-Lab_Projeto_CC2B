query "products/by_id/{product_id}/activate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int product_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.update"}
    } as $authorization

    db.get product {
      field_name = "id"
      field_value = $input.product_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    db.edit product {
      field_name = "id"
      field_value = $input.product_id
      data = {status: "ativo"}
    } as $product
  }

  response = $product
}
