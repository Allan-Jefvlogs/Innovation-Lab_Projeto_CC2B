query "purchase_requests/by_id/{request_id}/cancel" verb=PATCH {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int request_id
    text justificativa filters=trim
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {
        user_id                  : $auth.id
        permission_code          : "purchase_request.cancel"
        alternate_permission_code: "purchase_request.manage"
      }
    } as $authorization

    precondition ($input.request_id > 0) {
      error_type = "inputerror"
      error = "INVALID_REQUEST_ID"
    }

    precondition ($input.justificativa != null && $input.justificativa != "") {
      error_type = "inputerror"
      error = "INVALID_JUSTIFICATION"
    }

    db.get purchase_request {
      field_name = "id"
      field_value = $input.request_id
    } as $request_for_authorization

    precondition ($request_for_authorization != null) {
      error_type = "notfound"
      error = "PURCHASE_REQUEST_NOT_FOUND"
    }

    conditional {
      if ($request_for_authorization.solicitante_usuario_id != $auth.id) {
        function.run "Inventory/authorize_permission" {
          input = {
            user_id        : $auth.id
            permission_code: "purchase_request.manage"
          }
        } as $management_authorization
      }
    }

    var $cancelled_request {
      value = null
    }

    var $cancel_error {
      value = null
    }

    // Only cancels the purchase request. Email notification is handled by
    // the frontend after a successful cancel.
    try_catch {
      try {
        db.transaction {
          stack {
            db.get purchase_request {
              field_name = "id"
              field_value = $input.request_id
            } as $request_in_transaction

            conditional {
              if ($request_in_transaction == null) {
                var.update $cancel_error {
                  value = "PURCHASE_REQUEST_NOT_FOUND"
                }
              }
            }

            conditional {
              if ($request_in_transaction != null && $request_in_transaction.status == "cancelada") {
                var.update $cancel_error {
                  value = "PURCHASE_REQUEST_ALREADY_CANCELLED"
                }
              }
            }

            conditional {
              if ($request_in_transaction != null && $cancel_error == null && $request_in_transaction.status != $request_for_authorization.status) {
                var.update $cancel_error {
                  value = "PURCHASE_REQUEST_CANCEL_CONFLICT"
                }
              }
            }

            conditional {
              if ($request_in_transaction != null && $cancel_error == null && $request_in_transaction.status != "aberta" && $request_in_transaction.status != "em_analise") {
                var.update $cancel_error {
                  value = "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE"
                }
              }
            }

            conditional {
              if ($request_in_transaction != null && $cancel_error == null) {
                db.edit purchase_request {
                  field_name = "id"
                  field_value = $input.request_id
                  data = {
                    status           : "cancelada"
                    active_product_id: null
                    data_encerramento: now
                    data_atualizacao : now
                  }
                } as $cancelled_request_row

                db.add purchase_request_history {
                  data = {
                    purchase_request_id: $request_in_transaction.id
                    actor_user_id      : $auth.id
                    evento             : "cancelada"
                    justificativa      : $input.justificativa
                    dados              : {
                      status_anterior           : $request_in_transaction.status
                      status_novo               : "cancelada"
                      active_product_id_liberado: true
                    }
                  }
                } as $cancellation_event

                var.update $cancelled_request {
                  value = $cancelled_request_row
                }
              }
            }
          }
        }
      }

      catch {
        var.update $cancel_error {
          value = "PURCHASE_REQUEST_CANCEL_FAILED"
        }

        // Keep the real failure visible: log to event_log (outside the
        // rolled-back transaction) and keep the stable response code.
        db.add event_log {
          data = {
            user_id : $auth.id
            action  : "purchase_request_cancel_failed"
            metadata: {request_id: $input.request_id, erro: $error.message}
          }
        } as $cancel_failure_log
      }
    }

    precondition ($cancel_error != "PURCHASE_REQUEST_NOT_FOUND") {
      error_type = "notfound"
      error = "PURCHASE_REQUEST_NOT_FOUND"
    }

    precondition ($cancel_error != "PURCHASE_REQUEST_ALREADY_CANCELLED") {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_ALREADY_CANCELLED"
    }

    precondition ($cancel_error != "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE") {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE"
    }

    precondition ($cancel_error != "PURCHASE_REQUEST_CANCEL_CONFLICT") {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_CANCEL_CONFLICT"
    }

    precondition ($cancel_error != "PURCHASE_REQUEST_CANCEL_FAILED") {
      error = "PURCHASE_REQUEST_CANCEL_FAILED"
    }
  }

  response = {
    solicitacao  : ```
      {
        id: $cancelled_request.id,
        produto_id: $cancelled_request.produto_id,
        quantidade_solicitada: $cancelled_request.quantidade_solicitada,
        quantidade_recebida: $cancelled_request.quantidade_recebida,
        urgencia: $cancelled_request.urgencia,
        solicitante_usuario_id: $cancelled_request.solicitante_usuario_id,
        status: $cancelled_request.status,
        email_status: $cancelled_request.email_status,
        data_criacao: $cancelled_request.data_criacao,
        data_atualizacao: $cancelled_request.data_atualizacao,
        data_encerramento: $cancelled_request.data_encerramento
      }
      ```
    justificativa: $input.justificativa
  }
}
