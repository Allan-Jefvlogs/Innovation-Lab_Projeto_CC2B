query "auth/change-initial-password" verb=PATCH {
  api_group = "Authentication"
  auth = "user"

  input {
    text password filters=min:8 {
      sensitive = true
    }
    text confirm_password {
      sensitive = true
    }
  }

  stack {
    precondition ($input.password == $input.confirm_password) {
      error_type = "inputerror"
      error = "PASSWORD_MISMATCH"
    }

    db.get "user" {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "must_change_password", "is_active"]
    } as $current_user
    precondition ($current_user != null) {
      error_type = "accessdenied"
      error = "USER_NOT_FOUND"
    }
    precondition ($current_user.is_active !== false) {
      error_type = "accessdenied"
      error = "USER_INACTIVE"
    }
    precondition ($current_user.must_change_password == true) {
      error_type = "accessdenied"
      error = "PASSWORD_CHANGE_NOT_REQUIRED"
    }

    db.edit "user" {
      field_name = "id"
      field_value = $auth.id
      enforce_hidden_fields = false
      data = {password: $input.password, must_change_password: false}
    } as $updated_user
  }

  response = {must_change_password: false}
}
