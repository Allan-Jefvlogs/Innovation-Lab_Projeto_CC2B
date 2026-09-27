query "suppliers" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text nome_razao_social
    text tipo_documento
    text documento
    text? contato?
    text? endereco?
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.create"}
    } as $authorization

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
              name = $error.name
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $supplier
}
