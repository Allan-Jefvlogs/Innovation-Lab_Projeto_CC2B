query "categories/by_id/{category_id}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int category_id
    text nome?
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

    precondition ($input.nome != null) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query category {
      where = $db.category.nome == $input.nome && $db.category.id != $input.category_id
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_VALUE"
    }

    db.transaction {
      stack {
        try_catch {
          try {
            db.edit category {
              field_name = "id"
              field_value = $input.category_id
              data = {nome: $input.nome}
            } as $category
          }
          catch {
            db.query category {
              where = $db.category.nome == $input.nome && $db.category.id != $input.category_id
              return = {type: "exists"}
            } as $duplicate_after_write

            conditional {
              if ($duplicate_after_write) {
                throw {
                  name = "DUPLICATE_VALUE"
                  value = "DUPLICATE_VALUE"
                }
              }
              else {
                throw {
                  name = "CATEGORY_UPDATE_FAILED"
                  value = $error.message
                }
              }
            }
          }
        }

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
            action_type: "atualizado",
            entity_type: "categoria",
            entity_id: $category.id,
            summary: "Categoria atualizada.",
            changes: {before: {nome: $existing.nome}, after: {nome: $category.nome}}
          }
        } as $audit_event
      }
    }
  }

  response = $category
}
