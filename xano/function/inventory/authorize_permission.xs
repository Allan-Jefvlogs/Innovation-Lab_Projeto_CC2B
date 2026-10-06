function "Inventory/authorize_permission" {
  description = "Resolve o perfil atual do usuário e exige o grant solicitado. O código reservado administrator exige perfil Líder."
  input {
    int user_id {
      table = "user"
    }
    text permission_code
  }
  stack {
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id", "must_change_password", "is_active"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "PROFILE_UNASSIGNED"
    }
    precondition ($user.is_active == true || $user.is_active == null) {
      error_type = "accessdenied"
      error = "USER_INACTIVE"
    }
    precondition ($user.inventory_profile_id != null) {
      error_type = "accessdenied"
      error = "PROFILE_UNASSIGNED"
    }

    precondition ($user.must_change_password != true) {
      error_type = "accessdenied"
      error = "PASSWORD_CHANGE_REQUIRED"
    }

    db.get inventory_profile {
      field_name = "id"
      field_value = $user.inventory_profile_id
    } as $profile

    precondition ($profile != null) {
      error_type = "accessdenied"
      error = "PROFILE_INVALID"
    }

    conditional {
      if ($input.permission_code == "administrator") {
        precondition ($profile.code == "administrator") {
          error_type = "accessdenied"
          error = "PERMISSION_DENIED"
        }
      }
      else {
        conditional {
          if ($profile.code != "administrator") {
            db.get inventory_permission {
              field_name = "code"
              field_value = $input.permission_code
            } as $permission

            precondition ($permission != null) {
              error_type = "standard"
              error = "PERMISSION_CATALOG_INVALID"
            }

            db.query inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $permission.id
              return = {type: "exists"}
            } as $has_grant

            precondition ($has_grant) {
              error_type = "accessdenied"
              error = "PERMISSION_DENIED"
            }
          }
        }
      }
    }
  }

  response = {profile_code: $profile.code, authorized: true}
}
