query "suppliers/by_id/{supplier_id}" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int supplier_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.read"}
    } as $authorization

    db.get supplier {
      field_name = "id"
      field_value = $input.supplier_id
    } as $supplier

    precondition ($supplier != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }
  }

  response = $supplier
}
