table "purchase_request" {
  auth = false

  schema {
    int id
    int produto_id {
      table = "product"
    }
    decimal quantidade_solicitada filters=min:0
    decimal quantidade_recebida? filters=min:0
    text? unidade_medida_solicitada?
    enum urgencia?="normal" {
      values = ["baixa", "normal", "alta", "critica"]
    }
    int solicitante_usuario_id {
      table = "user"
    }
    enum status?="aberta" {
      values = ["aberta", "em_analise", "aprovada", "em_compra", "aguardando_recebimento", "recebimento_parcial", "concluida", "cancelada", "rejeitada"]
    }
    enum email_status?="pendente" {
      values = ["pendente", "enviado", "falhou"]
    }
    text? email_destinatario? filters=trim {
      visibility = "internal"
    }
    text chave_idempotencia
    int? active_product_id? {
      table = "product"
    }
    timestamp data_criacao?=now
    timestamp data_atualizacao?=now
    timestamp? data_encerramento?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "chave_idempotencia"}]}
    {type: "btree|unique", field: [{name: "active_product_id"}]}
    {type: "btree", field: [{name: "produto_id"}, {name: "status"}]}
    {type: "btree", field: [{name: "status"}, {name: "data_criacao", op: "desc"}]}
    {type: "btree", field: [{name: "solicitante_usuario_id"}, {name: "data_criacao", op: "desc"}]}
  ]
}
