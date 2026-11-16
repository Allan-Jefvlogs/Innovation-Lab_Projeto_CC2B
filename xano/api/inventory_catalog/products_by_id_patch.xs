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
    int fornecedor_padrao_id?
    bool limpar_fornecedor_padrao?
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

    precondition (!($input.fornecedor_padrao_id != null && $input.limpar_fornecedor_padrao == true)) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    precondition (!($input.limpar_fornecedor_padrao == true && $existing.fornecedor_padrao_id == null)) {
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

        var.update $updates.codigo {
          value = $input.codigo
        }
      }
    }

    conditional {
      if ($input.nome != null) {
        var.update $updates.nome {
          value = $input.nome
        }
      }
    }

    conditional {
      if ($input.descricao != null) {
        var.update $updates.descricao {
          value = $input.descricao
        }
      }
    }

    conditional {
      if ($input.limpar_descricao == true) {
        var.update $updates.descricao {
          value = null
        }
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

        var.update $updates.categoria_id {
          value = $input.categoria_id
        }
      }
    }

    conditional {
      if ($input.fornecedor_padrao_id != null) {
        conditional {
          if ($input.fornecedor_padrao_id != $existing.fornecedor_padrao_id) {
            db.get supplier {
              field_name = "id"
              field_value = $input.fornecedor_padrao_id
            } as $default_supplier

            precondition ($default_supplier != null && $default_supplier.status == "ativo") {
              error_type = "inputerror"
              error = "BUSINESS_RULE_VIOLATION"
            }

            var.update $updates.fornecedor_padrao_id {
              value = $input.fornecedor_padrao_id
            }
          }
        }
      }
    }

    conditional {
      if ($input.limpar_fornecedor_padrao == true) {
        var.update $updates.fornecedor_padrao_id {
          value = null
        }
      }
    }

    conditional {
      if ($input.unidade_medida != null) {
        var.update $updates.unidade_medida {
          value = $input.unidade_medida
        }
      }
    }

    conditional {
      if ($input.estoque_minimo != null) {
        var.update $updates.estoque_minimo {
          value = $input.estoque_minimo
        }
      }
    }

    precondition (($updates|is_empty) == false) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.transaction {
      stack {
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
            action_type: "atualizado",
            entity_type: "produto",
            entity_id: $product.id,
            summary: "Produto atualizado.",
            changes: {
              before: {
                codigo: $existing.codigo,
                nome: $existing.nome,
                descricao: $existing.descricao,
                categoria_id: $existing.categoria_id,
                fornecedor_padrao_id: $existing.fornecedor_padrao_id,
                unidade_medida: $existing.unidade_medida,
                estoque_minimo: $existing.estoque_minimo
              },
              after: {
                codigo: $product.codigo,
                nome: $product.nome,
                descricao: $product.descricao,
                categoria_id: $product.categoria_id,
                fornecedor_padrao_id: $product.fornecedor_padrao_id,
                unidade_medida: $product.unidade_medida,
                estoque_minimo: $product.estoque_minimo
              }
            }
          }
        } as $audit_event
      }
    }
  }

  response = $product
}