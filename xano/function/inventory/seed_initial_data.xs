function "Inventory/seed_initial_data" {
  description = "Provisiona idempotentemente perfis, catálogo de permissões e matriz inicial aprovada; não atribui perfil a usuários."
  input {
  }
  stack {
    var $profiles {
      value = [
        {code: "administrator", display_name: "Líder"},
        {code: "stockkeeper", display_name: "Almoxarife"},
        {code: "read_only", display_name: "Auxiliar de almoxarifado"}
      ]
    }

    var $permissions {
      value = [
        {code: "category.read", resource: "category", action: "read"},
        {code: "category.create", resource: "category", action: "create"},
        {code: "category.update", resource: "category", action: "update"},
        {code: "category.inactivate", resource: "category", action: "inactivate"},
        {code: "product.read", resource: "product", action: "read"},
        {code: "product.create", resource: "product", action: "create"},
        {code: "product.update", resource: "product", action: "update"},
        {code: "product.inactivate", resource: "product", action: "inactivate"},
        {code: "supplier.read", resource: "supplier", action: "read"},
        {code: "supplier.create", resource: "supplier", action: "create"},
        {code: "supplier.update", resource: "supplier", action: "update"},
        {code: "supplier.inactivate", resource: "supplier", action: "inactivate"},
        {code: "stock.read", resource: "stock", action: "read"},
        {code: "stock.entry", resource: "stock", action: "entry"},
        {code: "stock.exit", resource: "stock", action: "exit"},
        {code: "movement.read", resource: "movement", action: "read"},
        {code: "report.read", resource: "report", action: "read"}
      ]
    }

    var $initial_grants {
      value = [
        {profile_code: "stockkeeper", permission_code: "category.read"},
        {profile_code: "stockkeeper", permission_code: "product.read"},
        {profile_code: "stockkeeper", permission_code: "product.create"},
        {profile_code: "stockkeeper", permission_code: "product.update"},
        {profile_code: "stockkeeper", permission_code: "product.inactivate"},
        {profile_code: "stockkeeper", permission_code: "supplier.read"},
        {profile_code: "stockkeeper", permission_code: "supplier.create"},
        {profile_code: "stockkeeper", permission_code: "supplier.update"},
        {profile_code: "stockkeeper", permission_code: "supplier.inactivate"},
        {profile_code: "read_only", permission_code: "category.read"},
        {profile_code: "read_only", permission_code: "product.read"},
        {profile_code: "read_only", permission_code: "supplier.read"},
        {profile_code: "stockkeeper", permission_code: "stock.read"},
        {profile_code: "read_only", permission_code: "stock.read"},
        {profile_code: "stockkeeper", permission_code: "movement.read"},
        {profile_code: "read_only", permission_code: "movement.read"},
        {profile_code: "stockkeeper", permission_code: "report.read"},
        {profile_code: "read_only", permission_code: "report.read"},
        {profile_code: "stockkeeper", permission_code: "stock.entry"},
        {profile_code: "stockkeeper", permission_code: "stock.exit"}
      ]
    }

    db.transaction {
      stack {
        foreach ($profiles) {
          each as $profile_item {
            db.query inventory_profile {
              where = $db.inventory_profile.code == $profile_item.code
              return = {type: "single"}
            } as $existing_profile

            conditional {
              if ($existing_profile == null) {
                db.add inventory_profile {
                  data = {
                    code: $profile_item.code,
                    display_name: $profile_item.display_name,
                    permission_revision: 1
                  }
                } as $created_profile
              }
            }
          }
        }

        foreach ($permissions) {
          each as $permission_item {
            db.query inventory_permission {
              where = $db.inventory_permission.code == $permission_item.code
              return = {type: "single"}
            } as $existing_permission

            conditional {
              if ($existing_permission == null) {
                db.add inventory_permission {
                  data = {
                    code: $permission_item.code,
                    resource: $permission_item.resource,
                    action: $permission_item.action
                  }
                } as $created_permission
              }
            }
          }
        }

        foreach ($initial_grants) {
          each as $grant_item {
            db.get inventory_profile {
              field_name = "code"
              field_value = $grant_item.profile_code
            } as $grant_profile

            db.get inventory_permission {
              field_name = "code"
              field_value = $grant_item.permission_code
            } as $grant_permission

            db.query inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $grant_profile.id && $db.inventory_profile_permission.permission_id == $grant_permission.id
              return = {type: "single"}
            } as $existing_grant

            conditional {
              if ($existing_grant == null) {
                db.add inventory_profile_permission {
                  data = {
                    profile_id: $grant_profile.id,
                    permission_id: $grant_permission.id
                  }
                } as $created_grant
              }
            }
          }
        }
      }
    }
  }

  response = {success: true, profiles: 3, permissions: 17, editable_grants: 20}
}
