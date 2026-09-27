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
      join = {
        permission: {
          table: "inventory_permission",
          type: "inner",
          where: $db.inventory_profile_permission.permission_id == $db.inventory_permission.id
        }
        profile: {
          table: "inventory_profile",
          type: "inner",
          where: $db.inventory_profile_permission.profile_id == $db.inventory_profile.id
        }
      }
      eval = {
        profile_code: $db.inventory_profile.code,
        permission_code: $db.inventory_permission.code
      }
      sort = {profile_id: "asc", permission_id: "asc"}
      return = {type: "list"}
    } as $grants
  }

  response = {
    profiles: $profiles,
    permissions: $permissions,
    grants: $grants,
    administrator_access: "all_inventory_capabilities",
    editable_profile_codes: ["stockkeeper", "read_only"]
  }
}
