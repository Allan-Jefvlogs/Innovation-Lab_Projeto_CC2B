query "stock_summary" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "stock.read"}
    } as $authorization

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        }
      }
      where = $db.inventory_stock.quantidade_disponivel == 0
      return = {type: "list", paging: {page: 1, per_page: 1, totals: true}}
    } as $sem_estoque

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        }
      }
      where = $db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo
      return = {type: "list", paging: {page: 1, per_page: 1, totals: true}}
    } as $abaixo_minimo

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        }
      }
      where = $db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel >= $db.product.estoque_minimo
      return = {type: "list", paging: {page: 1, per_page: 1, totals: true}}
    } as $normal

    var $total {
      value = $normal.itemsTotal + $abaixo_minimo.itemsTotal + $sem_estoque.itemsTotal
    }
  }

  response = {
    total: $total,
    normal: $normal.itemsTotal,
    abaixo_minimo: $abaixo_minimo.itemsTotal,
    sem_estoque: $sem_estoque.itemsTotal
  }
}
