query "audit_logs" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    timestamp? date_from?
    timestamp? date_to?
    int? actor_user_id? filters=min:1
    text? action_type?
    text? entity_type?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "administrator"}
    } as $authorization

    precondition ($input.date_from == null || $input.date_to == null || $input.date_from <= $input.date_to) {
      error_type = "inputerror"
      error = "INVALID_DATE_RANGE"
    }

    db.query inventory_audit_log {
      output = ["items.*", "itemsTotal", "curPage", "perPage"]
      where = $db.inventory_audit_log.occurred_at >=? $input.date_from && $db.inventory_audit_log.occurred_at <=? $input.date_to && $db.inventory_audit_log.actor_user_id ==? $input.actor_user_id && $db.inventory_audit_log.action_type ==? $input.action_type && $db.inventory_audit_log.entity_type ==? $input.entity_type
      sort = {occurred_at: "desc", id: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $audit_page
  }

  response = $audit_page
}
