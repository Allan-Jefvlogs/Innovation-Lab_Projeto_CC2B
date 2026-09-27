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

    db.direct_query {
      sql = "SELECT ipp.id, ipp.profile_id, ipp.permission_id, profile.code AS profile_code, permission.code AS permission_code FROM inventory_profile_permission AS ipp INNER JOIN inventory_profile AS profile ON profile.id = ipp.profile_id INNER JOIN inventory_permission AS permission ON permission.id = ipp.permission_id ORDER BY ipp.profile_id ASC, ipp.permission_id ASC"
      response_type = "list"
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
