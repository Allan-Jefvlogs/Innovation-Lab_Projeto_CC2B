workflow_test "operacoes_backend_cadastros_authorization_matrix" {
  datasource = "test"
  tags = ["operacoes-backend-cadastros", "authorization", "fixtures"]

  stack {
    function.call "Inventory/seed_initial_data" as $seed_result

    db.get inventory_profile {
      field_name = "code"
      field_value = "administrator"
    } as $administrator

    db.get inventory_profile {
      field_name = "code"
      field_value = "stockkeeper"
    } as $stockkeeper

    db.get inventory_profile {
      field_name = "code"
      field_value = "read_only"
    } as $read_only

    precondition ($administrator != null && $stockkeeper != null && $read_only != null) {
      error_type = "standard"
      error = "TEST_FIXTURE_PROFILES_MISSING"
    }

    security.create_uuid as $administrator_uuid
    db.add user {
      data = {
        name: "OpenSpec administrator test " ~ $administrator_uuid,
        role: "admin",
        inventory_profile_id: $administrator.id
      }
    } as $administrator_user

    security.create_uuid as $stockkeeper_uuid
    db.add user {
      data = {
        name: "OpenSpec stockkeeper test " ~ $stockkeeper_uuid,
        role: "member",
        inventory_profile_id: $stockkeeper.id
      }
    } as $stockkeeper_user
    security.create_auth_token {
      table = "user"
      extras = {}
      expiration = 86400
      id = $stockkeeper_user.id
    } as $stockkeeper_token

    security.create_uuid as $read_only_uuid
    db.add user {
      data = {
        name: "OpenSpec read-only test " ~ $read_only_uuid,
        role: "member",
        inventory_profile_id: $read_only.id
      }
    } as $read_only_user

    var $permission_codes {
      value = [
        "category.read",
        "category.create",
        "category.update",
        "category.inactivate",
        "product.read",
        "product.create",
        "product.update",
        "product.inactivate",
        "supplier.read",
        "supplier.create",
        "supplier.update",
        "supplier.inactivate"
      ]
    }

    var $stockkeeper_permissions {
      value = [
        "category.read",
        "product.read",
        "product.create",
        "product.update",
        "product.inactivate",
        "supplier.read",
        "supplier.create",
        "supplier.update",
        "supplier.inactivate"
      ]
    }

    var $read_only_permissions {
      value = ["category.read", "product.read", "supplier.read"]
    }

    foreach ($permission_codes) {
      each as $permission_code {
        function.call "Inventory/authorize_permission" {
          input = {user_id: $administrator_user.id, permission_code: $permission_code}
        } as $administrator_result
        expect.to_be_true ($administrator_result.authorized)

        var $stockkeeper_allowed {
          value = $stockkeeper_permissions|some:$$ == $permission_code
        }
        conditional {
          if ($stockkeeper_allowed) {
            function.call "Inventory/authorize_permission" {
              input = {user_id: $stockkeeper_user.id, permission_code: $permission_code}
            } as $stockkeeper_result
            expect.to_be_true ($stockkeeper_result.authorized)
          }
          else {
            expect.to_throw {
              stack {
                function.call "Inventory/authorize_permission" {
                  input = {user_id: $stockkeeper_user.id, permission_code: $permission_code}
                } as $denied_stockkeeper_result
              }
              exception = "PERMISSION_DENIED"
            }
          }
        }

        var $read_only_allowed {
          value = $read_only_permissions|some:$$ == $permission_code
        }
        conditional {
          if ($read_only_allowed) {
            function.call "Inventory/authorize_permission" {
              input = {user_id: $read_only_user.id, permission_code: $permission_code}
            } as $read_only_result
            expect.to_be_true ($read_only_result.authorized)
          }
          else {
            expect.to_throw {
              stack {
                function.call "Inventory/authorize_permission" {
                  input = {user_id: $read_only_user.id, permission_code: $permission_code}
                } as $denied_read_only_result
              }
              exception = "PERMISSION_DENIED"
            }
          }
        }
      }
    }

    security.create_uuid as $unassigned_uuid
    db.add user {
      data = {
        name: "OpenSpec unassigned test " ~ $unassigned_uuid,
        role: "member"
      }
    } as $unassigned_user

    expect.to_throw {
      stack {
        function.call "Inventory/authorize_permission" {
          input = {user_id: $unassigned_user.id, permission_code: "category.read"}
        } as $unassigned_result
      }
      exception = "PROFILE_UNASSIGNED"
    }

    api.call "categories" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
    } as $before_revocation_response
    expect.to_be_defined ($before_revocation_response.items)

    db.query inventory_profile_permission {
      join = {
        permission: {
          table: "inventory_permission",
          type: "inner",
          where: $db.inventory_profile_permission.permission_id == $db.inventory_permission.id
        }
      }
      where = $db.inventory_profile_permission.profile_id == $stockkeeper.id
      eval = {permission_code: $db.inventory_permission.code}
      return = {type: "list"}
    } as $stockkeeper_grants_before_empty

    db.bulk.delete inventory_profile_permission {
      where = $db.inventory_profile_permission.profile_id == $stockkeeper.id
    } as $removed_stockkeeper_grants

    // The profile has no persisted grants while this same token is retried.
    expect.to_throw {
      stack {
        function.call "Inventory/authorize_permission" {
          input = {user_id: $stockkeeper_user.id, permission_code: "category.read"}
        } as $empty_grants_result
      }
      exception = "PERMISSION_DENIED"
    }

    expect.to_throw {
      stack {
        api.call "categories" verb=GET {
          api_group = "Inventory Catalog"
          headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
        } as $after_revocation_response
      }
      exception = "PERMISSION_DENIED"
    }

    foreach ($stockkeeper_grants_before_empty) {
      each as $grant_snapshot {
        db.get inventory_permission {
          field_name = "code"
          field_value = $grant_snapshot.permission_code
        } as $permission_to_restore

        precondition ($permission_to_restore != null) {
          error_type = "standard"
          error = "TEST_RESTORE_PERMISSION_MISSING"
        }

        db.add inventory_profile_permission {
          data = {
            profile_id: $stockkeeper.id,
            permission_id: $permission_to_restore.id
          }
        } as $restored_grant
      }
    }

    function.call "Inventory/seed_initial_data" as $restore_initial_grants
  }
}
