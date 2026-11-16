query "products/by_id/{product_id}/inactivate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int product_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.inactivate"}
    } as $authorization

    db.get product {
      field_name = "id"
      field_value = $input.product_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    db.transaction {
      stack {
        db.edit product {
          field_name = "id"
          field_value = $input.product_id
          data = {status: "inativo"}
        } as $product

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
            entity_type: "produto",
            entity_id: $product.id,
            summary: "Produto desativado.",
            changes: {before: {status: $existing.status}, after: {status: $product.status}}
          }
        } as $audit_event
      }
    }
  }

  response = $product
}
