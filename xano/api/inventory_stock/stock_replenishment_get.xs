query "stock/replenishment" verb=GET {
  api_group = "Inventory Stock"
  auth = "user"

  input {
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1|max:100
    int requested_page?=1 filters=min:1
    int requested_per_page?=20 filters=min:1|max:100
  }

  stack {
    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "stock.read"}
    } as $stock_authorization

    function.run "Inventory/authorize_permission" {
      input = {user_id: $auth.id, permission_code: "purchase_request.read"}
    } as $request_authorization

    function.run "Inventory/purchase_request_notification_all_access" {
      input = {user_id: $auth.id}
    } as $scope

    db.query product {
      join = {
        inventory_stock: {
          table: "inventory_stock",
          type: "left",
          where: $db.product.id == $db.inventory_stock.product_id
        }
      }
      where = $db.product.status == "ativo" && $db.inventory_stock.id == null
      return = {type: "exists"}
    } as $has_product_without_balance

    precondition ($has_product_without_balance == false) {
      error_type = "standard"
      error = "STOCK_BALANCE_NOT_FOUND"
    }

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        },
        active_request: {
          table: "purchase_request",
          type: "left",
          where: $db.inventory_stock.product_id == $db.active_request.active_product_id && ($db.active_request.status == "aberta" || $db.active_request.status == "em_analise" || $db.active_request.status == "aprovada" || $db.active_request.status == "em_compra" || $db.active_request.status == "aguardando_recebimento" || $db.active_request.status == "recebimento_parcial")
        }
      }
      eval = {
        codigo: $db.product.codigo,
        nome: $db.product.nome,
        unidade_medida: $db.product.unidade_medida,
        estoque_minimo: $db.product.estoque_minimo,
        solicitacao_id: $db.active_request.id,
        quantidade_solicitada: $db.active_request.quantidade_solicitada,
        urgencia_solicitacao: $db.active_request.urgencia,
        solicitacao_status: $db.active_request.status,
        data_criacao_solicitacao: $db.active_request.data_criacao
      }
      output = [
        "items.product_id",
        "items.codigo",
        "items.nome",
        "items.unidade_medida",
        "items.quantidade_disponivel",
        "items.estoque_minimo",
        "itemsTotal"
      ]
      where = $db.product.status == "ativo" && ($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo)) && $db.active_request.id == null
      sort = {product_id: "asc"}
      return = {type: "list", paging: {page: $input.page, per_page: $input.per_page, totals: true}}
    } as $eligible_page

    db.query inventory_stock {
      join = {
        product: {
          table: "product",
          type: "inner",
          where: $db.inventory_stock.product_id == $db.product.id
        },
        active_request: {
          table: "purchase_request",
          type: "left",
          where: $db.inventory_stock.product_id == $db.active_request.active_product_id && ($db.active_request.status == "aberta" || $db.active_request.status == "em_analise" || $db.active_request.status == "aprovada" || $db.active_request.status == "em_compra" || $db.active_request.status == "aguardando_recebimento" || $db.active_request.status == "recebimento_parcial")
        }
      }
      eval = {
        codigo: $db.product.codigo,
        nome: $db.product.nome,
        unidade_medida: $db.product.unidade_medida,
        estoque_minimo: $db.product.estoque_minimo,
        solicitante_usuario_id: $db.active_request.solicitante_usuario_id,
        solicitacao_id: $db.active_request.id,
        quantidade_solicitada: $db.active_request.quantidade_solicitada,
        urgencia_solicitacao: $db.active_request.urgencia,
        solicitacao_status: $db.active_request.status,
        data_criacao_solicitacao: $db.active_request.data_criacao
      }
      output = [
        "items.product_id",
        "items.codigo",
        "items.nome",
        "items.unidade_medida",
        "items.quantidade_disponivel",
        "items.estoque_minimo",
        "items.solicitante_usuario_id",
        "items.solicitacao_id",
        "items.quantidade_solicitada",
        "items.urgencia_solicitacao",
        "items.solicitacao_status",
        "items.data_criacao_solicitacao",
        "itemsTotal"
      ]
      where = $db.product.status == "ativo" && ($db.inventory_stock.quantidade_disponivel == 0 || ($db.inventory_stock.quantidade_disponivel > 0 && $db.inventory_stock.quantidade_disponivel < $db.product.estoque_minimo)) && $db.active_request.id != null
      sort = {product_id: "asc"}
      return = {type: "list", paging: {page: $input.requested_page, per_page: $input.requested_per_page, totals: true}}
    } as $requested_page

    var $eligible_items {
      value = []
    }

    foreach ($eligible_page.items) {
      each as $item {
        var $situacao_estoque {
          value = ""
        }

        conditional {
          if ($item.quantidade_disponivel == 0) {
            var.update $situacao_estoque {
              value = "sem_estoque"
            }
          }
          else {
            var.update $situacao_estoque {
              value = "abaixo_minimo"
            }
          }
        }

        array.push $eligible_items {
          value = {
            produto_id: $item.product_id,
            codigo: $item.codigo,
            nome: $item.nome,
            unidade_medida: $item.unidade_medida,
            quantidade_disponivel: $item.quantidade_disponivel,
            estoque_minimo: $item.estoque_minimo,
            situacao_estoque: $situacao_estoque
          }
        }
      }
    }

    var $requested_items {
      value = []
    }

    foreach ($requested_page.items) {
      each as $item {
        var $can_view_request_details {
          value = $scope.all_access || $item.solicitante_usuario_id == $auth.id
        }
        var $request_details {
          value = {
            solicitacao_id: null,
            quantidade_solicitada: null,
            urgencia: null,
            solicitacao_status: null,
            data_criacao_solicitacao: null
          }
        }
        conditional {
          if ($can_view_request_details) {
            var.update $request_details {
              value = {
                solicitacao_id: $item.solicitacao_id,
                quantidade_solicitada: $item.quantidade_solicitada,
                urgencia: $item.urgencia_solicitacao,
                solicitacao_status: $item.solicitacao_status,
                data_criacao_solicitacao: $item.data_criacao_solicitacao
              }
            }
          }
        }

        var $situacao_estoque {
          value = ""
        }

        conditional {
          if ($item.quantidade_disponivel == 0) {
            var.update $situacao_estoque {
              value = "sem_estoque"
            }
          }
          else {
            var.update $situacao_estoque {
              value = "abaixo_minimo"
            }
          }
        }

        array.push $requested_items {
          value = {
            produto_id: $item.product_id,
            codigo: $item.codigo,
            nome: $item.nome,
            unidade_medida: $item.unidade_medida,
            quantidade_disponivel: $item.quantidade_disponivel,
            estoque_minimo: $item.estoque_minimo,
            situacao_estoque: $situacao_estoque,
            solicitacao_detalhes_disponiveis: $can_view_request_details,
            solicitacao_id: $request_details.solicitacao_id,
            quantidade_solicitada: $request_details.quantidade_solicitada,
            urgencia: $request_details.urgencia,
            solicitacao_status: $request_details.solicitacao_status,
            data_criacao_solicitacao: $request_details.data_criacao_solicitacao
          }
        }
      }
    }
  }

  response = {
    a_solicitar: {
      items: $eligible_items,
      curPage: $input.page,
      perPage: $input.per_page,
      itemsTotal: $eligible_page.itemsTotal
    },
    compra_ja_solicitada: {
      items: $requested_items,
      curPage: $input.requested_page,
      perPage: $input.requested_per_page,
      itemsTotal: $requested_page.itemsTotal
    }
  }
}
