query "categories/by_id/{category_id}/activate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int category_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.update"}
    } as $authorization

    db.get category {
      field_name = "id"
      field_value = $input.category_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    db.edit category {
      field_name = "id"
      field_value = $input.category_id
      data = {status: "ativo"}
    } as $category
  }

  response = $category
}
