query "users/by_id/{user_id}/inactivate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id filters=min:1
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.user_id != $auth.id) {
      error_type = "accessdenied"
      error = "SELF_INACTIVATION_FORBIDDEN"
    }

    db.get "user" {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id", "is_active"]
    } as $target_user
    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }

    db.get "inventory_profile" {
      field_name = "code"
      field_value = "administrator"
      output = ["id"]
    } as $leader_profile
    precondition ($leader_profile != null) {

      error = "PROFILE_INVALID"
    }

    conditional {
      if ($target_user.inventory_profile_id == $leader_profile.id) {
        db.query "user" {
          where = $db.user.inventory_profile_id == $leader_profile.id && $db.user.is_active !== false && $db.user.id != $target_user.id
          return = {type: "exists"}
        } as $has_other_active_leader
        precondition ($has_other_active_leader) {
          error_type = "accessdenied"
          error = "LAST_LEADER_REQUIRED"
        }
      }
    }

    db.transaction {
      stack {
        db.edit "user" {
          field_name = "id"
          field_value = $target_user.id
          data = {is_active: false}
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
            action_type: "inativado",
            entity_type: "usuario",
            entity_id: $target_user.id,
            summary: "Usuário desativado.",
            changes: {is_active: {before: true, after: false}}
          }
        } as $audit_event
      }
    }
  }

  response = {user_id: $target_user.id, is_active: false}
}
