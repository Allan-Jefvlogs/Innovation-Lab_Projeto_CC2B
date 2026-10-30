function "Inventory/resolve_purchase_request_email_provider" {
  description = "Resolve a configuracao do provedor selecionado sem retornar segredos."
  input {
    text? provedor_solicitado?
    email? destinatario_solicitado?
  }
  stack {
    var $provider {
      value = null
    }
    conditional {
      if ($input.provedor_solicitado != null && $input.provedor_solicitado != "") {
        var.update $provider { value = $input.provedor_solicitado }
      }
      else {
        var.update $provider { value = $env.NEXSTOCK_EMAIL_PROVIDER }
      }
    }
    var $valid {
      value = false
    }
    var $from_email {
      value = null
    }
    var $from_name {
      value = null
    }
    var $reply_to {
      value = null
    }
    var $error_code {
      value = "EMAIL_PROVIDER_INVALID"
    }

    conditional {
      if ($provider == "brevo") {
        var.update $from_email { value = $env.BREVO_FROM_EMAIL }
        var.update $from_name { value = $env.BREVO_FROM_NAME }
        var.update $reply_to { value = $env.BREVO_REPLY_TO }

        conditional {
          if ($env.BREVO_API_KEY != null && $env.BREVO_API_KEY != "" && $env.BREVO_FROM_EMAIL != null && $env.BREVO_FROM_EMAIL != "" && $env.BREVO_FROM_NAME != null && $env.BREVO_FROM_NAME != "") {
            var.update $valid { value = true }
            var.update $error_code { value = null }
          }
          else {
            var.update $error_code { value = "EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE" }
          }
        }
      }
      elseif ($provider == "resend") {
        var.update $from_email { value = $env.RESEND_FROM_EMAIL }
        var.update $reply_to { value = $env.RESEND_REPLY_TO }

        conditional {
          if ($env.RESEND_API_KEY != null && $env.RESEND_API_KEY != "" && $env.RESEND_FROM_EMAIL == "onboarding@resend.dev" && $env.RESEND_ALLOWED_TEST_RECIPIENT != null && $env.RESEND_ALLOWED_TEST_RECIPIENT != "" && ($input.destinatario_solicitado == null || $env.RESEND_ALLOWED_TEST_RECIPIENT == $input.destinatario_solicitado)) {
            var.update $valid { value = true }
            var.update $error_code { value = null }
          }
          else {
            var.update $error_code { value = "EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE" }
          }
        }
      }
    }
  }
  response = {
    valid: $valid,
    provedor: $provider,
    remetente: $from_email,
    nome_remetente: $from_name,
    reply_to: $reply_to,
    codigo_erro: $error_code
  }
}
