query "suppliers/by_id/{supplier_id}/inactivate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int supplier_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.inactivate"}
    } as $authorization

    db.get supplier {
      field_name = "id"
      field_value = $input.supplier_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    db.edit supplier {
      field_name = "id"
      field_value = $input.supplier_id
      data = {status: "inativo"}
    } as $supplier
  }

  response = $supplier
}
