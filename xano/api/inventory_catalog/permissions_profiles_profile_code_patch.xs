query "permissions/profiles/{profile_code}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text profile_code
    int permission_revision filters=min:1
    text[] permissions
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.profile_code == "stockkeeper" || $input.profile_code == "read_only") {
      error_type = "inputerror"
      error = "IMMUTABLE_PROFILE"
    }

    var $unique_permissions {
      value = $input.permissions|unique
    }

    precondition (($unique_permissions|count) == ($input.permissions|count)) {
      error_type = "inputerror"
      error = "DUPLICATE_PERMISSION_CODE"
    }

    db.query inventory_permission {
      sort = {code: "asc"}
      return = {type: "list"}
    } as $catalog

    var $catalog_codes {
      value = $catalog|map:$$.code
    }

    foreach ($input.permissions) {
      each as $permission_code {
        precondition (($catalog_codes|some:$$ == $permission_code)) {
          error_type = "inputerror"
          error = "UNKNOWN_PERMISSION_CODE"
        }
      }
    }

    db.get inventory_profile {
      field_name = "code"
      field_value = $input.profile_code
    } as $target_profile

    precondition ($target_profile != null) {
      error_type = "notfound"
      error = "PROFILE_NOT_FOUND"
    }

    var $replacement {
      value = {}
    }

    try_catch {
      try {
        db.transaction {
          stack {
            db.get inventory_profile {
              field_name = "id"
              field_value = $target_profile.id
            } as $locked_profile

            precondition ($locked_profile.permission_revision == $input.permission_revision) {
              error_type = "inputerror"
              error = "PERMISSION_REVISION_CONFLICT"
            }

            db.query inventory_profile_permission {
              join = {
                permission: {
                  table: "inventory_permission",
                  type: "inner",
                  where: $db.inventory_profile_permission.permission_id == $db.inventory_permission.id
                }
              }
              where = $db.inventory_profile_permission.profile_id == $target_profile.id
              eval = {permission_code: $db.inventory_permission.code}
              return = {type: "list"}
            } as $current_grants

            var $current_codes {
              value = $current_grants|map:$$.permission_code
            }
            var $added_codes {
              value = $input.permissions|diff:$current_codes
            }
            var $removed_codes {
              value = $current_codes|diff:$input.permissions
            }
            var $next_revision {
              value = $locked_profile.permission_revision + 1
            }

            db.bulk.delete inventory_profile_permission {
              where = $db.inventory_profile_permission.profile_id == $target_profile.id
            } as $deleted_grants

            foreach ($input.permissions) {
              each as $permission_code {
                db.get inventory_permission {
                  field_name = "code"
                  field_value = $permission_code
                } as $permission

                db.add inventory_profile_permission {
                  data = {
                    profile_id: $target_profile.id,
                    permission_id: $permission.id
                  }
                } as $new_grant
              }
            }

            db.edit inventory_profile {
              field_name = "id"
              field_value = $target_profile.id
              data = {permission_revision: $next_revision}
            } as $updated_profile

            // The unique audit key serializes commits for the same prior revision.
            db.add inventory_permission_audit {
              data = {
                actor_user_id: $auth.id,
                target_profile_id: $target_profile.id,
                revision_before: $locked_profile.permission_revision,
                revision_after: $next_revision,
                permissions_added: $added_codes,
                permissions_removed: $removed_codes
              }
            } as $audit_event

            var.update $replacement {
              value = {
                profile_code: $target_profile.code,
                permission_revision: $next_revision,
                permissions: $input.permissions
              }
            }
          }
        }
      }
      catch {
        db.query inventory_permission_audit {
          where = $db.inventory_permission_audit.target_profile_id == $target_profile.id && $db.inventory_permission_audit.revision_before == $input.permission_revision
          return = {type: "exists"}
        } as $revision_already_committed

        conditional {
          if ($revision_already_committed) {
            throw {
              name = "PERMISSION_REVISION_CONFLICT"
              value = "PERMISSION_REVISION_CONFLICT"
            }
          }
          else {
            throw {
              name = "PERMISSION_UPDATE_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $replacement
}
