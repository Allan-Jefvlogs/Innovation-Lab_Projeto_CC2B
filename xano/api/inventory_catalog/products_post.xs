query "products" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text codigo
    text nome
    int categoria_id
    text unidade_medida
    decimal estoque_minimo filters=min:0
    text? descricao?
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.create"}
    } as $authorization

    db.get category {
      field_name = "id"
      field_value = $input.categoria_id
    } as $category

    precondition ($category != null) {
      error_type = "inputerror"
      error = "BUSINESS_RULE_VIOLATION"
    }
    precondition ($category.status == "ativo") {
      error_type = "inputerror"
      error = "BUSINESS_RULE_VIOLATION"
    }

    db.query product {
      where = $db.product.codigo == $input.codigo
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_VALUE"
    }

    try_catch {
      try {
        db.add product {
          data = {
            codigo: $input.codigo,
            nome: $input.nome,
            categoria_id: $input.categoria_id,
            unidade_medida: $input.unidade_medida,
            estoque_minimo: $input.estoque_minimo,
            descricao: $input.descricao
          }
        } as $product
      }
      catch {
        db.query product {
          where = $db.product.codigo == $input.codigo
          return = {type: "exists"}
        } as $duplicate_after_write

        conditional {
          if ($duplicate_after_write) {
            throw {
              name = "DUPLICATE_VALUE"
              value = "DUPLICATE_VALUE"
            }
          }
          else {
            throw {
              name = "PRODUCT_CREATE_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $product
}
