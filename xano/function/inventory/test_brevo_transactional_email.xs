function "Inventory/test_brevo_transactional_email" {
  description = "Envia uma única mensagem técnica ao destinatário configurado, sem acessar dados do NexStock. A execução permanece bloqueada até confirmar proteção do Request History contra exposição de headers e corpo."
  input {
    bool confirm_send
  }
  stack {
    var $success {
      value = false
    }
    var $http_status {
      value = null
    }
    var $error_category {
      value = "confirmation_required"
    }

    conditional {
      if ($input.confirm_send == true) {
        conditional {
          if ($env.BREVO_API_KEY == null || $env.BREVO_API_KEY == "" || $env.BREVO_FROM_EMAIL == null || $env.BREVO_FROM_EMAIL == "" || $env.BREVO_FROM_NAME == null || $env.BREVO_FROM_NAME == "" || $env.BREVO_TEST_RECIPIENT == null || $env.BREVO_TEST_RECIPIENT == "") {
            var.update $error_category {
              value = "configuration_missing"
            }
          }
          else {
            var.update $error_category {
              value = "timeout_or_transport_indeterminate"
            }

            try_catch {
              try {
                api.request {
                  url = "https://api.brevo.com/v3/smtp/email"
                  method = "POST"
                  params = {
                    sender: {
                      email: $env.BREVO_FROM_EMAIL,
                      name: $env.BREVO_FROM_NAME
                    },
                    to: [{email: $env.BREVO_TEST_RECIPIENT}],
                    subject: "NexStock - Teste tecnico Xano Brevo",
                    textContent: "Teste tecnico unico da integracao Xano para Brevo do NexStock. Esta mensagem nao corresponde a uma solicitacao de compra."
                  }
                  headers = [
                    "api-key: " ~ $env.BREVO_API_KEY,
                    "Content-Type: application/json"
                  ]
                  timeout = 15
                } as $brevo_result

                var.update $http_status {
                  value = $brevo_result.response.status
                }

                conditional {
                  if ($brevo_result.response.status >= 200 && $brevo_result.response.status < 300) {
                    var.update $success {
                      value = true
                    }
                    var.update $error_category {
                      value = "none"
                    }
                  }
                  elseif ($brevo_result.response.status == null) {
                    var.update $error_category {
                      value = "timeout_or_transport_indeterminate"
                    }
                  }
                  elseif ($brevo_result.response.status == 408) {
                    var.update $error_category {
                      value = "http_408_indeterminate"
                    }
                  }
                  elseif ($brevo_result.response.status == 401) {
                    var.update $error_category {
                      value = "http_401_unauthorized"
                    }
                  }
                  elseif ($brevo_result.response.status == 403) {
                    var.update $error_category {
                      value = "http_403_forbidden"
                    }
                  }
                  elseif ($brevo_result.response.status == 429) {
                    var.update $error_category {
                      value = "http_429_rejected"
                    }
                  }
                  elseif ($brevo_result.response.status >= 500) {
                    var.update $error_category {
                      value = "http_5xx_indeterminate"
                    }
                  }
                  elseif ($brevo_result.response.status >= 400) {
                    var.update $error_category {
                      value = "http_4xx_rejected"
                    }
                  }
                  else {
                    var.update $error_category {
                      value = "http_status_indeterminate"
                    }
                  }
                }
              }
              catch {
                // Do not inspect or expose raw exception text. A timeout or
                // transport error may happen after Brevo accepted the email.
                var.update $error_category {
                  value = "timeout_or_transport_indeterminate"
                }
              }
            }
          }
        }
      }
    }
  }
  response = {
    success: $success,
    http_status: $http_status,
    error_category: $error_category
  }
}
