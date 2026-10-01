query "stock" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
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
      eval = {
        codigo: $db.product.codigo,
        nome: $db.product.nome,
        estoque_minimo: $db.product.estoque_minimo
      }
      sort = {product_id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $stock_page

    var $items {
      value = []
    }

    foreach ($stock_page.items) {
      each as $stock_item {
        var $situacao_estoque {
          value = ""
        }

        conditional {
          if ($stock_item.quantidade_disponivel == 0) {
            var.update $situacao_estoque {
              value = "sem_estoque"
            }
          }
          else {
            conditional {
              if ($stock_item.quantidade_disponivel < $stock_item.estoque_minimo) {
                var.update $situacao_estoque {
                  value = "abaixo_minimo"
                }
              }
              else {
                var.update $situacao_estoque {
                  value = "normal"
                }
              }
            }
          }
        }

        array.push $items {
          value = {
            product_id: $stock_item.product_id,
            codigo: $stock_item.codigo,
            nome: $stock_item.nome,
            quantidade_disponivel: $stock_item.quantidade_disponivel,
            estoque_minimo: $stock_item.estoque_minimo,
            situacao_estoque: $situacao_estoque
          }
        }
      }
    }
  }

  response = $stock_page|set:"items":$items
}
