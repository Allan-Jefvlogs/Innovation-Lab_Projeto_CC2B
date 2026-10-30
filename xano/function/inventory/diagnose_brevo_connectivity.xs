function "Inventory/diagnose_brevo_connectivity" {
  description = "Verifica conectividade HTTPS e autenticação de leitura Brevo sem enviar e-mails nem expor detalhes sensíveis."
  input {}
  stack {
    var $success {
      value = false
    }
    var $http_status {
      value = null
    }
    var $error_category {
      value = "not_started"
    }

    conditional {
      if ($env.BREVO_API_KEY == null || $env.BREVO_API_KEY == "") {
        var.update $error_category { value = "configuration_missing" }
      }
      else {
        var.update $error_category { value = "connection_error" }

        try_catch {
          try {
            api.request {
              url = "https://api.brevo.com/v3/smtp/statistics/aggregatedReport?days=1"
              method = "GET"
              headers = ["api-key: " ~ $env.BREVO_API_KEY]
              timeout = 10
            } as $brevo_result

            var.update $http_status { value = $brevo_result.response.status }

            conditional {
              if ($brevo_result.response.status >= 200 && $brevo_result.response.status < 300) {
                var.update $success { value = true }
                var.update $error_category { value = "none" }
              }
              elseif ($brevo_result.response.status == 401) {
                var.update $error_category { value = "http_401_unauthorized" }
              }
              elseif ($brevo_result.response.status == 403) {
                var.update $error_category { value = "http_403_forbidden" }
              }
              elseif ($brevo_result.response.status == null) {
                var.update $error_category { value = "connection_error" }
              }
              else {
                var.update $error_category { value = "http_error" }
              }
            }
          }
          catch {
            var $normalized_error_message {
              value = $error.message|to_lower
            }
            conditional {
              if ($error.message != null && (($normalized_error_message|contains:"timeout") || ($normalized_error_message|contains:"timed out"))) {
                var.update $error_category { value = "timeout" }
              }
              else {
                var.update $error_category { value = "connection_error" }
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
