query "purchase_requests/notifications/by_id/{history_id}/read" verb=PATCH {
  api_group = "Inventory Stock"
  auth = "user"
  input { int history_id }
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
    db.get purchase_request_history {
      field_name = "id"
      field_value = $input.history_id
    } as $history
    precondition ($history != null && ($history.evento == "criada" || $history.evento == "cancelada" || $history.evento == "rejeitada" || $history.evento == "status_alterado" || $history.evento == "recebimento_registrado")) {
      error_type = "inputerror"
      error = "NOTIFICATION_NOT_FOUND"
    }
    db.get purchase_request {
      field_name = "id"
      field_value = $history.purchase_request_id
    } as $request
    precondition ($request != null && ($scope.all_access || $request.solicitante_usuario_id == $auth.id)) {
      error_type = "accessdenied"
      error = "PERMISSION_DENIED"
    }
    precondition ($history.data_evento >= $activation_at) {
      error_type = "inputerror"
      error = "NOTIFICATION_NOT_FOUND"
    }
    db.query purchase_request_notification_read {
      where = $db.purchase_request_notification_read.user_id == $auth.id && $db.purchase_request_notification_read.history_id == $history.id
      return = {type: "single"}
    } as $existing_read
    conditional {
      if ($existing_read == null) {
        db.add purchase_request_notification_read {
          data = {user_id: $auth.id, history_id: $history.id, read_at: now}
        } as $read_receipt
      }
    }
  }
  response = {history_id: $history.id, lida: true}
}
