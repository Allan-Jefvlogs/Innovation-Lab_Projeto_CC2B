query "products" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text codigo
    text nome
    int categoria_id
    int fornecedor_padrao_id?
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

    conditional {
      if ($input.fornecedor_padrao_id != null) {
        db.get supplier {
          field_name = "id"
          field_value = $input.fornecedor_padrao_id
        } as $default_supplier

        precondition ($default_supplier != null && $default_supplier.status == "ativo") {
          error_type = "inputerror"
          error = "BUSINESS_RULE_VIOLATION"
        }
      }
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
        db.transaction {
          stack {
            db.add product {
              data = {
                codigo: $input.codigo,
                nome: $input.nome,
                categoria_id: $input.categoria_id,
                fornecedor_padrao_id: $input.fornecedor_padrao_id,
                unidade_medida: $input.unidade_medida,
                estoque_minimo: $input.estoque_minimo,
                descricao: $input.descricao
              }
            } as $product

            db.add inventory_stock {
              data = {
                product_id: $product.id,
                quantidade_disponivel: 0
              }
            } as $initial_stock

            db.get "user" {
              field_name = "id"
              field_value = $auth.id
              output = ["id", "name"]
            } as $audit_actor

            precondition ($audit_actor != null) {
              error_type = "accessdenied"
              error = "AUDIT_ACTOR_NOT_FOUND"
            }

            db.add inventory_audit_log {
              data = {
                actor_user_id: $audit_actor.id,
                actor_name: $audit_actor.name,
                action_type: "criado",
                entity_type: "produto",
                entity_id: $product.id,
                summary: "Produto cadastrado.",
                changes: {after: {codigo: $product.codigo, nome: $product.nome, unidade_medida: $product.unidade_medida, estoque_minimo: $product.estoque_minimo}}
              }
            } as $audit_event
          }
        }
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
