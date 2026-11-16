query "users/by_id/{user_id}/reset_password" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id filters=min:1
    text password filters=min:8 {
      sensitive = true
    }
    text confirm_password {
      sensitive = true
    }
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.password == $input.confirm_password) {
      error_type = "inputerror"
      error = "PASSWORD_MISMATCH"
    }

    db.get "user" {
      field_name = "id"
      field_value = $input.user_id
      output = ["id"]
    } as $target_user
    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }

    db.transaction {
      stack {
        db.edit "user" {
          field_name = "id"
          field_value = $target_user.id
          enforce_hidden_fields = false
          data = {password: $input.password, must_change_password: true}
        } as $updated_user

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
            action_type: "credencial_redefinida",
            entity_type: "usuario",
            entity_id: $target_user.id,
            summary: "Credencial de usuário redefinida; nenhum valor de credencial foi armazenado."
          }
        } as $audit_event
      }
    }
  }

  response = {user_id: $target_user.id, must_change_password: true}
}
