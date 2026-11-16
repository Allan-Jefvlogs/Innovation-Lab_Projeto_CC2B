query "suppliers" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text nome_razao_social filters=trim
    text tipo_documento filters=trim
    text documento filters=trim
    text? contato? filters=trim
    text? endereco? filters=trim
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.create"}
    } as $authorization

    precondition ($input.nome_razao_social != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.documento != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    precondition ($input.tipo_documento == "CPF" || $input.tipo_documento == "CNPJ") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query supplier {
      where = $db.supplier.documento == $input.documento
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_VALUE"
    }

    db.transaction {
      stack {
        try_catch {
          try {
            db.add supplier {
              data = {
                nome_razao_social: $input.nome_razao_social,
                tipo_documento: $input.tipo_documento,
                documento: $input.documento,
                contato: $input.contato,
                endereco: $input.endereco
              }
            } as $supplier
          }
          catch {
            db.query supplier {
              where = $db.supplier.documento == $input.documento
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
                  name = "SUPPLIER_CREATE_FAILED"
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
            action_type: "criado",
            entity_type: "fornecedor",
            entity_id: $supplier.id,
            summary: "Fornecedor cadastrado.",
            changes: {after: {nome_razao_social: $supplier.nome_razao_social, tipo_documento: $supplier.tipo_documento}}
          }
        } as $audit_event
      }
    }
  }

  response = $supplier
}
