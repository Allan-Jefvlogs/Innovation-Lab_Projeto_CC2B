query "permissions" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    db.query inventory_profile {
      sort = {id: "asc"}
      return = {type: "list"}
    } as $profiles

    db.query inventory_permission {
      sort = {code: "asc"}
      return = {type: "list"}
    } as $permissions

    db.query inventory_profile_permission {
      sort = {
        profile_id: "asc"
        permission_id: "asc"
      }
      return = {type: "list"}
    } as $grant_rows

    var $enriched_grants {
      value = []
    }

    var $stockkeeper_permissions {
      value = []
    }

    var $read_only_permissions {
      value = []
    }

    var $permission_matrix {
      value = []
    }

    foreach ($grant_rows) {
      each as $grant {
        db.get "inventory_profile" {
          field_name = "id"
          field_value = $grant.profile_id
        } as $profile

        db.get "inventory_permission" {
          field_name = "id"
          field_value = $grant.permission_id
        } as $permission

        var $grant_item {
          value = {
            profile_id: $grant.profile_id,
            permission_id: $grant.permission_id,
            profile_code: $profile.code,
            permission_code: $permission.code
          }
        }

        array.push $enriched_grants {
          value = $grant_item
        }

        switch ($grant_item.profile_code) {
          case ("stockkeeper") {
            array.push $stockkeeper_permissions {
              value = $grant_item.permission_code
            }
          } break
          case ("read_only") {
            array.push $read_only_permissions {
              value = $grant_item.permission_code
            }
        } break
      }
    }
    }

    var $stockkeeper_profile {
      value = $profiles|find:$$.code=="stockkeeper"
    }

    var $read_only_profile {
      value = $profiles|find:$$.code=="read_only"
    }

    var.update $permission_matrix {
      value = [
        {
          profile_code: "administrator",
          permissions: "integral",
          access_scope: "integral",
          editable: false
        },
        {
          profile_code: "stockkeeper",
          permissions: $stockkeeper_permissions,
          permission_revision: $stockkeeper_profile.permission_revision
        },
        {
          profile_code: "read_only",
          permissions: $read_only_permissions,
          permission_revision: $read_only_profile.permission_revision
        }
      ]
    }
  }

  response = {
    profiles: $profiles,
    permissions: $permissions,
    permission_matrix: $permission_matrix,
    status: "ok"
  }
}
