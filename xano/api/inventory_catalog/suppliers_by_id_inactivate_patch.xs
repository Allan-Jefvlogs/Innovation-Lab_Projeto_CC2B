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

    db.transaction {
      stack {
        db.edit supplier {
          field_name = "id"
          field_value = $input.supplier_id
          data = {status: "inativo"}
        } as $supplier

        db.get "user" {
          field_name = "id"
          field_value = $auth.id
          output = ["id", "name"]
        } as $audit_actor

        precondition ($audit_actor != null) {
          error_type = "accessdenied"
          error = "AUDIT_ACTOR_NOT_FOUND"
        }

        db.add inventory_audit_log {
          data = {
            actor_user_id: $audit_actor.id,
            actor_name: $audit_actor.name,
            action_type: "inativado",
            entity_type: "fornecedor",
            entity_id: $supplier.id,
            summary: "Fornecedor desativado.",
            changes: {before: {status: $existing.status}, after: {status: $supplier.status}}
          }
        } as $audit_event
      }
    }
  }

  response = $supplier
}
