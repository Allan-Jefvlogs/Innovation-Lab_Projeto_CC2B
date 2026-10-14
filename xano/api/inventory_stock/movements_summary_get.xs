query "movements_summary" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int? product_id? filters=min:1
    text? tipo?
    timestamp? date_from?
    timestamp? date_to?
    int? supplier_id? filters=min:1
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "report.read"}
    } as $authorization

    precondition ($input.date_from == null || $input.date_to == null || $input.date_from <= $input.date_to) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    precondition ($input.tipo == null || $input.tipo == "entrada" || $input.tipo == "saida") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    conditional {
      if ($input.date_from != null && $input.date_to != null) {
        db.query inventory_movement {
          where = $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.data_hora >= $input.date_from && $db.inventory_movement.data_hora <= $input.date_to && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
          return = {type: "list"}
          output = ["tipo", "quantidade"]
        } as $filtered_movements
      }
      else {
        conditional {
          if ($input.date_from != null) {
            db.query inventory_movement {
              where = $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.data_hora >= $input.date_from && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
              return = {type: "list"}
              output = ["tipo", "quantidade"]
            } as $filtered_movements
          }
          else {
            conditional {
              if ($input.date_to != null) {
                db.query inventory_movement {
                  where = $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.data_hora <= $input.date_to && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
                  return = {type: "list"}
                  output = ["tipo", "quantidade"]
                } as $filtered_movements
              }
              else {
                db.query inventory_movement {
                  where = $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.tipo ==? $input.tipo && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
                  return = {type: "list"}
                  output = ["tipo", "quantidade"]
                } as $filtered_movements
              }
            }
          }
        }
      }
    }

    var $total_movimentacoes {
      value = 0
    }
    var $quantidade_entradas {
      value = 0
    }
    var $quantidade_saidas {
      value = 0
    }

    foreach ($filtered_movements) {
      each as $movement {
        var.update $total_movimentacoes {
          value = $total_movimentacoes + 1
        }
        conditional {
          if ($movement.tipo == "entrada") {
            var.update $quantidade_entradas {
              value = $quantidade_entradas + $movement.quantidade
            }
          }
          else {
            var.update $quantidade_saidas {
              value = $quantidade_saidas + $movement.quantidade
            }
          }
        }
      }
    }
  }

  response = {
    total_movimentacoes: $total_movimentacoes,
    quantidade_entradas: $quantidade_entradas,
    quantidade_saidas: $quantidade_saidas
  }
}
