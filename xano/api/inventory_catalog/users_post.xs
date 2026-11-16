query "users" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text name filters=trim
    email email filters=trim|lower
    text password filters=min:8 {
      sensitive = true
    }
    text confirm_password {
      sensitive = true
    }
    int inventory_profile_id filters=min:1
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.name != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.password == $input.confirm_password) {
      error_type = "inputerror"
      error = "PASSWORD_MISMATCH"
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
      where = $db.user.email == $input.email
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
            db.add "user" {
              enforce_hidden_fields = false
              data = {
                name: $input.name,
                email: $input.email,
                password: $input.password,
                role: "member",
                inventory_profile_id: $profile.id,
                must_change_password: true
              }
            } as $created_user
          }
          catch {
            db.query "user" {
              where = $db.user.email == $input.email
              return = {type: "exists"}
            } as $duplicate_after_write
            precondition (!$duplicate_after_write) {
              error_type = "inputerror"
              error = "DUPLICATE_EMAIL"
            }
            throw {
              name = "USER_CREATE_FAILED"
              value = "USER_CREATE_FAILED"
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
            action_type: "criado",
            entity_type: "usuario",
            entity_id: $created_user.id,
            summary: "Usuário cadastrado.",
            changes: {inventory_profile_id: $created_user.inventory_profile_id}
          }
        } as $audit_event
      }
    }
  }

  response = {
    id: $created_user.id,
    name: $created_user.name,
    email: $created_user.email,
    inventory_profile_id: $created_user.inventory_profile_id,
    profile_name: $profile.display_name
  }
}
