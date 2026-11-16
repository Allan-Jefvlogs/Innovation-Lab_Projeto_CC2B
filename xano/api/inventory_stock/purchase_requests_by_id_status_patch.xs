query "purchase_requests/by_id/{request_id}/status" verb=PATCH {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int request_id
    text status_esperado
    text novo_status
    text? justificativa? filters=trim
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.status.update"}
    } as $authorization

    precondition ($input.request_id > 0) {
      error_type = "inputerror"
      error = "INVALID_REQUEST_ID"
    }
    precondition ($input.status_esperado == "aberta" || $input.status_esperado == "em_analise" || $input.status_esperado == "aprovada" || $input.status_esperado == "em_compra") {
      error_type = "inputerror"
      error = "INVALID_EXPECTED_STATUS"
    }
    precondition (($input.status_esperado == "aberta" && $input.novo_status == "em_analise") || ($input.status_esperado == "em_analise" && ($input.novo_status == "aprovada" || $input.novo_status == "rejeitada")) || ($input.status_esperado == "aprovada" && $input.novo_status == "em_compra") || ($input.status_esperado == "em_compra" && $input.novo_status == "aguardando_recebimento")) {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_TRANSITION_INVALID"
    }
    precondition ($input.novo_status != "rejeitada" || ($input.justificativa != null && $input.justificativa != "")) {
      error_type = "inputerror"
      error = "INVALID_JUSTIFICATION"
    }

    var $updated_request { value = null }
    db.transaction {
      stack {
        db.get purchase_request {
          field_name = "id"
          field_value = $input.request_id
        } as $current_request

        precondition ($current_request != null) {
          error_type = "notfound"
          error = "PURCHASE_REQUEST_NOT_FOUND"
        }
        precondition ($current_request.status == $input.status_esperado) {
          error_type = "inputerror"
          error = "PURCHASE_REQUEST_STATUS_CONFLICT"
        }

        // Academic scope: one operator at a time. This read/check/edit sequence
        // detects an already stale status, but is not an atomic compare-and-swap.
        var $changed_row { value = null }
        conditional {
          if ($input.novo_status == "rejeitada") {
            db.edit purchase_request {
              field_name = "id"
              field_value = $input.request_id
              data = {
                status: $input.novo_status,
                active_product_id: null,
                data_atualizacao: now,
                data_encerramento: now
              }
            } as $rejected_row
            var.update $changed_row { value = $rejected_row }
          }
          else {
            db.edit purchase_request {
              field_name = "id"
              field_value = $input.request_id
              data = {
                status: $input.novo_status,
                data_atualizacao: now
              }
            } as $transition_row
            var.update $changed_row { value = $transition_row }
          }
        }

        db.add purchase_request_history {
          data = {
            purchase_request_id: $input.request_id,
            actor_user_id: $auth.id,
            evento: $input.novo_status == "rejeitada" ? "rejeitada" : "status_alterado",
            justificativa: $input.justificativa,
            dados: {status_anterior: $input.status_esperado, status_novo: $input.novo_status}
          }
        } as $history_event

        var.update $updated_request { value = $changed_row }
      }
    }
  }

  response = {
    solicitacao: {
      id: $updated_request.id,
      produto_id: $updated_request.produto_id,
      quantidade_solicitada: $updated_request.quantidade_solicitada,
      quantidade_recebida: $updated_request.quantidade_recebida,
      urgencia: $updated_request.urgencia,
      solicitante_usuario_id: $updated_request.solicitante_usuario_id,
      status: $updated_request.status,
      email_status: $updated_request.email_status,
      data_criacao: $updated_request.data_criacao,
      data_atualizacao: $updated_request.data_atualizacao,
      data_encerramento: $updated_request.data_encerramento
    }
  }
}
