query "movements" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    text tipo?
    int? product_id? filters=min:1
    int? user_id? filters=min:1
    timestamp? date_from?
    timestamp? date_to?
    int? supplier_id? filters=min:1
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {
        user_id: $auth.id,
        permission_code: "movement.read",
        alternate_permission_code: "report.read"
      }
    } as $authorization

    precondition ($input.tipo == null || $input.tipo == "entrada" || $input.tipo == "saida") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    precondition ($input.date_from == null || $input.date_to == null || $input.date_from <= $input.date_to) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    conditional {
      if ($input.date_from != null && $input.date_to != null) {
        db.query inventory_movement {
          join = {
            product: {table: "product", type: "left", where: $db.inventory_movement.product_id == $db.product.id},
            user: {table: "user", type: "left", where: $db.inventory_movement.user_id == $db.user.id},
            supplier: {table: "supplier", type: "left", where: $db.inventory_movement.supplier_id == $db.supplier.id}
          }
          eval = {product_code: $db.product.codigo, product_name: $db.product.nome, user_name: $db.user.name, supplier_name: $db.supplier.nome_razao_social}
          where = $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.user_id ==? $input.user_id && $db.inventory_movement.data_hora >= $input.date_from && $db.inventory_movement.data_hora <= $input.date_to && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
          sort = {data_hora: "desc", id: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
        } as $movement_page
      }
      else {
        conditional {
          if ($input.date_from != null) {
            db.query inventory_movement {
          join = {
            product: {table: "product", type: "left", where: $db.inventory_movement.product_id == $db.product.id},
            user: {table: "user", type: "left", where: $db.inventory_movement.user_id == $db.user.id},
            supplier: {table: "supplier", type: "left", where: $db.inventory_movement.supplier_id == $db.supplier.id}
          }
          eval = {product_code: $db.product.codigo, product_name: $db.product.nome, user_name: $db.user.name, supplier_name: $db.supplier.nome_razao_social}
          where = $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.user_id ==? $input.user_id && $db.inventory_movement.data_hora >= $input.date_from && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
          sort = {data_hora: "desc", id: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
            } as $movement_page
          }
          else {
            conditional {
              if ($input.date_to != null) {
                db.query inventory_movement {
          join = {
            product: {table: "product", type: "left", where: $db.inventory_movement.product_id == $db.product.id},
            user: {table: "user", type: "left", where: $db.inventory_movement.user_id == $db.user.id},
            supplier: {table: "supplier", type: "left", where: $db.inventory_movement.supplier_id == $db.supplier.id}
          }
          eval = {product_code: $db.product.codigo, product_name: $db.product.nome, user_name: $db.user.name, supplier_name: $db.supplier.nome_razao_social}
          where = $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.user_id ==? $input.user_id && $db.inventory_movement.data_hora <= $input.date_to && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
          sort = {data_hora: "desc", id: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
                } as $movement_page
              }
              else {
                db.query inventory_movement {
          join = {
            product: {table: "product", type: "left", where: $db.inventory_movement.product_id == $db.product.id},
            user: {table: "user", type: "left", where: $db.inventory_movement.user_id == $db.user.id},
            supplier: {table: "supplier", type: "left", where: $db.inventory_movement.supplier_id == $db.supplier.id}
          }
          eval = {product_code: $db.product.codigo, product_name: $db.product.nome, user_name: $db.user.name, supplier_name: $db.supplier.nome_razao_social}
          where = $db.inventory_movement.tipo ==? $input.tipo && $db.inventory_movement.product_id ==? $input.product_id && $db.inventory_movement.user_id ==? $input.user_id && ($input.supplier_id == null || $db.inventory_movement.supplier_id == $input.supplier_id)
          sort = {data_hora: "desc", id: "desc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
                } as $movement_page
              }
            }
          }
        }
      }
    }

    var $items {
      value = []
    }

    foreach ($movement_page.items) {
      each as $movement {
        array.push $items {
          value = {
            movement_id: $movement.id,
            product_id: $movement.product_id,
            product_code: $movement.product_code,
            product_name: $movement.product_name,
            tipo: $movement.tipo,
            quantidade: $movement.quantidade,
            data_hora: $movement.data_hora,
            user_id: $movement.user_id,
            user_name: $movement.user_name,
            supplier_id: $movement.supplier_id,
            supplier_name: $movement.supplier_name,
            motivo: $movement.motivo,
            observacao: $movement.observacao
          }
        }
      }
    }
  }

  response = $movement_page|set:"items":$items
}
