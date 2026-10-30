function "Inventory/dispatch_purchase_request_email" {
  description = "Entrega uma única intenção pelo provedor gravado na outbox; não é chamada automaticamente pelos endpoints."
  input {
    int delivery_id
  }
  stack {
    db.get purchase_request_email_delivery {
      field_name = "id"
      field_value = $input.delivery_id
    } as $delivery

    precondition ($delivery != null) {
      error_type = "notfound"
      error = "EMAIL_DELIVERY_NOT_FOUND"
    }

    var $result_status {
      value = "not_processed"
    }
    var $eligible_to_send {
      value = false
    }
    var $request {
      value = null
    }
    var $original_delivery {
      value = null
    }

    conditional {
      if ($delivery.status == "enviado" || $delivery.status == "falhou" || $delivery.status == "indeterminado" || $delivery.status == "suprimido" || $delivery.status == "processando") {
        var.update $result_status {
          value = $delivery.status
        }
      }
    }

    conditional {
      if ($delivery.tipo_evento == "solicitacao" && $delivery.status == "pendente") {
        db.get purchase_request {
          field_name = "id"
          field_value = $delivery.purchase_request_id
        } as $request

        conditional {
          if ($request != null && $request.status == "cancelada") {
            db.edit purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
              data = {
                status: "suprimido",
                data_atualizacao: now,
                codigo_erro: "REQUEST_CANCELLED_BEFORE_SEND"
              }
            } as $suppressed_original

            var.update $result_status {
              value = "suprimido"
            }

            db.query purchase_request_email_delivery {
              where = $db.purchase_request_email_delivery.purchase_request_id == $delivery.purchase_request_id && $db.purchase_request_email_delivery.tipo_evento == "cancelamento" && $db.purchase_request_email_delivery.status == "aguardando_confirmacao_original"
              return = {type: "single"}
            } as $waiting_cancellation

            conditional {
              if ($waiting_cancellation != null) {
                db.edit purchase_request_email_delivery {
                  field_name = "id"
                  field_value = $waiting_cancellation.id
                  data = {
                    status: "suprimido",
                    data_atualizacao: now,
                    codigo_erro: "ORIGINAL_EMAIL_NOT_SENT"
                  }
                } as $suppressed_cancellation
              }
            }
          }
          elseif ($request != null && $delivery.status == "pendente") {
            var.update $eligible_to_send {
              value = true
            }
          }
        }
      }
      elseif ($delivery.tipo_evento == "cancelamento" && ($delivery.status == "pendente" || $delivery.status == "aguardando_confirmacao_original")) {
        db.query purchase_request_email_delivery {
          where = $db.purchase_request_email_delivery.purchase_request_id == $delivery.purchase_request_id && $db.purchase_request_email_delivery.tipo_evento == "solicitacao"
          return = {type: "single"}
        } as $original_delivery

        conditional {
          if ($original_delivery != null && $original_delivery.status == "enviado" && ($delivery.status == "pendente" || $delivery.status == "aguardando_confirmacao_original")) {
            conditional {
              if ($delivery.status == "aguardando_confirmacao_original") {
                db.edit purchase_request_email_delivery {
                  field_name = "id"
                  field_value = $delivery.id
                  data = {
                    status: "pendente",
                    data_atualizacao: now,
                    codigo_erro: null
                  }
                } as $ready_cancellation
              }
            }
            var.update $eligible_to_send {
              value = true
            }
          }
          elseif ($original_delivery != null && ($original_delivery.status == "falhou" || $original_delivery.status == "suprimido")) {
            db.edit purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
              data = {
                status: "suprimido",
                data_atualizacao: now,
                codigo_erro: "ORIGINAL_EMAIL_NOT_CONFIRMED_SENT"
              }
            } as $suppressed_cancellation

            var.update $result_status {
              value = "suprimido"
            }
          }
          else {
            var.update $result_status {
              value = "aguardando_confirmacao_original"
            }
          }
        }
      }
    }

    conditional {
      if ($eligible_to_send == true) {
        var $provider_ready { value = false }
        var $send_payload { value = null }
        var $request_headers { value = ["Content-Type: application/json"] }
        var $provider_url { value = "" }
        var $transport_failed { value = false }
        var $api_result { value = null }
        var $http_status { value = null }
        var $provider_message_id { value = null }
        var $provider_duplicate { value = false }
        var $provider_configuration_error_code { value = null }

        // Route only by the immutable provider stored with this delivery.
        // NEXSTOCK_EMAIL_PROVIDER is deliberately not consulted here.
        conditional {
          if ($delivery.provedor == "resend") {
            conditional {
              if ($env.RESEND_API_KEY == null || $env.RESEND_API_KEY == "" || $env.RESEND_FROM_EMAIL != "onboarding@resend.dev" || $delivery.payload_snapshot.from != "onboarding@resend.dev" || $env.RESEND_ALLOWED_TEST_RECIPIENT == null || $env.RESEND_ALLOWED_TEST_RECIPIENT == "" || $delivery.destinatario != $env.RESEND_ALLOWED_TEST_RECIPIENT || $delivery.payload_snapshot.to != $env.RESEND_ALLOWED_TEST_RECIPIENT) {
                var.update $result_status { value = "configuracao_de_teste_incompleta" }
                var.update $provider_configuration_error_code { value = "EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE" }
              }
              else {
                var.update $send_payload {
                  value = {
                    from: $delivery.payload_snapshot.from,
                    to: $delivery.payload_snapshot.to,
                    subject: $delivery.payload_snapshot.subject,
                    text: $delivery.payload_snapshot.text
                  }
                }
                conditional {
                  if ($delivery.payload_snapshot.reply_to != null && $delivery.payload_snapshot.reply_to != "") {
                    var.update $send_payload {
                      value = {
                        from: $delivery.payload_snapshot.from,
                        to: $delivery.payload_snapshot.to,
                        reply_to: $delivery.payload_snapshot.reply_to,
                        subject: $delivery.payload_snapshot.subject,
                        text: $delivery.payload_snapshot.text
                      }
                    }
                  }
                }
                var.update $request_headers {
                  value = [
                    "Authorization: Bearer " ~ $env.RESEND_API_KEY,
                    "Content-Type: application/json",
                    "Idempotency-Key: " ~ $delivery.chave_idempotencia
                  ]
                }
                var.update $provider_url { value = "https://api.resend.com/emails" }
                var.update $provider_ready { value = true }
              }
            }
          }
          elseif ($delivery.provedor == "brevo") {
            conditional {
              if ($env.BREVO_API_KEY == null || $env.BREVO_API_KEY == "" || $env.BREVO_FROM_EMAIL == null || $env.BREVO_FROM_EMAIL == "" || $env.BREVO_FROM_NAME == null || $env.BREVO_FROM_NAME == "" || $delivery.payload_snapshot.from != $env.BREVO_FROM_EMAIL || $delivery.payload_snapshot.from_name != $env.BREVO_FROM_NAME) {
                var.update $result_status { value = "configuracao_de_provedor_incompleta" }
                var.update $provider_configuration_error_code { value = "EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE" }
              }
              else {
                var.update $send_payload {
                  value = {
                    sender: {email: $delivery.payload_snapshot.from, name: $delivery.payload_snapshot.from_name},
                    to: [{email: $delivery.payload_snapshot.to}],
                    subject: $delivery.payload_snapshot.subject,
                    textContent: $delivery.payload_snapshot.text,
                    htmlContent: $delivery.payload_snapshot.html,
                    headers: {IdempotencyKey: $delivery.chave_idempotencia}
                  }
                }
                conditional {
                  if ($delivery.payload_snapshot.reply_to != null && $delivery.payload_snapshot.reply_to != "") {
                    var.update $send_payload {
                      value = {
                        sender: {email: $delivery.payload_snapshot.from, name: $delivery.payload_snapshot.from_name},
                        to: [{email: $delivery.payload_snapshot.to}],
                        replyTo: {email: $delivery.payload_snapshot.reply_to},
                        subject: $delivery.payload_snapshot.subject,
                        textContent: $delivery.payload_snapshot.text,
                      htmlContent: $delivery.payload_snapshot.html,
                        headers: {IdempotencyKey: $delivery.chave_idempotencia}
                      }
                    }
                  }
                }
                var.update $request_headers {
                  value = [
                    "api-key: " ~ $env.BREVO_API_KEY,
                    "Content-Type: application/json"
                  ]
                }
                var.update $provider_url { value = "https://api.brevo.com/v3/smtp/email" }
                var.update $provider_ready { value = true }
              }
            }
          }
          else {
            var.update $result_status { value = "provedor_nao_suportado" }
            var.update $provider_configuration_error_code { value = "EMAIL_PROVIDER_UNSUPPORTED" }
          }
        }

        conditional {
          if ($provider_ready == true) {
            db.edit purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
              data = {
                status: "processando",
                tentativas: $delivery.tentativas + 1,
                data_ultima_tentativa: now,
                data_atualizacao: now,
                codigo_erro: null
              }
            } as $processing_delivery

            try_catch {
              try {
                api.request {
                  url = $provider_url
                  method = "POST"
                  params = $send_payload
                  headers = $request_headers
                  timeout = 20
                } as $api_result
              }
              catch {
                var.update $transport_failed { value = true }
              }
            }

            conditional {
              if ($transport_failed == false && $api_result.response.status != null) {
                var.update $http_status { value = $api_result.response.status }
                conditional {
                  if ($api_result.response.status >= 200 && $api_result.response.status < 300) {
                    conditional {
                      if ($delivery.provedor == "brevo") {
                        var.update $provider_message_id { value = $api_result.response.result.messageId }
                      }
                      else {
                        var.update $provider_message_id { value = $api_result.response.result.id }
                      }
                    }
                  }
                  elseif ($delivery.provedor == "brevo" && $api_result.response.result.code == "duplicate_parameter") {
                    // Brevo reports an already-consumed idempotency key as a
                    // duplicate. The original provider outcome is not known.
                    var.update $provider_duplicate { value = true }
                  }
                }
              }
              elseif ($transport_failed == false) {
                var.update $transport_failed { value = true }
              }
            }

            function.run "Inventory/classify_purchase_request_email_response" {
              input = {
                transport_failed: $transport_failed,
                http_status: $http_status,
                provider_message_id: $provider_message_id,
                duplicate_request: $provider_duplicate
              }
            } as $classification

            // Preserve the canonical snapshot. Provider-specific request
            // bodies are transient and never replace the saved intent.
            db.get purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
            } as $latest_delivery

            var $resolved_status { value = $classification.status }
            var $resolved_message_id { value = $provider_message_id }
            var $resolved_error_code { value = $classification.codigo_erro }
            var $confirmation_timestamp { value = null }

            conditional {
              if ($latest_delivery != null && $latest_delivery.status == "enviado" && $latest_delivery.id_mensagem_provedor != null) {
                var.update $resolved_status { value = "enviado" }
                var.update $resolved_message_id { value = $latest_delivery.id_mensagem_provedor }
                var.update $resolved_error_code { value = null }
                var.update $confirmation_timestamp { value = $latest_delivery.data_confirmacao }
              }
              elseif ($classification.status == "enviado") {
                var.update $confirmation_timestamp { value = now }
              }
            }

            db.edit purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
              data = {
                status: $resolved_status,
                id_mensagem_provedor: $resolved_message_id,
                data_confirmacao: $confirmation_timestamp,
                data_atualizacao: now,
                codigo_erro: $resolved_error_code
              }
            } as $updated_delivery

            conditional {
              if ($delivery.tipo_evento == "solicitacao" && ($resolved_status == "enviado" || $resolved_status == "falhou")) {
                db.edit purchase_request {
                  field_name = "id"
                  field_value = $delivery.purchase_request_id
                  data = {email_status: $resolved_status, data_atualizacao: now}
                } as $updated_request_email_status
              }
            }

            var.update $result_status { value = $resolved_status }
          }
        }

        conditional {
          if ($provider_ready == false && $provider_configuration_error_code != null) {
            // Persist the non-sent outcome before returning so a configuration
            // error cannot leave this delivery eligible for repeated runs.
            db.edit purchase_request_email_delivery {
              field_name = "id"
              field_value = $delivery.id
              data = {
                status: "falhou",
                data_atualizacao: now,
                codigo_erro: $provider_configuration_error_code
              }
            } as $failed_configuration_delivery

            conditional {
              if ($delivery.tipo_evento == "solicitacao") {
                db.edit purchase_request {
                  field_name = "id"
                  field_value = $delivery.purchase_request_id
                  data = {email_status: "falhou", data_atualizacao: now}
                } as $failed_request_email_configuration
              }
            }
          }
        }
      }
    }
  }
  response = {
    delivery_id: $input.delivery_id,
    status: $result_status
  }
}
