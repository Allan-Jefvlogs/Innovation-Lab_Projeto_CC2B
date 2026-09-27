function "Inventory/bootstrap_first_leader" {
  description = "Bootstrap privado e de uso único do primeiro perfil administrator. Invocável somente por operador no Xano, sem endpoint HTTP."
  input {
    int user_id {
      table = "user"
    }
  }

  stack {
    db.get inventory_profile {
      field_name = "code"
      field_value = "administrator"
    } as $administrator_profile

    precondition ($administrator_profile != null) {
      error_type = "standard"
      error = "BOOTSTRAP_PROFILES_NOT_SEEDED"
    }

    db.get inventory_bootstrap_state {
      field_name = "code"
      field_value = "first_leader"
    } as $bootstrap_state

    precondition ($bootstrap_state == null) {
      error_type = "accessdenied"
      error = "BOOTSTRAP_ALREADY_COMPLETED"
    }

    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id"]
    } as $target_user

    precondition ($target_user != null && $target_user.inventory_profile_id == null) {
      error_type = "inputerror"
      error = "BOOTSTRAP_TARGET_INVALID"
    }

    db.query user {
      where = $db.user.inventory_profile_id == $administrator_profile.id
      return = {type: "exists"}
    } as $administrator_already_assigned

    precondition (!$administrator_already_assigned) {
      error_type = "accessdenied"
      error = "BOOTSTRAP_ALREADY_COMPLETED"
    }

    try_catch {
      try {
        db.transaction {
          stack {
            db.get inventory_bootstrap_state {
              field_name = "code"
              field_value = "first_leader"
            } as $locked_bootstrap_state

            precondition ($locked_bootstrap_state == null) {
              error_type = "accessdenied"
              error = "BOOTSTRAP_ALREADY_COMPLETED"
            }

            db.query user {
              where = $db.user.inventory_profile_id == $administrator_profile.id
              return = {type: "exists"}
            } as $leader_already_assigned

            precondition (!$leader_already_assigned) {
              error_type = "accessdenied"
              error = "BOOTSTRAP_ALREADY_COMPLETED"
            }

            db.get user {
              field_name = "id"
              field_value = $input.user_id
              output = ["id", "inventory_profile_id"]
            } as $locked_target_user

            precondition ($locked_target_user != null && $locked_target_user.inventory_profile_id == null) {
              error_type = "inputerror"
              error = "BOOTSTRAP_TARGET_INVALID"
            }

            db.edit user {
              field_name = "id"
              field_value = $locked_target_user.id
              data = {inventory_profile_id: $administrator_profile.id}
            } as $assigned_leader

            db.add inventory_bootstrap_state {
              data = {
                code: "first_leader",
                first_leader_user_id: $assigned_leader.id,
                completed_at: now
              }
            } as $completed_bootstrap
          }
        }
      }
      catch {
        db.get inventory_bootstrap_state {
          field_name = "code"
          field_value = "first_leader"
        } as $bootstrap_completed_after_error

        conditional {
          if ($bootstrap_completed_after_error != null) {
            throw {
              name = "BOOTSTRAP_ALREADY_COMPLETED"
              value = "BOOTSTRAP_ALREADY_COMPLETED"
            }
          }
          else {
            throw {
              name = "BOOTSTRAP_TRANSACTION_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = {
    completed: true,
    user_id: $assigned_leader.id,
    profile_code: "administrator"
  }
}
