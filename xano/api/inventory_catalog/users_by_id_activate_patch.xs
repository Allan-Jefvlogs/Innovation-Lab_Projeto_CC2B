query "users/by_id/{user_id}/activate" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id filters=min:1
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    db.get "user" {
      field_name = "id"
      field_value = $input.user_id
      output = ["id"]
    } as $target_user
    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }

    db.edit "user" {
      field_name = "id"
      field_value = $target_user.id
      data = {is_active: true}
    } as $updated_user
  }

  response = {user_id: $target_user.id, is_active: true}
}
