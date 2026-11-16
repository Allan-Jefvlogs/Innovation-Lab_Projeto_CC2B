query "users/by_id/{user_id}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id filters=min:1
    text name filters=trim
    email email filters=trim|lower
    int inventory_profile_id filters=min:1
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    db.get "user" {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id"]
    } as $target_user
    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }
    precondition ($input.name != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.user_id != $auth.id || $input.inventory_profile_id == $target_user.inventory_profile_id) {
      error_type = "accessdenied"
      error = "IMMUTABLE_PROFILE"
    }

    db.get inventory_profile {
      field_name = "id"
      field_value = $input.inventory_profile_id
    } as $profile
    precondition ($profile != null) {
      error_type = "inputerror"
      error = "PROFILE_INVALID"
    }

    db.query "user" {
      where = $db.user.email == $input.email && $db.user.id != $input.user_id
      return = {type: "exists"}
    } as $duplicate
    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_EMAIL"
    }

    db.transaction {
      stack {
        try_catch {
          try {
            db.edit "user" {
              field_name = "id"
              field_value = $input.user_id
              data = {
                name: $input.name,
                email: $input.email,
                inventory_profile_id: $profile.id
              }
            } as $updated_user
          }
          catch {
            db.query "user" {
              where = $db.user.email == $input.email && $db.user.id != $input.user_id
              return = {type: "exists"}
            } as $duplicate_after_write
            precondition (!$duplicate_after_write) {
              error_type = "inputerror"
              error = "DUPLICATE_EMAIL"
            }
            throw {
              name = "USER_UPDATE_FAILED"
              value = "USER_UPDATE_FAILED"
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
            entity_type: "usuario",
            entity_id: $updated_user.id,
            summary: "Cadastro de usuário atualizado; valores pessoais foram omitidos do evento."
          }
        } as $audit_event
      }
    }
  }

  response = {
    id: $updated_user.id,
    name: $updated_user.name,
    email: $updated_user.email,
    inventory_profile_id: $updated_user.inventory_profile_id,
    profile_name: $profile.display_name
  }
}
