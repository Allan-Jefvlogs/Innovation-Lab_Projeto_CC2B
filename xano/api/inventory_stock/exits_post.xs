query "exits" verb=POST {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int product_id
    decimal quantidade
    timestamp data_hora?
    text motivo filters=trim
    text? observacao?
  }

  stack {
    db.transaction {
      stack {
        function.run "Inventory/authorize_permission" {
          input = {user_id: $auth.id, permission_code: "stock.exit"}
        } as $authorization

        precondition ($input.quantidade > 0 && $input.motivo != "") {
          error_type = "inputerror"
          error = "INVALID_INPUT"
        }

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

        db.get inventory_stock {
          field_name = "product_id"
          field_value = $input.product_id
        } as $stock

        precondition ($stock != null) {
          error_type = "inputerror"
          error = "STOCK_BALANCE_NOT_FOUND"
        }
        precondition ($input.quantidade <= $stock.quantidade_disponivel) {
          error_type = "inputerror"
          error = "INSUFFICIENT_STOCK"
        }

        var $effective_datetime {
          value = now
        }

        conditional {
          if ($input.data_hora != null) {
            var.update $effective_datetime {
              value = $input.data_hora
            }
          }
        }

        var $saldo_anterior {
          value = $stock.quantidade_disponivel
        }

        var $saldo_calculado {
          value = $stock.quantidade_disponivel - $input.quantidade
        }

        try_catch {
          try {
            db.edit inventory_stock {
              field_name = "id"
              field_value = $stock.id
              data = {quantidade_disponivel: $saldo_calculado}
            } as $updated_stock
          }
          catch {
            conditional {
              if ($error.name == "DeadlockError") {
                throw {
                  name = "STOCK_CONCURRENCY_CONFLICT"
                  value = "STOCK_CONCURRENCY_CONFLICT"
                }
              }
              else {
                throw {
                  name = "STOCK_UPDATE_FAILED"
                  value = $error.message
                }
              }
            }
          }
        }

        precondition ($updated_stock != null) {
          error_type = "inputerror"
          error = "STOCK_BALANCE_NOT_FOUND"
        }

        db.add inventory_movement {
          data = {
            product_id: $input.product_id,
            tipo: "saida",
            quantidade: $input.quantidade,
            data_hora: $effective_datetime,
            user_id: $auth.id,
            supplier_id: null,
            motivo: $input.motivo,
            observacao: $input.observacao
          }
        } as $movement
      }
    }
  }

  response = {
    movement_id: $movement.id,
    product_id: $movement.product_id,
    tipo: $movement.tipo,
    quantidade: $movement.quantidade,
    saldo_anterior: $saldo_anterior,
    saldo_atual: $updated_stock.quantidade_disponivel,
    data_hora: $movement.data_hora,
    supplier_id: $movement.supplier_id,
    user_id: $movement.user_id,
    motivo: $movement.motivo,
    observacao: $movement.observacao
  }
}
