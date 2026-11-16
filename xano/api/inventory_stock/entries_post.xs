query "entries" verb=POST {
  api_group = "Inventory Stock"
  auth = "user"
  input {
    int product_id
    decimal quantidade
    int? supplier_id?
    timestamp data_hora?
    text motivo filters=trim
    text? observacao?
    int? purchase_request_id?
    text? chave_recebimento? filters=trim
    text? unidade_medida? filters=trim
  }
  stack {
    var $global_access { value = false }
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "stock.entry"}
    } as $authorization
    precondition ($input.quantidade > 0 && $input.motivo != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.purchase_request_id != null || ($input.chave_recebimento == null && $input.unidade_medida == null)) {
      error_type = "inputerror"
      error = "RECEIPT_LINK_REQUIRED"
    }
    conditional {
      if ($input.purchase_request_id != null) {
        precondition ($input.purchase_request_id > 0 && $input.chave_recebimento != null && $input.chave_recebimento != "" && $input.unidade_medida != null && $input.unidade_medida != "") {
          error_type = "inputerror"
          error = "RECEIPT_INPUT_INVALID"
        }
        function.run "Inventory/authorize_permission" {
          input = {user_id: $auth.id, permission_code: "purchase_request.read"}
        } as $read_authorization
        function.run "Inventory/purchase_request_notification_all_access" {
          input = {user_id: $auth.id}
        } as $scope
        var.update $global_access { value = $scope.all_access }
      }
    }
    var $movement { value = null }
    var $request_after { value = null }
    var $saldo_anterior { value = null }
    var $saldo_atual { value = null }
    var $repeticao { value = false }
    var $stock_update_missing { value = false }
    db.transaction {
      stack {
        var $existing_movement { value = null }
        var $request { value = null }
        conditional {
          if ($input.purchase_request_id != null) {
            db.get purchase_request {
              field_name = "id"
              field_value = $input.purchase_request_id
            } as $request_found
            var.update $request { value = $request_found }
            precondition ($request != null) {
              error_type = "notfound"
              error = "PURCHASE_REQUEST_NOT_FOUND"
            }
            precondition ($global_access || $request.solicitante_usuario_id == $auth.id) {
              error_type = "notfound"
              error = "PURCHASE_REQUEST_NOT_FOUND"
            }
            db.get inventory_movement {
              field_name = "chave_recebimento"
              field_value = $input.chave_recebimento
            } as $found_movement
            var.update $existing_movement { value = $found_movement }
          }
        }
        conditional {
          if ($existing_movement != null) {
            // Recover a committed attempt even when the order is now complete.
            precondition ($existing_movement.tipo == "entrada" && $existing_movement.purchase_request_id == $input.purchase_request_id && $existing_movement.product_id == $input.product_id && $existing_movement.user_id == $auth.id && $existing_movement.quantidade == $input.quantidade && $existing_movement.unidade_medida == $input.unidade_medida && $existing_movement.supplier_id == $input.supplier_id && $existing_movement.motivo == $input.motivo && $existing_movement.observacao == $input.observacao && ($input.data_hora == null || $existing_movement.data_hora == $input.data_hora)) {
              error_type = "inputerror"
              error = "RECEIPT_IDEMPOTENCY_CONFLICT"
            }
            var.update $movement { value = $existing_movement }
            var.update $request_after { value = $request }
            var.update $repeticao { value = true }
          }
          else {
            db.get product {
              field_name = "id"
              field_value = $input.product_id
            } as $product
            precondition ($product != null) {
              error_type = "inputerror"
              error = "PRODUCT_NOT_FOUND"
            }
            precondition ($product.status == "ativo") {
              error_type = "inputerror"
              error = "PRODUCT_INACTIVE"
            }
            conditional {
              if ($input.supplier_id != null) {
                db.get supplier {
                  field_name = "id"
                  field_value = $input.supplier_id
                } as $supplier
                precondition ($supplier != null) {
                  error_type = "inputerror"
                  error = "SUPPLIER_NOT_FOUND"
                }
                precondition ($supplier.status == "ativo") {
                  error_type = "inputerror"
                  error = "SUPPLIER_INACTIVE"
                }
              }
            }
            db.get inventory_stock {
              field_name = "product_id"
              field_value = $input.product_id
            } as $stock
            precondition ($stock != null) {
              error_type = "inputerror"
              error = "STOCK_BALANCE_NOT_FOUND"
            }
            var $accumulated { value = null }
            conditional {
              if ($input.purchase_request_id != null) {
                precondition ($request.status == "aguardando_recebimento" || $request.status == "recebimento_parcial") {
                  error_type = "inputerror"
                  error = "RECEIPT_STATUS_INVALID"
                }
                precondition ($request.produto_id == $input.product_id && $request.active_product_id == $input.product_id) {
                  error_type = "inputerror"
                  error = "RECEIPT_PRODUCT_MISMATCH"
                }
                precondition ($request.unidade_medida_solicitada != null && $request.unidade_medida_solicitada != "") {
                  error_type = "inputerror"
                  error = "RECEIPT_UNIT_UNCONFIRMED"
                }
                precondition ($request.unidade_medida_solicitada == $input.unidade_medida && $product.unidade_medida == $input.unidade_medida) {
                  error_type = "inputerror"
                  error = "RECEIPT_UNIT_MISMATCH"
                }
                precondition ($request.quantidade_recebida !== null && $request.quantidade_recebida >= 0 && $request.quantidade_solicitada > 0 && $request.quantidade_recebida < $request.quantidade_solicitada) {
                  error_type = "inputerror"
                  error = "RECEIPT_BALANCE_INVALID"
                }
                var.update $accumulated { value = $request.quantidade_recebida + $input.quantidade }
                precondition ($accumulated <= $request.quantidade_solicitada) {
                  error_type = "inputerror"
                  error = "RECEIPT_EXCEEDS_REMAINING"
                }
              }
            }
            var.update $saldo_anterior { value = $stock.quantidade_disponivel }
            db.edit inventory_stock {
              field_name = "id"
              field_value = $stock.id
              data = {quantidade_disponivel: $stock.quantidade_disponivel + $input.quantidade}
            } as $updated_stock
            conditional {
              if ($updated_stock == null) {
                var.update $stock_update_missing { value = true }
              }
              else {
                var.update $saldo_atual { value = $updated_stock.quantidade_disponivel }
                var $effective_datetime { value = now }
                conditional {
                  if ($input.data_hora != null) {
                    var.update $effective_datetime { value = $input.data_hora }
                  }
                }
                db.add inventory_movement {
                  data = {
                    product_id: $input.product_id,
                    tipo: "entrada",
                    quantidade: $input.quantidade,
                    data_hora: $effective_datetime,
                    user_id: $auth.id,
                    supplier_id: $input.supplier_id,
                    motivo: $input.motivo,
                    observacao: $input.observacao,
                    purchase_request_id: $input.purchase_request_id,
                    chave_recebimento: $input.chave_recebimento,
                    unidade_medida: $product.unidade_medida
                  }
                } as $new_movement
                var.update $movement { value = $new_movement }
                conditional {
                  if ($input.purchase_request_id != null) {
                    var $new_status { value = "recebimento_parcial" }
                    var $active_product_id { value = $request.active_product_id }
                    var $closed_at { value = null }
                    conditional {
                      if ($accumulated == $request.quantidade_solicitada) {
                        var.update $new_status { value = "concluida" }
                        var.update $active_product_id { value = null }
                        var.update $closed_at { value = now }
                      }
                    }
                    db.edit purchase_request {
                      field_name = "id"
                      field_value = $request.id
                      data = {
                        quantidade_recebida: $accumulated,
                        status: $new_status,
                        active_product_id: $active_product_id,
                        data_atualizacao: now,
                        data_encerramento: $closed_at
                      }
                    } as $received_request
                    db.add purchase_request_history {
                      data = {
                        purchase_request_id: $request.id,
                        actor_user_id: $auth.id,
                        evento: "recebimento_registrado",
                        dados: {movement_id: $movement.id, quantidade: $input.quantidade, quantidade_recebida: $accumulated, unidade_medida: $input.unidade_medida, status_anterior: $request.status, status_novo: $new_status}
                      }
                    } as $receipt_history
                    var.update $request_after { value = $received_request }
                  }
                }
              }
            }
          }
        }
      }
    }
    precondition (!$stock_update_missing) {
      error_type = "inputerror"
      error = "STOCK_BALANCE_NOT_FOUND"
    }
    var $receipt_response { value = null }
    conditional {
      if ($request_after != null) {
        var.update $receipt_response {
          value = {id: $request_after.id, status: $request_after.status, quantidade_solicitada: $request_after.quantidade_solicitada, quantidade_recebida: $request_after.quantidade_recebida, unidade_medida_solicitada: $request_after.unidade_medida_solicitada}
        }
      }
    }
  }
  response = {
    movement_id: $movement.id,
    product_id: $movement.product_id,
    tipo: $movement.tipo,
    quantidade: $movement.quantidade,
    saldo_anterior: $saldo_anterior,
    saldo_atual: $saldo_atual,
    data_hora: $movement.data_hora,
    supplier_id: $movement.supplier_id,
    user_id: $movement.user_id,
    motivo: $movement.motivo,
    observacao: $movement.observacao,
    purchase_request_id: $movement.purchase_request_id,
    repeticao: $repeticao,
    recebimento: $receipt_response
  }
}
