query "products/by_id/{product_id}" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int product_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.read"}
    } as $authorization

    db.get product {
      field_name = "id"
      field_value = $input.product_id
    } as $product

    precondition ($product != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }
  }

  response = $product
}
