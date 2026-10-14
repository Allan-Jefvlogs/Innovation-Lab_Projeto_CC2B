query "stock" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    text? situacao?
    text? search?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "stock.read"}
    } as $authorization

    precondition ($input.situacao == null || $input.situacao == "normal" || $input.situacao == "abaixo_minimo" || $input.situacao == "sem_estoque") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        },
        category: {
          table: "category",
          type: "left",
          where: $db.product.categoria_id == $db.category.id
        },
        supplier: {
          table: "supplier",
          type: "left",
          where: $db.product.fornecedor_padrao_id == $db.supplier.id
        }
      }
      eval = {
        codigo: $db.product.codigo,
        nome: $db.product.nome,
        estoque_minimo: $db.product.estoque_minimo,
        categoria_id: $db.product.categoria_id,
        categoria_nome: $db.category.nome,
        fornecedor_padrao_id: $db.product.fornecedor_padrao_id,
        fornecedor_nome: $db.supplier.nome_razao_social
      }
      where = ($input.situacao == null || ($input.situacao == "sem_estoque" && $db.inventory_stock.quantidade_disponivel == 0) || ($input.situacao == "abaixo_minimo" && $db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo) || ($input.situacao == "normal" && $db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel >= $db.product.estoque_minimo)) && ($input.search == null || $input.search == "" || $db.product.codigo includes $input.search || $db.product.nome includes $input.search)
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
            categoria_id: $stock_item.categoria_id,
            categoria_nome: $stock_item.categoria_nome,
            fornecedor_padrao_id: $stock_item.fornecedor_padrao_id,
            fornecedor_nome: $stock_item.fornecedor_nome,
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
