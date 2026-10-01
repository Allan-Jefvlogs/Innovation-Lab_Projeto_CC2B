function "Inventory/initialize_stock_balances" {
  description = "Inicializa uma única vez os saldos ausentes dos Produtos existentes em zero; não altera saldos já persistidos."
  input {
    int page?=1 filters=min:1
  }
  stack {
    db.query product {
      sort = {id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: 100, totals: true}}
    } as $products

    foreach ($products.items) {
      each as $product_item {
        db.query inventory_stock {
          where = $db.inventory_stock.product_id == $product_item.id
          return = {type: "single"}
        } as $existing_stock

        conditional {
          if ($existing_stock == null) {
            db.add inventory_stock {
              data = {
                product_id: $product_item.id,
                quantidade_disponivel: 0
              }
            } as $created_stock
          }
        }
      }
    }
  }

  response = {success: true, page: $input.page, products_checked: $products.items|count}
}
