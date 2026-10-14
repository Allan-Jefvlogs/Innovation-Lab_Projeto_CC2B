query "movement_users" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int page?=1 filters=min:1
    int per_page?=100 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "movement.read"}
    } as $authorization

    db.query "user" {
      sort = {
        name: "asc"
        id: "asc"
      }
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
            name: $user_record.name
          }
        }
      }
    }
  }

  response = $users_page|set:"items":$items
}
