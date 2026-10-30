function "Inventory/build_purchase_request_email_payload" {
  description = "Monta um snapshot de e-mail transacional em texto simples; não envia mensagens."
  input {
    text tipo_evento
    int request_id
    email destinatario
    text? remetente?
    text? nome_remetente?
    email? reply_to?
    text produto_codigo
    text produto_nome
    decimal quantidade
    text unidade_medida
    text urgencia
    text data_evento
  }
  stack {
    precondition ($input.tipo_evento == "solicitacao" || $input.tipo_evento == "cancelamento") {
      error_type = "inputerror"
      error = "INVALID_EMAIL_EVENT_TYPE"
    }

    var $subject {
      value = ""
    }
    var $body {
      value = ""
    }
    var $html_body {
      value = ""
    }
    var $payload {
      value = null
    }

    conditional {
      if ($input.tipo_evento == "solicitacao") {
        var.update $subject {
          value = "Solicitação de compra #" ~ ($input.request_id|to_text) ~ " registrada - NexStock"
        }
        var.update $body {
          value = "Olá,\n\nA solicitação de compra #" ~ ($input.request_id|to_text) ~ " foi registrada no NexStock.\n\nProduto: " ~ $input.produto_codigo ~ " - " ~ $input.produto_nome ~ "\nQuantidade: " ~ ($input.quantidade|to_text) ~ " " ~ $input.unidade_medida ~ "\nUrgência: " ~ $input.urgencia ~ "\nData: " ~ $input.data_evento ~ "\n\nEsta mensagem confirma o registro da solicitação, não a compra ou o recebimento do material.\n\nNexStock"
        }
      }
      else {
        var.update $subject {
          value = "Cancelamento da solicitação #" ~ ($input.request_id|to_text) ~ " - NexStock"
        }
        var.update $body {
          value = "Olá,\n\nA solicitação de compra #" ~ ($input.request_id|to_text) ~ " foi cancelada no NexStock.\n\nProduto: " ~ $input.produto_codigo ~ " - " ~ $input.produto_nome ~ "\nQuantidade solicitada: " ~ ($input.quantidade|to_text) ~ " " ~ $input.unidade_medida ~ "\nData: " ~ $input.data_evento ~ "\n\nPor favor, desconsidere a mensagem anterior sobre esta solicitação.\n\nNexStock"
        }
      }
    }

    var.update $html_body {
      value = "<!doctype html><html><body><pre style='white-space:pre-wrap;font-family:Arial,sans-serif'>" ~ ($body|replace:"&":"&amp;"|replace:"<":"&lt;"|replace:">":"&gt;") ~ "</pre></body></html>"
    }

    var.update $payload {
      value = {
        from: $input.remetente,
        from_name: $input.nome_remetente,
        to: $input.destinatario,
        subject: $subject,
        text: $body,
        html: $html_body
      }
    }

    conditional {
      if ($input.reply_to != null && $input.reply_to != "") {
        var.update $payload {
          value = {
            from: $input.remetente,
            from_name: $input.nome_remetente,
            to: $input.destinatario,
            reply_to: $input.reply_to,
            subject: $subject,
            text: $body,
            html: $html_body
          }
        }
      }
    }
  }
  response = $payload

  test "builds original request message in Portuguese" {
    input = {
      tipo_evento: "solicitacao",
      request_id: 104,
      destinatario: "compras@example.com",
      remetente: "onboarding@resend.dev",
      nome_remetente: null,
      reply_to: "respostas@example.com",
      produto_codigo: "P-1",
      produto_nome: "Produto <teste>",
      quantidade: 2.5,
      unidade_medida: "KG",
      urgencia: "alta",
      data_evento: "2026-10-26"
    }
    expect.to_equal ($response.subject) { value = "Solicitação de compra #104 registrada - NexStock" }
    expect.to_contain ($response.text) { value = "Esta mensagem confirma o registro da solicitação" }
    expect.to_contain ($response.html) { value = "&lt;teste&gt;" }
    expect.to_equal ($response.to) { value = "compras@example.com" }
    expect.to_equal ($response.from) { value = "onboarding@resend.dev" }
    expect.to_equal ($response.reply_to) { value = "respostas@example.com" }
  }

  test "builds cancellation notice without justification" {
    input = {
      tipo_evento: "cancelamento",
      request_id: 104,
      destinatario: "compras@example.com",
      produto_codigo: "P-1",
      produto_nome: "Produto teste",
      quantidade: 2.5,
      unidade_medida: "KG",
      urgencia: "alta",
      data_evento: "2026-10-26"
    }
    expect.to_equal ($response.subject) { value = "Cancelamento da solicitação #104 - NexStock" }
    expect.to_contain ($response.text) { value = "desconsidere a mensagem anterior" }
  }
}
