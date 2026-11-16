query "movements/dashboard" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"
  input {
    timestamp date_from
    timestamp date_to
    text period?="7d"
  }
  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "movement.read", alternate_permission_code: "report.read"}
    } as $authorization
    precondition ($input.date_from < $input.date_to) {
      error_type = "inputerror"
      error = "INVALID_DATE_RANGE"
    }
    precondition ($input.period == "7d" || $input.period == "30d" || $input.period == "12m") {
      error_type = "inputerror"
      error = "INVALID_PERIOD"
    }
    var $start_day {
      value = $input.date_from|format_timestamp:"Y-m-d":"America/Sao_Paulo"
    }
    var $start_boundary {
      value = ($start_day ~ " 00:00:00")|parse_timestamp:"Y-m-d H:i:s":"America/Sao_Paulo"
    }
    precondition ($input.date_from == $start_boundary) {
      error_type = "inputerror"
      error = "DATE_RANGE_MUST_START_AT_LOCAL_MIDNIGHT"
    }

    var $day_indexes { value = [0, 1, 2, 3, 4, 5, 6] }
    conditional {
      if ($input.period == "30d") {
        var.update $day_indexes { value = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29] }
      }
      elseif ($input.period == "12m") {
        precondition (($input.date_from|format_timestamp:"d":"America/Sao_Paulo") == "01") {
          error_type = "inputerror"
          error = "DATE_RANGE_MUST_START_AT_MONTH_BOUNDARY"
        }
        var.update $day_indexes { value = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] }
      }
    }
    var $day_cursor { value = $input.date_from }
    var $day_keys { value = [] }
    var $daily_counts { value = {} }
    foreach ($day_indexes) {
      each as $day_index {
        var $day_key {
          value = $day_cursor|format_timestamp:"Y-m-d":"America/Sao_Paulo"
        }
        conditional {
          if ($input.period == "12m") {
            var.update $day_key { value = $day_cursor|format_timestamp:"Y-m":"America/Sao_Paulo" }
          }
        }
        array.push $day_keys { value = $day_key }
        var.update $daily_counts {
          value = $daily_counts|set:$day_key:{dia: $day_key, entradas: 0, saidas: 0}
        }
        conditional {
          if ($input.period == "12m") {
            var.update $day_cursor { value = $day_cursor|transform_timestamp:"+1 month":"America/Sao_Paulo" }
          }
          else {
            var.update $day_cursor {
              value = $day_cursor|transform_timestamp:"tomorrow":"America/Sao_Paulo"
            }
          }
        }
      }
    }
    precondition ($input.date_to == $day_cursor) {
      error_type = "inputerror"
      error = "DATE_RANGE_DOES_NOT_MATCH_PERIOD"
    }

    // Stream matching rows once; keep at most 30 counters, never sum mixed units.
    db.query inventory_movement {
      where = $db.inventory_movement.data_hora >= $input.date_from && $db.inventory_movement.data_hora < $input.date_to
      output = ["tipo", "data_hora"]
      return = {type: "stream"}
    } as $period_movements

    foreach ($period_movements) {
      each as $movement {
        var $movement_day {
          value = $movement.data_hora|format_timestamp:"Y-m-d":"America/Sao_Paulo"
        }
        conditional {
          if ($input.period == "12m") {
            var.update $movement_day { value = $movement.data_hora|format_timestamp:"Y-m":"America/Sao_Paulo" }
          }
        }
        var $day_counts { value = $daily_counts|get:$movement_day }
        conditional {
          if ($movement.tipo == "entrada") {
            var.update $day_counts {
              value = $day_counts|set:"entradas":($day_counts.entradas + 1)
            }
          }
          elseif ($movement.tipo == "saida") {
            var.update $day_counts {
              value = $day_counts|set:"saidas":($day_counts.saidas + 1)
            }
          }
        }
        var.update $daily_counts {
          value = $daily_counts|set:$movement_day:$day_counts
        }
      }
    }
    var $daily_rows { value = [] }
    foreach ($day_keys) {
      each as $date_key {
        array.push $daily_rows { value = $daily_counts|get:$date_key }
      }
    }
    db.query inventory_movement {
      join = {
        product: {table: "product", type: "left", where: $db.inventory_movement.product_id == $db.product.id},
        user: {table: "user", type: "left", where: $db.inventory_movement.user_id == $db.user.id}
      }
      eval = {product_code: $db.product.codigo, product_name: $db.product.nome, user_name: $db.user.name}
      sort = {data_hora: "desc", id: "desc"}
      return = {type: "list", paging: {page: 1, per_page: 5, totals: false}}
    } as $recent_page
    var $recent_items { value = [] }
    foreach ($recent_page.items) {
      each as $recent_movement {
        array.push $recent_items {
          value = {
            id: $recent_movement.id,
            tipo: $recent_movement.tipo,
            product_name: $recent_movement.product_name,
            quantidade: $recent_movement.quantidade,
            data_hora: $recent_movement.data_hora,
            user_name: $recent_movement.user_name
          }
        }
      }
    }
  }
  response = {
    serie: $daily_rows,
    recentes: {
      items: $recent_items,
      curPage: 1,
      perPage: 5
    }
  }
}
