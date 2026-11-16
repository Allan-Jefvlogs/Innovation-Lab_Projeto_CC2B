query "purchase_requests" verb=POST {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int produto_id
    decimal quantidade_solicitada
    text urgencia?="normal"
    email? email_destinatario? filters=trim
    text chave_idempotencia filters=trim
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.create"}
    } as $authorization

    precondition ($input.produto_id > 0 && $input.chave_idempotencia != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.quantidade_solicitada > 0) {
      error_type = "inputerror"
      error = "INVALID_QUANTITY"
    }
    precondition ($input.urgencia == "baixa" || $input.urgencia == "normal" || $input.urgencia == "alta" || $input.urgencia == "critica") {
      error_type = "inputerror"
      error = "INVALID_URGENCY"
    }
    precondition ($input.email_destinatario == null || ($input.email_destinatario != "" && ($input.email_destinatario|strlen) <= 254)) {
      error_type = "inputerror"
      error = "INVALID_RECIPIENT_EMAIL"
    }

    var $solicitacao {
      value = null
    }
    var $repeticao_idempotente {
      value = false
    }
    var $creation_error {
      value = null
    }

    // Fast path for a completed request. The key and payload are checked
    // again inside the transaction when this lookup misses.
    db.get purchase_request {
      field_name = "chave_idempotencia"
      field_value = $input.chave_idempotencia
    } as $existing_idempotency

    conditional {
      if ($existing_idempotency != null) {
        precondition ($existing_idempotency.solicitante_usuario_id == $auth.id && $existing_idempotency.produto_id == $input.produto_id && $existing_idempotency.quantidade_solicitada == $input.quantidade_solicitada && $existing_idempotency.urgencia == $input.urgencia && $existing_idempotency.email_destinatario == $input.email_destinatario) {
          error_type = "inputerror"
          error = "IDEMPOTENCY_KEY_REUSED"
        }

        var.update $solicitacao {
          value = $existing_idempotency
        }
        var.update $repeticao_idempotente {
          value = true
        }
      }
      else {
        try_catch {
          try {
            db.transaction {
              stack {
                // Recheck the idempotency key inside the transaction. Domain
                // errors are recorded before any write and mapped below.
                db.get purchase_request {
                  field_name = "chave_idempotencia"
                  field_value = $input.chave_idempotencia
                } as $idempotency_in_transaction

                conditional {
                  if ($idempotency_in_transaction != null) {
                    conditional {
                      if ($idempotency_in_transaction.solicitante_usuario_id == $auth.id && $idempotency_in_transaction.produto_id == $input.produto_id && $idempotency_in_transaction.quantidade_solicitada == $input.quantidade_solicitada && $idempotency_in_transaction.urgencia == $input.urgencia && $idempotency_in_transaction.email_destinatario == $input.email_destinatario) {
                        var.update $solicitacao {
                          value = $idempotency_in_transaction
                        }
                        var.update $repeticao_idempotente {
                          value = true
                        }
                      }
                      else {
                        var.update $creation_error {
                          value = "IDEMPOTENCY_KEY_REUSED"
                        }
                      }
                    }
                  }
                  else {
                    var $stock {
                      value = null
                    }

                    db.get product {
                      field_name = "id"
                      field_value = $input.produto_id
                    } as $product

                    conditional {
                      if ($product == null) {
                        var.update $creation_error {
                          value = "PRODUCT_NOT_FOUND"
                        }
                      }
                    }
                    conditional {
                      if ($product != null && $creation_error == null && $product.status != "ativo") {
                        var.update $creation_error {
                          value = "PRODUCT_INACTIVE"
                        }
                      }
                    }

                    conditional {
                      if ($product != null && $creation_error == null) {
                        db.get inventory_stock {
                          field_name = "product_id"
                          field_value = $product.id
                        } as $stock
                      }
                    }

                    conditional {
                      if ($creation_error == null && $stock == null) {
                        var.update $creation_error {
                          value = "STOCK_BALANCE_NOT_FOUND"
                        }
                      }
                    }
                    conditional {
                      if ($creation_error == null && $stock != null && $stock.quantidade_disponivel < 0) {
                        var.update $creation_error {
                          value = "STOCK_BALANCE_INVALID"
                        }
                      }
                    }
                    conditional {
                      if ($creation_error == null && $stock != null && !($stock.quantidade_disponivel == 0 || ($stock.quantidade_disponivel > 0 && $stock.quantidade_disponivel < $product.estoque_minimo))) {
                        var.update $creation_error {
                          value = "PRODUCT_STOCK_NOT_INSUFFICIENT"
                        }
                      }
                    }

                    conditional {
                      if ($creation_error == null) {
                        db.get purchase_request {
                          field_name = "active_product_id"
                          field_value = $product.id
                        } as $existing_active_request

                        conditional {
                          if ($existing_active_request != null) {
                            var.update $creation_error {
                              value = "PURCHASE_REQUEST_ALREADY_ACTIVE"
                            }
                          }
                        }
                      }
                    }

                    var $initial_email_status { value = "pendente" }
                    var $initial_notification_state { value = "nao_solicitada" }
                    var $email_failure_code { value = null }

                    conditional {
                      if ($creation_error == null && $input.email_destinatario != null) {
                        function.run "Inventory/resolve_purchase_request_email_provider" {
                          input = {destinatario_solicitado: $input.email_destinatario}
                        } as $email_provider_config

                        conditional {
                          if ($email_provider_config.provedor != "brevo" && $email_provider_config.provedor != "resend") {
                            var.update $initial_email_status { value = "falhou" }
                            var.update $initial_notification_state { value = "nao_enviada" }
                            var.update $email_failure_code {
                              value = $email_provider_config.codigo_erro
                            }
                          }
                          elseif ($email_provider_config.valid != true) {
                            var.update $initial_email_status { value = "falhou" }
                            var.update $initial_notification_state { value = "falhou" }
                            var.update $email_failure_code {
                              value = $email_provider_config.codigo_erro
                            }
                          }
                          else {
                            var.update $initial_notification_state { value = "pendente" }
                          }
                        }
                      }
                    }

                    conditional {
                      if ($creation_error == null) {
                        db.add purchase_request {
                          data = {
                            produto_id: $product.id,
                            quantidade_solicitada: $input.quantidade_solicitada,
                            quantidade_recebida: 0,
                            unidade_medida_solicitada: $product.unidade_medida,
                            urgencia: $input.urgencia,
                            email_destinatario: $input.email_destinatario,
                            solicitante_usuario_id: $auth.id,
                            status: "aberta",
                            email_status: $initial_email_status,
                            chave_idempotencia: $input.chave_idempotencia,
                            active_product_id: $product.id
                          }
                        } as $new_request

                        db.add purchase_request_history {
                          data = {
                            purchase_request_id: $new_request.id,
                            actor_user_id: $auth.id,
                            evento: "criada",
                            dados: {
                              produto_id: $product.id,
                              quantidade_solicitada: $input.quantidade_solicitada,
                              urgencia: $input.urgencia,
                              status: "aberta",
                              email_status: $initial_email_status,
                              notificacao_email_estado: $initial_notification_state,
                              notificacao_email_codigo: $email_failure_code
                            }
                          }
                        } as $creation_event

                        // Persist only a delivery intent in the same database
                        // transaction. No provider request is made here.
                        conditional {
                          if ($input.email_destinatario != null && ($email_provider_config.provedor == "brevo" || $email_provider_config.provedor == "resend")) {
                            function.run "Inventory/build_purchase_request_email_payload" {
                              input = {
                                tipo_evento: "solicitacao",
                                request_id: $new_request.id,
                                destinatario: $input.email_destinatario,
                                remetente: $email_provider_config.remetente,
                                nome_remetente: $email_provider_config.nome_remetente,
                                reply_to: $email_provider_config.reply_to,
                                produto_codigo: $product.codigo,
                                produto_nome: $product.nome,
                                quantidade: $new_request.quantidade_solicitada,
                                unidade_medida: $product.unidade_medida,
                                urgencia: $new_request.urgencia,
                                data_evento: $new_request.data_criacao|to_text
                              }
                            } as $email_payload_snapshot

                            var $original_delivery_idempotency_key {
                              value = "purchase-request-created/" ~ ($new_request.id|to_text)
                            }

                            conditional {
                              if ($email_provider_config.provedor == "brevo") {
                                var.update $original_delivery_idempotency_key { value = ""|uuid }
                              }
                            }

                            db.add purchase_request_email_delivery {
                              data = {
                                purchase_request_id: $new_request.id,
                                tipo_evento: "solicitacao",
                                destinatario: $input.email_destinatario,
                                status: $initial_email_status,
                                provedor: $email_provider_config.provedor,
                                chave_idempotencia: $original_delivery_idempotency_key,
                                payload_snapshot: $email_payload_snapshot,
                                tentativas: 0,
                                codigo_erro: $email_failure_code
                              }
                            } as $original_email_delivery
                          }
                        }

                        var.update $solicitacao {
                          value = $new_request
                        }
                      }
                    }
                  }
                }
              }
            }
          }
          catch {
            // This catch is outside db.transaction. A database failure first
            // aborts the transaction; only then do we classify the outcome.
            var.update $creation_error {
              value = "PURCHASE_REQUEST_CREATE_FAILED"
            }

            db.get purchase_request {
              field_name = "chave_idempotencia"
              field_value = $input.chave_idempotencia
            } as $idempotency_after_conflict

            conditional {
              if ($idempotency_after_conflict != null) {
                conditional {
                  if ($idempotency_after_conflict.solicitante_usuario_id == $auth.id && $idempotency_after_conflict.produto_id == $input.produto_id && $idempotency_after_conflict.quantidade_solicitada == $input.quantidade_solicitada && $idempotency_after_conflict.urgencia == $input.urgencia && $idempotency_after_conflict.email_destinatario == $input.email_destinatario) {
                    var.update $solicitacao {
                      value = $idempotency_after_conflict
                    }
                    var.update $repeticao_idempotente {
                      value = true
                    }
                    var.update $creation_error {
                      value = null
                    }
                  }
                  else {
                    var.update $creation_error {
                      value = "IDEMPOTENCY_KEY_REUSED"
                    }
                  }
                }
              }
              else {
                db.get purchase_request {
                  field_name = "active_product_id"
                  field_value = $input.produto_id
                } as $active_after_conflict

                conditional {
                  if ($active_after_conflict != null) {
                    var.update $creation_error {
                      value = "PURCHASE_REQUEST_ALREADY_ACTIVE"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    precondition ($creation_error != "PRODUCT_NOT_FOUND") {
      error_type = "notfound"
      error = "PRODUCT_NOT_FOUND"
    }
    precondition ($creation_error != "PRODUCT_INACTIVE") {
      error_type = "inputerror"
      error = "PRODUCT_INACTIVE"
    }
    precondition ($creation_error != "STOCK_BALANCE_NOT_FOUND") {
      error = "STOCK_BALANCE_NOT_FOUND"
    }
    precondition ($creation_error != "STOCK_BALANCE_INVALID") {
      error = "STOCK_BALANCE_INVALID"
    }
    precondition ($creation_error != "PRODUCT_STOCK_NOT_INSUFFICIENT") {
      error_type = "inputerror"
      error = "PRODUCT_STOCK_NOT_INSUFFICIENT"
    }
    precondition ($creation_error != "PURCHASE_REQUEST_ALREADY_ACTIVE") {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_ALREADY_ACTIVE"
    }
    precondition ($creation_error != "IDEMPOTENCY_KEY_REUSED") {
      error_type = "inputerror"
      error = "IDEMPOTENCY_KEY_REUSED"
    }
    precondition ($creation_error != "PURCHASE_REQUEST_CREATE_FAILED") {
      error = "PURCHASE_REQUEST_CREATE_FAILED"
    }
  }

  response = {
    solicitacao: {
      id: $solicitacao.id,
      produto_id: $solicitacao.produto_id,
      quantidade_solicitada: $solicitacao.quantidade_solicitada,
      quantidade_recebida: $solicitacao.quantidade_recebida,
      urgencia: $solicitacao.urgencia,
      solicitante_usuario_id: $solicitacao.solicitante_usuario_id,
      status: $solicitacao.status,
      email_status: $solicitacao.email_status,
      data_criacao: $solicitacao.data_criacao,
      data_atualizacao: $solicitacao.data_atualizacao,
      data_encerramento: $solicitacao.data_encerramento
    },
    repeticao_idempotente: $repeticao_idempotente,
    email_status: $solicitacao.email_status,
    email_enviado: false
  }
}
