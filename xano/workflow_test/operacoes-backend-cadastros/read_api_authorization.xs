workflow_test "operacoes_backend_cadastros_read_api_authorization" {
  datasource = "test"
  tags = ["operacoes-backend-cadastros", "authorization", "api"]

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

    security.create_uuid as $administrator_uuid
    db.add user {
      data = {
        name: "OpenSpec API administrator " ~ $administrator_uuid,
        role: "admin",
        inventory_profile_id: $administrator.id
      }
    } as $administrator_user
    security.create_auth_token {
      table = "user"
      extras = {}
      expiration = 86400
      id = $administrator_user.id
    } as $administrator_token

    security.create_uuid as $stockkeeper_uuid
    db.add user {
      data = {
        name: "OpenSpec API stockkeeper " ~ $stockkeeper_uuid,
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
        name: "OpenSpec API read-only " ~ $read_only_uuid,
        role: "member",
        inventory_profile_id: $read_only.id
      }
    } as $read_only_user
    security.create_auth_token {
      table = "user"
      extras = {}
      expiration = 86400
      id = $read_only_user.id
    } as $read_only_token

    api.call "permissions" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $administrator_token ~ '\"]'
    } as $permissions_response
    expect.to_be_defined ($permissions_response.profiles)
    expect.to_be_defined ($permissions_response.permissions)

    expect.to_throw {
      stack {
        api.call "permissions" verb=GET {
          api_group = "Inventory Catalog"
          headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
        } as $stockkeeper_permissions_response
      }
      exception = "PERMISSION_DENIED"
    }

    expect.to_throw {
      stack {
        api.call "permissions" verb=GET {
          api_group = "Inventory Catalog"
          headers = '[\"Authorization: Bearer ' ~ $read_only_token ~ '\"]'
        } as $read_only_permissions_response
      }
      exception = "PERMISSION_DENIED"
    }

    api.call "categories" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $administrator_token ~ '\"]'
    } as $administrator_categories
    expect.to_be_defined ($administrator_categories.items)

    api.call "categories" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
    } as $stockkeeper_categories
    expect.to_be_defined ($stockkeeper_categories.items)

    api.call "categories" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $read_only_token ~ '\"]'
    } as $read_only_categories
    expect.to_be_defined ($read_only_categories.items)

    api.call "products" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $administrator_token ~ '\"]'
    } as $administrator_products
    expect.to_be_defined ($administrator_products.items)

    api.call "products" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
    } as $stockkeeper_products
    expect.to_be_defined ($stockkeeper_products.items)

    api.call "products" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $read_only_token ~ '\"]'
    } as $read_only_products
    expect.to_be_defined ($read_only_products.items)

    api.call "suppliers" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $administrator_token ~ '\"]'
    } as $administrator_suppliers
    expect.to_be_defined ($administrator_suppliers.items)

    api.call "suppliers" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $stockkeeper_token ~ '\"]'
    } as $stockkeeper_suppliers
    expect.to_be_defined ($stockkeeper_suppliers.items)

    api.call "suppliers" verb=GET {
      api_group = "Inventory Catalog"
      headers = '[\"Authorization: Bearer ' ~ $read_only_token ~ '\"]'
    } as $read_only_suppliers
    expect.to_be_defined ($read_only_suppliers.items)
  }
}
