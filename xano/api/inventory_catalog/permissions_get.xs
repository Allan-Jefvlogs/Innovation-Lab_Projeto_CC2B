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
      sort = {profile_id: "asc", permission_id: "asc"}
      return = {type: "list"}
    } as $grant_rows

    var $grants {
      value = []
    }

    foreach ($grant_rows) {
      each as $grant {
        db.get inventory_profile {
          field_name = "id"
          field_value = $grant.profile_id
          output = ["code"]
        } as $grant_profile

        db.get inventory_permission {
          field_name = "id"
          field_value = $grant.permission_id
          output = ["code"]
        } as $grant_permission

        array.push $grants {
          value = {
            profile_id: $grant.profile_id,
            permission_id: $grant.permission_id,
            profile_code: $grant_profile.code,
            permission_code: $grant_permission.code
          }
        }
      }
    }
  }

  response = {
    profiles: $profiles,
    permissions: $permissions,
    grants: $grants,
    administrator_access: "all_inventory_capabilities",
    editable_profile_codes: ["stockkeeper", "read_only"]
  }
}
