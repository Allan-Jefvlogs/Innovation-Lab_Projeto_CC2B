query "users/by_id/{user_id}/profile" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int user_id {
      table = "user"
    }
    text profile_code
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.user_id != $auth.id) {
      error_type = "accessdenied"
      error = "IMMUTABLE_PROFILE"
    }

    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id"]
    } as $target_user

    precondition ($target_user != null) {
      error_type = "notfound"
      error = "USER_NOT_FOUND"
    }

    db.get inventory_profile {
      field_name = "code"
      field_value = $input.profile_code
    } as $profile

    precondition ($profile != null) {
      error_type = "inputerror"
      error = "PROFILE_INVALID"
    }

    db.edit user {
      field_name = "id"
      field_value = $target_user.id
      data = {inventory_profile_id: $profile.id}
    } as $updated_user
  }

  response = {
    user_id: $target_user.id,
    profile_code: $profile.code,
    display_name: $profile.display_name
  }
}
