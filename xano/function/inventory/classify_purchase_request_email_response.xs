function "Inventory/classify_purchase_request_email_response" {
  description = "Classifica respostas normalizadas do provedor sem expor corpo ou dados sensíveis."
  input {
    bool transport_failed
    int http_status?
    text provider_message_id?
    bool duplicate_request?=false
  }
  stack {
    var $status {
      value = "indeterminado"
    }
    var $error_code {
      value = "EMAIL_RESPONSE_AMBIGUOUS"
    }

    conditional {
      if ($input.transport_failed == true) {
        var.update $status { value = "indeterminado" }
        var.update $error_code { value = "EMAIL_TRANSPORT_AMBIGUOUS" }
      }
      elseif ($input.http_status >= 200 && $input.http_status < 300 && $input.provider_message_id != null && $input.provider_message_id != "") {
        var.update $status { value = "enviado" }
        var.update $error_code { value = null }
      }
      elseif ($input.duplicate_request == true || $input.http_status == 409 || $input.http_status >= 500 || ($input.http_status >= 200 && $input.http_status < 300)) {
        var.update $status { value = "indeterminado" }
        var.update $error_code { value = "EMAIL_RESPONSE_AMBIGUOUS" }
      }
      else {
        var.update $status { value = "falhou" }
        var.update $error_code { value = "EMAIL_REJECTED_HTTP_" ~ ($input.http_status|to_text) }
      }
    }
  }
  response = {
    status: $status,
    codigo_erro: $error_code
  }

  test "provider success requires message id" {
    input = {transport_failed: false, http_status: 200, provider_message_id: "resend-message-id"}
    expect.to_equal ($response.status) { value = "enviado" }
    expect.to_be_null ($response.codigo_erro)
  }

  test "provider rejection is a definite failure" {
    input = {transport_failed: false, http_status: 422, provider_message_id: null}
    expect.to_equal ($response.status) { value = "falhou" }
    expect.to_equal ($response.codigo_erro) { value = "EMAIL_REJECTED_HTTP_422" }
  }

  test "rate limit is a definite rejection and is not retried here" {
    input = {transport_failed: false, http_status: 429, provider_message_id: null}
    expect.to_equal ($response.status) { value = "falhou" }
    expect.to_equal ($response.codigo_erro) { value = "EMAIL_REJECTED_HTTP_429" }
  }

  test "provider timeout remains indeterminate" {
    input = {transport_failed: true, http_status: null, provider_message_id: null}
    expect.to_equal ($response.status) { value = "indeterminado" }
    expect.to_equal ($response.codigo_erro) { value = "EMAIL_TRANSPORT_AMBIGUOUS" }
  }

  test "provider server error remains indeterminate" {
    input = {transport_failed: false, http_status: 503, provider_message_id: null}
    expect.to_equal ($response.status) { value = "indeterminado" }
  }

  test "concurrent idempotent request remains indeterminate" {
    input = {transport_failed: false, http_status: 409, provider_message_id: null}
    expect.to_equal ($response.status) { value = "indeterminado" }
  }

  test "success without provider message id remains indeterminate" {
    input = {transport_failed: false, http_status: 200, provider_message_id: null}
    expect.to_equal ($response.status) { value = "indeterminado" }
  }

  test "Brevo success uses normalized message id" {
    input = {transport_failed: false, http_status: 201, provider_message_id: "brevo-message-id"}
    expect.to_equal ($response.status) { value = "enviado" }
    expect.to_be_null ($response.codigo_erro)
  }

  test "Brevo idempotency duplicate remains ambiguous" {
    input = {transport_failed: false, http_status: 400, provider_message_id: null, duplicate_request: true}
    expect.to_equal ($response.status) { value = "indeterminado" }
    expect.to_equal ($response.codigo_erro) { value = "EMAIL_RESPONSE_AMBIGUOUS" }
  }
}
