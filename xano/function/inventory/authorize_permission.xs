function "Inventory/authorize_permission" {
  description = "Resolve o perfil atual e exige um dos grants solicitados. administrator mantém acesso integral protegido."
  input {
    int user_id {
      table = "user"
    }
    text permission_code
    text alternate_permission_code?
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
    precondition ($user.is_active !== false) {
      error_type = "accessdenied"
      error = "USER_INACTIVE"
    }
    precondition ($user.inventory_profile_id != null) {
      error_type = "accessdenied"
      error = "PROFILE_UNASSIGNED"
    }

    precondition ($user.must_change_password == false || $user.must_change_password == null) {
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

            var $has_primary_grant {
              value = false
            }

            conditional {
              if ($permission != null) {
                db.query inventory_profile_permission {
                  where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $permission.id
                  return = {type: "exists"}
                } as $has_primary_grant_result

                var.update $has_primary_grant {
                  value = $has_primary_grant_result
                }
              }
            }

            var $has_alternate_grant {
              value = false
            }
            var $alternate_permission_found {
              value = false
            }

            conditional {
              if ($input.alternate_permission_code != null) {
                db.get inventory_permission {
                  field_name = "code"
                  field_value = $input.alternate_permission_code
                } as $alternate_permission_result

                conditional {
                  if ($alternate_permission_result != null) {
                    var.update $alternate_permission_found {
                      value = true
                    }

                    db.query inventory_profile_permission {
                      where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $alternate_permission_result.id
                      return = {type: "exists"}
                    } as $has_alternate_grant_result

                    var.update $has_alternate_grant {
                      value = $has_alternate_grant_result
                    }
                  }
                }
              }
            }

            precondition ($permission != null || $alternate_permission_found) {
              error_type = "standard"
              error = "PERMISSION_CATALOG_INVALID"
            }

            precondition ($has_primary_grant || $has_alternate_grant) {
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
