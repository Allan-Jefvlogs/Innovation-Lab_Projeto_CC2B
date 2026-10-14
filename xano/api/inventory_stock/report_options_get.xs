query "report_options" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    text kind
    int page?=1 filters=min:1
    int per_page?=100 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "report.read"}
    } as $authorization

    precondition ($input.kind == "product" || $input.kind == "supplier") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    var $options_page {
      value = {}
    }

    conditional {
      if ($input.kind == "product") {
        db.query product {
          sort = {codigo: "asc", id: "asc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
          output = ["id", "codigo", "nome"]
        } as $product_options_page

        var $product_items {
          value = []
        }

        foreach ($product_options_page.items) {
          each as $product_item {
            array.push $product_items {
              value = {
                id: $product_item.id,
                codigo: $product_item.codigo,
                nome: $product_item.nome
              }
            }
          }
        }

        var.update $options_page {
          value = $product_options_page|set:"items":$product_items
        }
      }
      else {
        db.query supplier {
          sort = {nome_razao_social: "asc", id: "asc"}
          return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
          output = ["id", "nome_razao_social"]
        } as $supplier_options_page

        var $supplier_items {
          value = []
        }

        foreach ($supplier_options_page.items) {
          each as $supplier_item {
            array.push $supplier_items {
              value = {
                id: $supplier_item.id,
                nome_razao_social: $supplier_item.nome_razao_social
              }
            }
          }
        }

        var.update $options_page {
          value = $supplier_options_page|set:"items":$supplier_items
        }
      }
    }
  }

  response = $options_page
}
