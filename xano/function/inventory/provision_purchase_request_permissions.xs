function "Inventory/provision_purchase_request_permissions" {
  description = "Adiciona ao catálogo somente os quatro códigos de Solicitações de Compras ausentes; não altera grants."
  input {
  }
  stack {
    var $requested_permissions {
      value = [
        {code: "purchase_request.read", resource: "purchase_request", action: "read"},
        {code: "purchase_request.create", resource: "purchase_request", action: "create"},
        {code: "purchase_request.cancel", resource: "purchase_request", action: "cancel"},
        {code: "purchase_request.manage", resource: "purchase_request", action: "manage"}
      ]
    }
    var $missing_permissions {
      value = []
    }
    var $created_codes {
      value = []
    }
    var $preserved_codes {
      value = []
    }

    db.transaction {
      stack {
        // Pré-valida todos os códigos antes de realizar qualquer inserção.
        foreach ($requested_permissions) {
          each as $permission_item {
            db.query inventory_permission {
              where = $db.inventory_permission.code == $permission_item.code
              return = {type: "list"}
            } as $existing_permissions

            conditional {
              if (($existing_permissions|count) > 0) {
                foreach ($existing_permissions) {
                  each as $existing_permission {
                    precondition ($existing_permission.resource == $permission_item.resource && $existing_permission.action == $permission_item.action) {
                      error_type = "standard"
                      error = "PURCHASE_REQUEST_PERMISSION_METADATA_MISMATCH"
                    }
                  }
                }

                array.push $preserved_codes {
                  value = $permission_item.code
                }
              }
            }

            conditional {
              if (($existing_permissions|count) == 0) {
                array.push $missing_permissions {
                  value = $permission_item
                }
              }
            }
          }
        }

        // Insere exclusivamente os códigos ausentes apurados na pré-verificação.
        foreach ($missing_permissions) {
          each as $permission_to_create {
            db.add inventory_permission {
              data = {
                code: $permission_to_create.code,
                resource: $permission_to_create.resource,
                action: $permission_to_create.action
              }
            } as $created_permission

            array.push $created_codes {
              value = $created_permission.code
            }
          }
        }
      }
    }
  }

  response = {
    success: true,
    permissions_created: $created_codes|count,
    created_codes: $created_codes,
    preserved_codes: $preserved_codes
  }
}
