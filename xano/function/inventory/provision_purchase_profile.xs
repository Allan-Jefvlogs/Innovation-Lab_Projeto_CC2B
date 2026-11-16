function "Inventory/provision_purchase_profile" {
  description = "Provisionamento interno seletivo do perfil Compras; nao atribui usuarios."
  input {
  }
  stack {
    db.transaction {
      stack {
        db.get inventory_profile {
          field_name = "code"
          field_value = "compras"
        } as $existing_profile

        var $profile { value = null }

        conditional {
          if ($existing_profile == null) {
            db.add inventory_profile {
              data = {code: "compras", display_name: "Compras", permission_revision: 1}
            } as $created_profile
            var.update $profile { value = $created_profile }
          }
          else {
            precondition ($existing_profile.display_name == "Compras") {
              error_type = "inputerror"
              error = "PURCHASE_PROFILE_CONFLICT"
            }
            var.update $profile { value = $existing_profile }
          }
        }

        var $required_permissions {
          value = [
            {code: "purchase_request.read", resource: "purchase_request", action: "read"},
            {code: "purchase_request.manage", resource: "purchase_request", action: "manage"},
            {code: "purchase_request.status.update", resource: "purchase_request", action: "status.update"}
          ]
        }

        foreach ($required_permissions) {
          each as $required {
            db.get inventory_permission {
              field_name = "code"
              field_value = $required.code
            } as $existing_permission

            var $permission { value = null }

            conditional {
              if ($existing_permission == null) {
                db.add inventory_permission {
                  data = {
                    code: $required.code,
                    resource: $required.resource,
                    action: $required.action
                  }
                } as $created_permission
                var.update $permission { value = $created_permission }
              }
              else {
                precondition ($existing_permission.resource == $required.resource && $existing_permission.action == $required.action) {
                  error_type = "inputerror"
                  error = "PURCHASE_PERMISSION_CONFLICT"
                }
                var.update $permission { value = $existing_permission }
              }
            }

            db.query inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $permission.id
              return = {type: "exists"}
            } as $grant_exists
            conditional {
              if (!$grant_exists) {
                db.add inventory_profile_permission {
                  data = {profile_id: $profile.id, permission_id: $permission.id}
                } as $new_grant
              }
            }
          }
        }

        db.query inventory_profile_permission {
          where = $db.inventory_profile_permission.profile_id == $profile.id
          return = {type: "count"}
        } as $grant_count
        precondition ($grant_count == 3) {
          error_type = "inputerror"
          error = "PURCHASE_PROFILE_EXTRA_GRANTS"
        }
      }
    }
  }
  response = {profile_code: "compras", grant_count: $grant_count}
}
