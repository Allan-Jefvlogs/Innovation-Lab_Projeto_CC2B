query "categories/by_id/{category_id}/inactivate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int category_id
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.inactivate"}
    } as $authorization

    db.get category {
      field_name = "id"
      field_value = $input.category_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    db.transaction {
      stack {
        db.edit category {
          field_name = "id"
          field_value = $input.category_id
          data = {status: "inativo"}
        } as $category

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
            entity_type: "categoria",
            entity_id: $category.id,
            summary: "Categoria desativada.",
            changes: {before: {status: $existing.status}, after: {status: $category.status}}
          }
        } as $audit_event
      }
    }
  }

  response = $category
}
