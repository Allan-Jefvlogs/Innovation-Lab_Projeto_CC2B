table "purchase_request_email_delivery" {
  auth = false

  schema {
    int id
    int purchase_request_id {
      table = "purchase_request"
    }
    enum tipo_evento {
      values = ["solicitacao", "cancelamento"]
    }
    email destinatario {
      sensitive = true
    }
    enum status?="pendente" {
      values = ["pendente", "aguardando_confirmacao_original", "processando", "enviado", "falhou", "indeterminado", "suprimido"]
    }
    text provedor?="resend"
    text? id_mensagem_provedor?
    text chave_idempotencia
    json payload_snapshot {
      sensitive = true
    }
    int tentativas?=0 filters=min:0
    timestamp? data_ultima_tentativa?
    timestamp? data_confirmacao?
    text? codigo_erro?
    timestamp data_criacao?=now
    timestamp data_atualizacao?=now
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "chave_idempotencia"}]}
    {type: "btree|unique", field: [{name: "purchase_request_id"}, {name: "tipo_evento"}]}
    {type: "btree", field: [{name: "status"}, {name: "data_criacao", op: "asc"}]}
    {type: "btree", field: [{name: "purchase_request_id"}, {name: "data_criacao", op: "asc"}]}
  ]
}
