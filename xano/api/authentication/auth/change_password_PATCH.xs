query "auth/change-password" verb=PATCH {
  api_group = "Authentication"
  auth = "user"
  input {
    text current_password filters=min:1 {
      sensitive = true
    }
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
    precondition ("/^(?=.*[A-Za-z])(?=.*[0-9]).{8,}$/"|regex_matches:$input.password) {
      error_type = "inputerror"
      error = "PASSWORD_POLICY_INVALID"
    }
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "password", "is_active", "must_change_password"]
    } as $user
    precondition ($user != null && $user.is_active !== false) {
      error_type = "accessdenied"
      error = "USER_INACTIVE"
    }
    precondition ($user.must_change_password != true) {
      error_type = "accessdenied"
      error = "INITIAL_PASSWORD_FLOW_REQUIRED"
    }
    precondition ($user.password !== null) {
      error_type = "inputerror"
      error = "CURRENT_PASSWORD_INVALID"
    }
    security.check_password {
      text_password = $input.current_password
      hash_password = $user.password
    } as $current_password_valid
    precondition ($current_password_valid) {
      error_type = "inputerror"
      error = "CURRENT_PASSWORD_INVALID"
    }
    security.check_password {
      text_password = $input.password
      hash_password = $user.password
    } as $password_unchanged
    precondition (!$password_unchanged) {
      error_type = "inputerror"
      error = "NEW_PASSWORD_MUST_DIFFER"
    }
    db.edit user {
      field_name = "id"
      field_value = $auth.id
      enforce_hidden_fields = false
      data = {password: $input.password}
      output = ["id"]
    } as $updated_user
    precondition ($updated_user !== null && $updated_user.id == $auth.id) {
      error_type = "standard"
      error = "PASSWORD_CHANGE_FAILED"
    }
  }
  response = {senha_atualizada: true}
}
