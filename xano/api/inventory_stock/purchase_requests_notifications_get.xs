query "purchase_requests/notifications" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"
  input {
    int page?=1 filters=min:1
    int per_page?=10 filters=min:1|max:50
  }
  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.read"}
    } as $read_authorization
    function.run "Inventory/purchase_request_notification_all_access" {
      input = {user_id: $auth.id}
    } as $scope
    var $activation_raw { value = $env.NEXSTOCK_PURCHASE_NOTIFICATIONS_ACTIVATED_AT }
    precondition ($activation_raw !== null) {
      error_type = "standard"
      error = "NOTIFICATIONS_ACTIVATION_MARKER_MISSING"
    }
    var $activation_text { value = $activation_raw|to_text|trim }
    precondition ($activation_text !== "") {
      error_type = "standard"
      error = "NOTIFICATIONS_ACTIVATION_MARKER_EMPTY"
    }
    precondition (("/^[1-9][0-9]{12}$/"|regex_matches:$activation_text)) {
      error_type = "standard"
      error = "NOTIFICATIONS_ACTIVATION_MARKER_INVALID"
    }
    var $activation_at { value = null }
    try_catch {
      try {
        var.update $activation_at { value = $activation_text|to_int }
      }
      catch {
        precondition (false) {
          error_type = "standard"
          error = "NOTIFICATIONS_ACTIVATION_MARKER_CONVERSION_FAILED"
        }
      }
    }
    precondition ($activation_at > 0 && ($activation_at|to_text) === $activation_text) {
      error_type = "standard"
      error = "NOTIFICATIONS_ACTIVATION_MARKER_CONVERSION_FAILED"
    }
    // BEGIN TEMP NOTIFICATIONS DIAG LIST
    try_catch {
      try {
        db.query purchase_request_history {
          join = {
            purchase_request: {table: "purchase_request", type: "inner", where: $db.purchase_request_history.purchase_request_id == $db.purchase_request.id},
            purchase_request_notification_read: {table: "purchase_request_notification_read", type: "left", where: $db.purchase_request_notification_read.history_id == $db.purchase_request_history.id && $db.purchase_request_notification_read.user_id == $auth.id}
          }
          eval = {
            read_receipt_id: $db.purchase_request_notification_read.id
          }
          where = $db.purchase_request_history.data_evento >= $activation_at && ($db.purchase_request_history.evento == "criada" || $db.purchase_request_history.evento == "cancelada" || $db.purchase_request_history.evento == "rejeitada" || $db.purchase_request_history.evento == "status_alterado" || $db.purchase_request_history.evento == "recebimento_registrado") && ($scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id)
          sort = {data_evento: "desc", id: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
          output = ["items.id", "items.purchase_request_id", "items.evento", "items.data_evento", "items.read_receipt_id", "items.dados", "itemsTotal", "curPage", "perPage"]
        } as $page
      }
      catch {
        precondition (false) {
          error_type = "standard"
          error = "NOTIFICATIONS_DIAG_LIST_QUERY_FAILED"
        }
      }
    }
    // END TEMP NOTIFICATIONS DIAG LIST
    // BEGIN TEMP NOTIFICATIONS DIAG COUNT
    try_catch {
      try {
        db.query purchase_request_history {
          join = {
            purchase_request: {table: "purchase_request", type: "inner", where: $db.purchase_request_history.purchase_request_id == $db.purchase_request.id},
            purchase_request_notification_read: {table: "purchase_request_notification_read", type: "left", where: $db.purchase_request_notification_read.history_id == $db.purchase_request_history.id && $db.purchase_request_notification_read.user_id == $auth.id}
          }
          where = $db.purchase_request_history.data_evento >= $activation_at && $db.purchase_request_notification_read.id == null && ($db.purchase_request_history.evento == "criada" || $db.purchase_request_history.evento == "cancelada" || $db.purchase_request_history.evento == "rejeitada" || $db.purchase_request_history.evento == "status_alterado" || $db.purchase_request_history.evento == "recebimento_registrado") && ($scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id)
          return = {type: "count"}
        } as $unread_total
      }
      catch {
        precondition (false) {
          error_type = "standard"
          error = "NOTIFICATIONS_DIAG_COUNT_QUERY_FAILED"
        }
      }
    }
    // END TEMP NOTIFICATIONS DIAG COUNT
    var $notification_items { value = [] }
    foreach ($page.items) {
      each as $notification {
        array.push $notification_items {
          value = {
            history_id: $notification.id,
            purchase_request_id: $notification.purchase_request_id,
            evento: $notification.evento,
            descricao: "Solicitação #"|concat:$notification.purchase_request_id|concat:" - "|concat:$notification.evento,
            status_novo: $notification.dados.status_novo,
            data_evento: $notification.data_evento,
            lida: ($notification.read_receipt_id !== null)
          }
        }
      }
    }
  }
  response = {
    items: $notification_items,
    curPage: $page.curPage,
    perPage: $page.perPage,
    itemsTotal: $page.itemsTotal,
    unreadTotal: $unread_total
  }
}
