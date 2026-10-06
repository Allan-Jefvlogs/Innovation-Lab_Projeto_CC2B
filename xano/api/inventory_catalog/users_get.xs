query "users" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text? search? filters=trim
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    db.query "user" {
      join = {
        profile: {
          table: "inventory_profile",
          type: "left",
          where: $db.user.inventory_profile_id == $db.profile.id
        }
      }
      eval = {profile_name: $db.profile.display_name}
      where = $input.search == null || $input.search == "" || $db.user.name includes $input.search || $db.user.email includes $input.search
      sort = {id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $users_page

    var $items {
      value = []
    }
    foreach ($users_page.items) {
      each as $user_record {
        array.push $items {
          value = {
            id: $user_record.id,
            name: $user_record.name,
            email: $user_record.email,
            inventory_profile_id: $user_record.inventory_profile_id,
            profile_name: $user_record.profile_name,
            is_active: $user_record.is_active
          }
        }
      }
    }
  }

  response = $users_page|set:"items":$items
}
