query "categories" verb=POST {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text nome
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "category.create"}
    } as $authorization

    db.query category {
      where = $db.category.nome == $input.nome
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_VALUE"
    }

    try_catch {
      try {
        db.add category {
          data = {nome: $input.nome}
        } as $category
      }
      catch {
        db.query category {
          where = $db.category.nome == $input.nome
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
              name = "CATEGORY_CREATE_FAILED"
              value = $error.message
            }
          }
        }
      }
    }
  }

  response = $category
}
