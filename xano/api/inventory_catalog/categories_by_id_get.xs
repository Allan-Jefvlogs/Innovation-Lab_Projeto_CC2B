query "categories/by_id/{category_id}" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int category_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.read"}
    } as $authorization

    db.get category {
      field_name = "id"
      field_value = $input.category_id
    } as $category

    precondition ($category != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }
  }

  response = $category
}
