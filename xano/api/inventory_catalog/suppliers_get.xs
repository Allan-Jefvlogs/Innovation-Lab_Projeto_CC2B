query "suppliers" verb=GET {
  api_group = "Inventory Catalog"
  auth = "user"

  input {
    text status?
    text tipo_documento?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "supplier.read"}
    } as $authorization

    precondition ($input.status == null || $input.status == "ativo" || $input.status == "inativo") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.tipo_documento == null || $input.tipo_documento == "CPF" || $input.tipo_documento == "CNPJ") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query supplier {
      where = $db.supplier.status ==? $input.status && $db.supplier.tipo_documento ==? $input.tipo_documento
      sort = {id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $suppliers
  }

  response = $suppliers
}
