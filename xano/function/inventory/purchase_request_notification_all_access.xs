function "Inventory/purchase_request_notification_all_access" {
  description = "Indica escopo global após autorização purchase_request.read já validada pelo endpoint chamador."
  input {
    int user_id { table = "user" }
  }
  stack {
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "inventory_profile_id"]
    } as $user
    db.get inventory_profile {
      field_name = "id"
      field_value = $user.inventory_profile_id
      output = ["id", "code"]
    } as $profile
    var $all_access { value = $profile != null && $profile.code == "administrator" }
    conditional {
      if (!$all_access) {
        db.get inventory_permission {
          field_name = "code"
          field_value = "purchase_request.manage"
        } as $manage_permission
        conditional {
          if ($manage_permission != null) {
            db.query inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $manage_permission.id
              return = {type: "exists"}
            } as $granted
            var.update $all_access { value = $granted }
          }
        }
      }
    }
  }
  response = {all_access: $all_access}
}
