query "stock/insufficient_summary" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int page?=1 filters=min:1
    int per_page?=5 filters=min:1|max:20
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "stock.read"}
    } as $authorization

    db.query product {
      join = {
        inventory_stock: {
          table: "inventory_stock",
          type: "left",
          where: $db.product.id == $db.inventory_stock.product_id
        }
      }
      where = $db.product.status == "ativo" && $db.inventory_stock.id == null
      return = {type: "exists"}
    } as $has_product_without_balance

    precondition ($has_product_without_balance == false) {
      error_type = "standard"
      error = "STOCK_BALANCE_NOT_FOUND"
    }

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        }
      }
      where = $db.product.status == "ativo" && ($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo))
      return = {type: "count"}
    } as $insufficient_total

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        }
      }
      eval = {
        codigo: $db.product.codigo,
        nome: $db.product.nome,
        unidade_medida: $db.product.unidade_medida,
        estoque_minimo: $db.product.estoque_minimo
      }
      output = [
        "items.product_id",
        "items.codigo",
        "items.nome",
        "items.unidade_medida",
        "items.quantidade_disponivel",
        "items.estoque_minimo"
      ]
      where = $db.product.status == "ativo" && ($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo))
      sort = {product_id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $insufficient_page

    var $alert_items {
      value = []
    }

    foreach ($insufficient_page.items) {
      each as $item {
        var $situation {
          value = "abaixo_minimo"
        }

        conditional {
          if ($item.quantidade_disponivel == 0) {
            var.update $situation {
              value = "sem_estoque"
            }
          }
        }

        array.push $alert_items {
          value = {
            product_id: $item.product_id,
            codigo: $item.codigo,
            nome: $item.nome,
            quantidade_disponivel: $item.quantidade_disponivel,
            estoque_minimo: $item.estoque_minimo,
            unidade_medida: $item.unidade_medida,
            situacao_estoque: $situation
          }
        }
      }
    }
  }

  response = {
    items: $alert_items,
    itemsTotal: $insufficient_total,
    curPage: $input.page,
    perPage: $input.per_page
  }
}
