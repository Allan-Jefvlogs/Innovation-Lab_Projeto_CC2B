query "purchase_requests/by_id/{request_id}" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int request_id
    int history_page?=1 filters=min:1
    int history_per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.read"}
    } as $authorization

    db.get purchase_request {
      field_name = "id"
      field_value = $input.request_id
    } as $request

    precondition ($request != null) {
      error_type = "inputerror"
      error = "PURCHASE_REQUEST_NOT_FOUND"
    }

    db.get product {
      field_name = "id"
      field_value = $request.produto_id
    } as $product

    db.query purchase_request_history {
      where = $db.purchase_request_history.purchase_request_id == $request.id
      sort = {data_evento: "desc", id: "desc"}
      output = [
        "items.id",
        "items.actor_user_id",
        "items.evento",
        "items.justificativa",
        "items.dados",
        "items.data_evento"
      ]
      return = {type: "list", paging: {page: $input.history_page, per_page: $input.history_per_page, totals: true}}
    } as $history_page
  }

  response = {
    solicitacao: {
      id: $request.id,
      produto_id: $request.produto_id,
      quantidade_solicitada: $request.quantidade_solicitada,
      quantidade_recebida: $request.quantidade_recebida,
      urgencia: $request.urgencia,
      solicitante_usuario_id: $request.solicitante_usuario_id,
      status: $request.status,
      email_status: $request.email_status,
      data_criacao: $request.data_criacao,
      data_atualizacao: $request.data_atualizacao,
      data_encerramento: $request.data_encerramento
    },
    produto: {
      id: $product.id,
      codigo: $product.codigo,
      nome: $product.nome,
      unidade_medida: $product.unidade_medida
    },
    historico: $history_page
  }
}
