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
        user_id: $auth.id,
        permission_code: "purchase_request.cancel",
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
          input = {user_id: $auth.id, permission_code: "purchase_request.manage"}
        } as $management_authorization
      }
    }

    var $cancelled_request {
      value = null
    }
    var $cancel_error {
      value = null
    }
    var $email_provider_config {
      value = null
    }
    var $cancel_notice_status {
      value = "nao_aplicavel"
    }
    var $cancel_notice_error {
      value = null
    }
    var $original_email_delivery {
      value = null
    }

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
              if ($request_in_transaction != null && $cancel_error == null) {
                conditional {
                  if ($request_in_transaction.status == "cancelada") {
                    var.update $cancel_error {
                      value = "PURCHASE_REQUEST_ALREADY_CANCELLED"
                    }
                  }
                }
                conditional {
                  if ($cancel_error == null && $request_in_transaction.status != $request_for_authorization.status) {
                    var.update $cancel_error {
                      value = "PURCHASE_REQUEST_CANCEL_CONFLICT"
                    }
                  }
                }
                conditional {
                  if ($cancel_error == null && $request_in_transaction.status != "aberta" && $request_in_transaction.status != "em_analise") {
                    var.update $cancel_error {
                      value = "PURCHASE_REQUEST_STATUS_NOT_CANCELLABLE"
                    }
                  }
                }
              }
            }

            // Notification preparation is subordinate to the business cancel.
            // Keep the original intent's provider; never use the active selector
            // to route a cancellation notice.
            conditional {
              if ($request_in_transaction != null && $cancel_error == null && $request_in_transaction.email_destinatario != null) {
                db.query purchase_request_email_delivery {
                  where = $db.purchase_request_email_delivery.purchase_request_id == $request_in_transaction.id && $db.purchase_request_email_delivery.tipo_evento == "solicitacao"
                  return = {type: "single"}
                } as $original_email_delivery

                conditional {
                  if ($original_email_delivery != null && (($original_email_delivery.status == "enviado" && $original_email_delivery.id_mensagem_provedor != null) || $original_email_delivery.status == "pendente" || $original_email_delivery.status == "processando" || $original_email_delivery.status == "indeterminado")) {
                    conditional {
                      if ($original_email_delivery.provedor != "brevo" && $original_email_delivery.provedor != "resend") {
                        var.update $cancel_notice_status { value = "nao_enviada" }
                        var.update $cancel_notice_error { value = "EMAIL_ORIGINAL_PROVIDER_UNSUPPORTED" }
                      }
                      else {
                        function.run "Inventory/resolve_purchase_request_email_provider" {
                          input = {
                            provedor_solicitado: $original_email_delivery.provedor,
                            destinatario_solicitado: $original_email_delivery.destinatario
                          }
                        } as $resolved_email_provider_config
                        var.update $email_provider_config { value = $resolved_email_provider_config }

                        conditional {
                          if ($original_email_delivery.status == "enviado" && $original_email_delivery.id_mensagem_provedor != null) {
                            conditional {
                              if ($email_provider_config.valid == true) {
                                var.update $cancel_notice_status { value = "pendente" }
                              }
                              else {
                                var.update $cancel_notice_status { value = "falhou" }
                                var.update $cancel_notice_error { value = $email_provider_config.codigo_erro }
                              }
                            }
                          }
                          else {
                            // Original delivery can still be in flight or ambiguous.
                            // Preserve a deferred event with the original provider.
                            var.update $cancel_notice_status { value = "aguardando_confirmacao_original" }
                            conditional {
                              if ($email_provider_config.valid != true) {
                                var.update $cancel_notice_error { value = $email_provider_config.codigo_erro }
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

            conditional {
              if ($request_in_transaction != null && $cancel_error == null) {
                // The installed XanoScript validator rejects `where` for
                // db.bulk.update in this endpoint context. Re-read and validate
                // within the transaction, then use the documented single-row edit.
                db.edit purchase_request {
                  field_name = "id"
                  field_value = $input.request_id
                  data = {
                    status: "cancelada",
                    active_product_id: null,
                    data_encerramento: now,
                    data_atualizacao: now
                  }
                } as $cancelled_request_row

                db.add purchase_request_history {
                  data = {
                    purchase_request_id: $request_in_transaction.id,
                    actor_user_id: $auth.id,
                    evento: "cancelada",
                    justificativa: $input.justificativa,
                    dados: {
                      status_anterior: $request_in_transaction.status,
                      status_novo: "cancelada",
                      active_product_id_liberado: true,
                      notificacao_cancelamento_estado: $cancel_notice_status,
                      notificacao_cancelamento_codigo: $cancel_notice_error,
                      notificacao_cancelamento_provedor: $original_email_delivery.provedor
                    }
                  }
                } as $cancellation_event

                // A cancellation notice is only prepared if this exact
                // request has an original delivery record. A legacy
                // email_status value alone is not proof of provider success.
                conditional {
                  if ($request_in_transaction.email_destinatario != null) {
                    conditional {
                      if ($original_email_delivery != null && $original_email_delivery.status == "enviado" && $original_email_delivery.id_mensagem_provedor != null && ($original_email_delivery.provedor == "brevo" || $original_email_delivery.provedor == "resend")) {
                        var $cancellation_payload_snapshot {
                          value = null
                        }

                        db.get product {
                          field_name = "id"
                          field_value = $request_in_transaction.produto_id
                        } as $request_product

                        function.run "Inventory/build_purchase_request_email_payload" {
                          input = {
                            tipo_evento: "cancelamento",
                            request_id: $request_in_transaction.id,
                            destinatario: $request_in_transaction.email_destinatario,
                            remetente: $original_email_delivery.payload_snapshot.from,
                            nome_remetente: $original_email_delivery.payload_snapshot.from_name,
                            reply_to: $original_email_delivery.payload_snapshot.reply_to,
                            produto_codigo: $request_product.codigo,
                            produto_nome: $request_product.nome,
                            quantidade: $request_in_transaction.quantidade_solicitada,
                            unidade_medida: $request_product.unidade_medida,
                            urgencia: $request_in_transaction.urgencia,
                            data_evento: now|to_text
                          }
                        } as $cancellation_payload_snapshot

                        var $cancellation_delivery_idempotency_key {
                          value = "purchase-request-cancelled/" ~ ($request_in_transaction.id|to_text)
                        }

                        conditional {
                          if ($original_email_delivery.provedor == "brevo") {
                            var.update $cancellation_delivery_idempotency_key { value = ""|uuid }
                          }
                        }

                        db.add purchase_request_email_delivery {
                          data = {
                            purchase_request_id: $request_in_transaction.id,
                            tipo_evento: "cancelamento",
                            destinatario: $request_in_transaction.email_destinatario,
                            status: $cancel_notice_status,
                            provedor: $original_email_delivery.provedor,
                            chave_idempotencia: $cancellation_delivery_idempotency_key,
                            payload_snapshot: $cancellation_payload_snapshot,
                            tentativas: 0,
                            codigo_erro: $cancel_notice_error
                          }
                        } as $cancellation_email_delivery
                      }
                      elseif ($original_email_delivery != null && ($original_email_delivery.status == "pendente" || $original_email_delivery.status == "processando" || $original_email_delivery.status == "indeterminado") && ($original_email_delivery.provedor == "brevo" || $original_email_delivery.provedor == "resend")) {
                        // `pendente` is not proof that dispatch has not started:
                        // a worker may have read it before marking it
                        // `processando`. Do not race the worker by suppressing
                        // the original intent; wait for its persisted outcome.
                        var $waiting_cancellation_payload {
                          value = null
                        }

                        db.get product {
                          field_name = "id"
                          field_value = $request_in_transaction.produto_id
                        } as $request_product

                        function.run "Inventory/build_purchase_request_email_payload" {
                          input = {
                            tipo_evento: "cancelamento",
                            request_id: $request_in_transaction.id,
                            destinatario: $request_in_transaction.email_destinatario,
                            remetente: $original_email_delivery.payload_snapshot.from,
                            nome_remetente: $original_email_delivery.payload_snapshot.from_name,
                            reply_to: $original_email_delivery.payload_snapshot.reply_to,
                            produto_codigo: $request_product.codigo,
                            produto_nome: $request_product.nome,
                            quantidade: $request_in_transaction.quantidade_solicitada,
                            unidade_medida: $request_product.unidade_medida,
                            urgencia: $request_in_transaction.urgencia,
                            data_evento: now|to_text
                          }
                        } as $waiting_cancellation_payload

                        var $waiting_cancellation_delivery_idempotency_key {
                          value = "purchase-request-cancelled/" ~ ($request_in_transaction.id|to_text)
                        }

                        conditional {
                          if ($original_email_delivery.provedor == "brevo") {
                            var.update $waiting_cancellation_delivery_idempotency_key { value = ""|uuid }
                          }
                        }

                        db.add purchase_request_email_delivery {
                          data = {
                            purchase_request_id: $request_in_transaction.id,
                            tipo_evento: "cancelamento",
                            destinatario: $request_in_transaction.email_destinatario,
                            status: "aguardando_confirmacao_original",
                            provedor: $original_email_delivery.provedor,
                            chave_idempotencia: $waiting_cancellation_delivery_idempotency_key,
                            payload_snapshot: $waiting_cancellation_payload,
                            tentativas: 0,
                            codigo_erro: $cancel_notice_error
                          }
                        } as $waiting_cancellation_delivery
                      }
                    }
                  }
                }

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
      error_type = "standard"
      error = "PURCHASE_REQUEST_CANCEL_FAILED"
    }
  }

  response = {
    solicitacao: {
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
    },
    justificativa: $input.justificativa
  }
}
