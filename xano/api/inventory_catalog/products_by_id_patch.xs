query "products/by_id/{product_id}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int product_id
    text codigo?
    text nome?
    text descricao?
    bool limpar_descricao?
    int categoria_id?
    text unidade_medida?
    decimal estoque_minimo? filters=min:0
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "product.update"}
    } as $authorization

    db.get product {
      field_name = "id"
      field_value = $input.product_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    precondition (!($input.descricao != null && $input.limpar_descricao == true)) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    var $updates {
      value = {}
    }

    conditional {
      if ($input.codigo != null) {
        db.query product {
          where = $db.product.codigo == $input.codigo && $db.product.id != $input.product_id
          return = {type: "exists"}
        } as $duplicate

        precondition (!$duplicate) {
          error_type = "inputerror"
          error = "DUPLICATE_VALUE"
        }

        var.update $updates.codigo {value = $input.codigo}
      }
    }

    conditional {
      if ($input.nome != null) {
        var.update $updates.nome {value = $input.nome}
      }
    }

    conditional {
      if ($input.descricao != null) {
        var.update $updates.descricao {value = $input.descricao}
      }
    }

    conditional {
      if ($input.limpar_descricao == true) {
        var.update $updates.descricao {value = null}
      }
    }

    conditional {
      if ($input.categoria_id != null) {
        conditional {
          if ($input.categoria_id != $existing.categoria_id) {
            db.get category {
              field_name = "id"
              field_value = $input.categoria_id
            } as $category

            precondition ($category != null && $category.status == "ativo") {
              error_type = "inputerror"
              error = "BUSINESS_RULE_VIOLATION"
            }
          }
        }
        var.update $updates.categoria_id {value = $input.categoria_id}
      }
    }

    conditional {
      if ($input.unidade_medida != null) {
        var.update $updates.unidade_medida {value = $input.unidade_medida}
      }
    }

    conditional {
      if ($input.estoque_minimo != null) {
        var.update $updates.estoque_minimo {value = $input.estoque_minimo}
      }
    }

    precondition (($updates|is_empty) == false) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    try_catch {
      try {
        db.patch product {
          field_name = "id"
          field_value = $input.product_id
          data = $updates
        } as $product
      }
      catch {
        conditional {
          if ($input.codigo != null) {
            db.query product {
              where = $db.product.codigo == $input.codigo && $db.product.id != $input.product_id
              return = {type: "exists"}
            } as $duplicate_after_write
          }
          else {
            var $duplicate_after_write {
              value = false
            }
          }
        }

        conditional {
          if ($duplicate_after_write) {
            throw {
              name = "DUPLICATE_VALUE"
              value = "DUPLICATE_VALUE"
            }
          }
          else {
            throw {
              name = "PRODUCT_UPDATE_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $product
}
