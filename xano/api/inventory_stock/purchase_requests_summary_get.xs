query "purchase_requests/summary" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {}

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.read"}
    } as $authorization

    function.run "Inventory/purchase_request_notification_all_access" {
      input = {user_id: $auth.id}
    } as $scope

    db.query purchase_request {
      where = ($scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id) && ($db.purchase_request.status == "aberta" || $db.purchase_request.status == "em_analise" || $db.purchase_request.status == "aprovada" || $db.purchase_request.status == "em_compra" || $db.purchase_request.status == "aguardando_recebimento" || $db.purchase_request.status == "recebimento_parcial")
      return = {type: "count"}
    } as $open_requests_count
  }

  response = {solicitacoes_abertas: $open_requests_count}
}
