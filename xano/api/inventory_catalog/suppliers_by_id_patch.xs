query "suppliers/by_id/{supplier_id}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int supplier_id
    text nome_razao_social? filters=trim
    text tipo_documento? filters=trim
    text documento? filters=trim
    text contato? filters=trim
    bool limpar_contato?
    text endereco? filters=trim
    bool limpar_endereco?
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.update"}
    } as $authorization

    db.get supplier {
      field_name = "id"
      field_value = $input.supplier_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    precondition ($input.nome_razao_social == null || $input.nome_razao_social != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.documento == null || $input.documento != "") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    precondition (!($input.contato != null && $input.limpar_contato == true)) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition (!($input.endereco != null && $input.limpar_endereco == true)) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    var $updates {
      value = {}
    }

    conditional {
      if ($input.nome_razao_social != null) {
        var.update $updates.nome_razao_social {value = $input.nome_razao_social}
      }
    }
    conditional {
      if ($input.tipo_documento != null) {
        precondition ($input.tipo_documento == "CPF" || $input.tipo_documento == "CNPJ") {
          error_type = "inputerror"
          error = "INVALID_INPUT"
        }
        var.update $updates.tipo_documento {value = $input.tipo_documento}
      }
    }
    conditional {
      if ($input.documento != null) {
        db.query supplier {
          where = $db.supplier.documento == $input.documento && $db.supplier.id != $input.supplier_id
          return = {type: "exists"}
        } as $duplicate

        precondition (!$duplicate) {
          error_type = "inputerror"
          error = "DUPLICATE_VALUE"
        }

        var.update $updates.documento {value = $input.documento}
      }
    }
    conditional {
      if ($input.contato != null) {
        var.update $updates.contato {value = $input.contato}
      }
    }
    conditional {
      if ($input.limpar_contato == true) {
        var.update $updates.contato {value = null}
      }
    }
    conditional {
      if ($input.endereco != null) {
        var.update $updates.endereco {value = $input.endereco}
      }
    }
    conditional {
      if ($input.limpar_endereco == true) {
        var.update $updates.endereco {value = null}
      }
    }

    precondition (($updates|is_empty) == false) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    try_catch {
      try {
        db.patch supplier {
          field_name = "id"
          field_value = $input.supplier_id
          data = $updates
        } as $supplier
      }
      catch {
        conditional {
          if ($input.documento != null) {
            db.query supplier {
              where = $db.supplier.documento == $input.documento && $db.supplier.id != $input.supplier_id
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
              name = "SUPPLIER_UPDATE_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $supplier
}
