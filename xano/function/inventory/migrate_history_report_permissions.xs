function "Inventory/migrate_history_report_permissions" {
  description = "Migra movement.read e report.read apenas para perfis não administradores que já possuem stock.read; preserva os demais grants."
  input {
    int actor_user_id {
      table = "user"
    }
  }
  stack {
    function.run "Inventory/authorize_permission" {
      input = {
        user_id: $input.actor_user_id,
        permission_code: "administrator"
      }
    } as $authorization

    var $permissions_created {
      value = 0
    }
    var $grants_created {
      value = 0
    }
    var $profiles_updated {
      value = []
    }

    db.transaction {
      stack {
        db.query inventory_permission {
          where = $db.inventory_permission.code == "movement.read"
          return = {type: "single"}
        } as $existing_movement_permission

        conditional {
          if ($existing_movement_permission == null) {
            db.add inventory_permission {
              data = {
                code: "movement.read",
                resource: "movement",
                action: "read"
              }
            } as $created_movement_permission

            var.update $permissions_created {
              value = $permissions_created + 1
            }
          }
        }

        db.query inventory_permission {
          where = $db.inventory_permission.code == "report.read"
          return = {type: "single"}
        } as $existing_report_permission

        conditional {
          if ($existing_report_permission == null) {
            db.add inventory_permission {
              data = {
                code: "report.read",
                resource: "report",
                action: "read"
              }
            } as $created_report_permission

            var.update $permissions_created {
              value = $permissions_created + 1
            }
          }
        }

        db.get inventory_permission {
          field_name = "code"
          field_value = "movement.read"
        } as $movement_permission

        db.get inventory_permission {
          field_name = "code"
          field_value = "report.read"
        } as $report_permission

        db.get inventory_permission {
          field_name = "code"
          field_value = "stock.read"
        } as $stock_permission

        precondition ($movement_permission != null) {
          error_type = "standard"
          error = "MOVEMENT_READ_PERMISSION_MISSING"
        }

        precondition ($report_permission != null) {
          error_type = "standard"
          error = "REPORT_READ_PERMISSION_MISSING"
        }

        precondition ($stock_permission != null) {
          error_type = "standard"
          error = "STOCK_READ_PERMISSION_MISSING"
        }

        precondition ($movement_permission.resource == "movement" && $movement_permission.action == "read") {
          error_type = "standard"
          error = "MOVEMENT_READ_PERMISSION_METADATA_INVALID"
        }

        precondition ($report_permission.resource == "report" && $report_permission.action == "read") {
          error_type = "standard"
          error = "REPORT_READ_PERMISSION_METADATA_INVALID"
        }

        db.query inventory_profile_permission {
          where = $db.inventory_profile_permission.permission_id == $stock_permission.id
          return = {type: "list"}
        } as $stock_read_grants

        foreach ($stock_read_grants) {
          each as $stock_read_grant {
            db.get inventory_profile {
              field_name = "id"
              field_value = $stock_read_grant.profile_id
            } as $profile

            var $profile_added_codes {
              value = []
            }

            conditional {
              if ($profile != null && $profile.code != "administrator") {
                db.query inventory_profile_permission {
                  where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $movement_permission.id
                  return = {type: "single"}
                } as $existing_movement_grant

                conditional {
                  if ($existing_movement_grant == null) {
                    precondition ($profile.permission_revision != null) {
                      error_type = "standard"
                      error = "PROFILE_PERMISSION_REVISION_MISSING"
                    }

                    db.add inventory_profile_permission {
                      data = {
                        profile_id: $profile.id,
                        permission_id: $movement_permission.id
                      }
                    } as $created_movement_grant

                    array.push $profile_added_codes {
                      value = "movement.read"
                    }

                    var.update $grants_created {
                      value = $grants_created + 1
                    }
                  }
                }

                db.query inventory_profile_permission {
                  where = $db.inventory_profile_permission.profile_id == $profile.id && $db.inventory_profile_permission.permission_id == $report_permission.id
                  return = {type: "single"}
                } as $existing_report_grant

                conditional {
                  if ($existing_report_grant == null) {
                    precondition ($profile.permission_revision != null) {
                      error_type = "standard"
                      error = "PROFILE_PERMISSION_REVISION_MISSING"
                    }

                    db.add inventory_profile_permission {
                      data = {
                        profile_id: $profile.id,
                        permission_id: $report_permission.id
                      }
                    } as $created_report_grant

                    array.push $profile_added_codes {
                      value = "report.read"
                    }

                    var.update $grants_created {
                      value = $grants_created + 1
                    }
                  }
                }

                conditional {
                  if (($profile_added_codes|count) > 0) {
                    var $next_revision {
                      value = $profile.permission_revision + 1
                    }

                    db.edit inventory_profile {
                      field_name = "id"
                      field_value = $profile.id
                      data = {permission_revision: $next_revision}
                    } as $updated_profile

                    db.add inventory_permission_audit {
                      data = {
                        actor_user_id: $input.actor_user_id,
                        target_profile_id: $profile.id,
                        revision_before: $profile.permission_revision,
                        revision_after: $next_revision,
                        permissions_added: $profile_added_codes,
                        permissions_removed: []
                      }
                    } as $audit_event

                    array.push $profiles_updated {
                      value = $profile.code
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  response = {
    success: true,
    permissions_created: $permissions_created,
    grants_created: $grants_created,
    profiles_updated: $profiles_updated
  }
}
