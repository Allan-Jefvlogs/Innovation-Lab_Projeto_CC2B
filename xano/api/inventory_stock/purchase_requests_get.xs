query "purchase_requests" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    text? status?
    int? produto_id?
    timestamp? data_inicio?
    timestamp? data_fim?
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.read"}
    } as $authorization

    function.run "Inventory/purchase_request_notification_all_access" {
      input = {user_id: $auth.id}
    } as $scope

    precondition ($input.status == null || $input.status == "aberta" || $input.status == "em_analise" || $input.status == "aprovada" || $input.status == "em_compra" || $input.status == "aguardando_recebimento" || $input.status == "recebimento_parcial" || $input.status == "concluida" || $input.status == "cancelada" || $input.status == "rejeitada") {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }
    precondition ($input.data_inicio == null || $input.data_fim == null || $input.data_inicio <= $input.data_fim) {
      error_type = "inputerror"
      error = "INVALID_INPUT"
    }

    db.query purchase_request {
      join = {
        product: {
          table: "product",
          where: $db.purchase_request.produto_id == $db.product.id
        }
      }
      eval = {
        produto_codigo: $db.product.codigo,
        produto_nome: $db.product.nome
      }
      output = [
        "items.id",
        "items.produto_id",
        "items.produto_codigo",
        "items.produto_nome",
        "items.quantidade_solicitada",
        "items.quantidade_recebida",
        "items.unidade_medida_solicitada",
        "items.urgencia",
        "items.solicitante_usuario_id",
        "items.status",
        "items.email_status",
        "items.data_criacao",
        "items.data_atualizacao",
        "items.data_encerramento",
        "itemsTotal",
        "curPage",
        "perPage"
      ]
      where = ($scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id) && $db.purchase_request.status ==? $input.status && $db.purchase_request.produto_id ==? $input.produto_id && $db.purchase_request.data_criacao >=? $input.data_inicio && $db.purchase_request.data_criacao <=? $input.data_fim
      sort = {data_criacao: "desc", id: "desc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $requests_page
  }

  response = $requests_page
}
