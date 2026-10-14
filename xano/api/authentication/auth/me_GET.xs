// Get the user record belonging to the authentication token
query "auth/me" verb=GET {
  api_group = "Authentication"
  auth = "user"

  input {
  }

  stack {
    // Get the user record based on the auth ID
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = [
        "id"
        "created_at"
        "name"
        "email"
        "account_id"
        "role"
        "inventory_profile_id"
        "must_change_password"
        "is_active"
      ]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "USER_NOT_FOUND"
    }
    precondition ($user.is_active !== false) {
      error_type = "accessdenied"
      error = "USER_INACTIVE"
    }

    db.get inventory_profile {
      field_name = "id"
      field_value = $user.inventory_profile_id
    } as $profile

    var $effective_permissions {
      value = []
    }

    conditional {
      if ($profile != null) {
        conditional {
          if ($profile.code == "administrator") {
            db.query inventory_permission {
              sort = {code: "asc"}
              return = {type: "list"}
            } as $all_permissions

            foreach ($all_permissions) {
              each as $permission {
                array.push $effective_permissions {
                  value = $permission.code
                }
              }
            }
          }
          else {
            db.query inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $profile.id
              return = {type: "list"}
            } as $profile_grants

            foreach ($profile_grants) {
              each as $grant {
                db.get inventory_permission {
                  field_name = "id"
                  field_value = $grant.permission_id
                } as $permission

                conditional {
                  if ($permission != null) {
                    array.push $effective_permissions {
                      value = $permission.code
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  
    // Create an event log for get user record
    function.run "Getting Started Template/create_event_log" {
      input = {
        user_id   : $user.id
        account_id: $user.account_id
        action    : "get_auth_user"
        metadata  : $user
      }
    } as $event_log
  }

  response = $user
    |set:"inventory_profile_code":$profile.code
    |set:"permission_codes":$effective_permissions
  tags = ["xano:quick-start"]
  guid = "R_7_R-8SS4-WfM3GS4ieMO0_vls"
}
