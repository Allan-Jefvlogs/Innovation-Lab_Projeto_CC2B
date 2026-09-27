query "categories/by_id/{category_id}" verb=PATCH {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    int category_id
    text nome?
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.update"}
    } as $authorization

    db.get category {
      field_name = "id"
      field_value = $input.category_id
    } as $existing

    precondition ($existing != null) {
      error_type = "notfound"
      error = "NOT_FOUND"
    }

    precondition ($input.nome != null) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query category {
      where = $db.category.nome == $input.nome && $db.category.id != $input.category_id
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_VALUE"
    }

    try_catch {
      try {
        db.edit category {
          field_name = "id"
          field_value = $input.category_id
          data = {nome: $input.nome}
        } as $category
      }
      catch {
        db.query category {
          where = $db.category.nome == $input.nome && $db.category.id != $input.category_id
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

  response = $category
}
