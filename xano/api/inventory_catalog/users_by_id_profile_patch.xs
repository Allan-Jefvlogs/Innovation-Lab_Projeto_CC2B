query "users/by_id/{user_id}/profile" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id {
      table = "user"
    }
    text profile_code
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.user_id != $auth.id) {
      error_type = "accessdenied"
      error = "IMMUTABLE_PROFILE"
    }

    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id"]
    } as $target_user

    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }

    db.get inventory_profile {
      field_name = "code"
      field_value = $input.profile_code
    } as $profile

    precondition ($profile != null) {
      error_type = "inputerror"
      error = "PROFILE_INVALID"
    }

    db.transaction {
      stack {
        db.edit user {
          field_name = "id"
          field_value = $target_user.id
          data = {inventory_profile_id: $profile.id}
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
            action_type: "perfil_alterado",
            entity_type: "usuario",
            entity_id: $updated_user.id,
            summary: "Perfil de usuário alterado.",
            changes: {inventory_profile_id: {before: $target_user.inventory_profile_id, after: $profile.id}}
          }
        } as $audit_event
      }
    }
  }

  response = {
    user_id: $target_user.id,
    profile_code: $profile.code,
    display_name: $profile.display_name
  }
}
