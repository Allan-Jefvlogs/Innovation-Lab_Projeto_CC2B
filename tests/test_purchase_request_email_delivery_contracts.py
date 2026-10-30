"""Static contract checks for the local Xano email outbox.

These tests do not execute XanoScript, access Xano, or call Resend. Runtime,
transaction and provider behavior still require isolated/live validation.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
XS = ROOT / "xano"


def read(relative: str) -> str:
    return (XS / relative).read_text(encoding="utf-8")


class PurchaseRequestEmailOutboxTests(unittest.TestCase):
    def test_delivery_table_separates_event_state_and_has_unique_keys(self):
        schema = read("table/purchase_request_email_delivery.xs")
        for field in (
            "purchase_request_id", "tipo_evento", "destinatario", "status",
            "provedor", "id_mensagem_provedor", "chave_idempotencia",
            "payload_snapshot", "tentativas", "data_ultima_tentativa",
            "data_confirmacao", "codigo_erro", "data_criacao", "data_atualizacao",
        ):
            with self.subTest(field=field):
                self.assertIn(field, schema)
        self.assertIn('"solicitacao", "cancelamento"', schema)
        self.assertIn('"aguardando_confirmacao_original"', schema)
        self.assertIn('"indeterminado"', schema)
        self.assertIn('{type: "btree|unique", field: [{name: "chave_idempotencia"}]}', schema)
        self.assertIn('{name: "purchase_request_id"}, {name: "tipo_evento"}', schema)
        self.assertIn("sensitive = true", schema)
        self.assertNotIn("RESEND_API_KEY", schema)

    def test_provider_resolver_accepts_only_explicit_config_and_never_returns_keys(self):
        resolver = read("function/inventory/resolve_purchase_request_email_provider.xs")
        self.assertIn("$env.NEXSTOCK_EMAIL_PROVIDER", resolver)
        self.assertIn("provedor_solicitado", resolver)
        self.assertIn("destinatario_solicitado", resolver)
        self.assertIn('$provider == "brevo"', resolver)
        self.assertIn('$provider == "resend"', resolver)
        self.assertIn("EMAIL_PROVIDER_INVALID", resolver)
        self.assertIn("EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE", resolver)
        self.assertIn("$input.provedor_solicitado", resolver)
        self.assertIn("value = $input.provedor_solicitado", resolver)
        self.assertIn("$input.destinatario_solicitado", resolver)
        self.assertIn("$env.BREVO_API_KEY", resolver)
        self.assertIn("$env.RESEND_API_KEY", resolver)
        self.assertIn("$env.RESEND_ALLOWED_TEST_RECIPIENT", resolver)
        self.assertIn("$input.destinatario_solicitado", resolver)
        self.assertNotIn("brevo_api_key:", resolver.lower())
        self.assertNotIn("resend_api_key:", resolver.lower())
        self.assertNotIn("debug.log", resolver.lower())

    def test_create_enqueues_only_for_non_null_recipient_inside_existing_transaction(self):
        post = read("api/inventory_stock/purchase_requests_post.xs")
        transaction = post.split("db.transaction {", 1)[1].split("\n            }\n          }", 1)[0]
        self.assertIn("db.add purchase_request {", transaction)
        self.assertIn("db.add purchase_request_history {", transaction)
        self.assertIn("$input.email_destinatario != null)", transaction)
        self.assertIn("db.add purchase_request_email_delivery {", transaction)
        self.assertIn('tipo_evento: "solicitacao"', transaction)
        self.assertIn('status: $initial_email_status', transaction)
        self.assertIn('function.run "Inventory/resolve_purchase_request_email_provider"', transaction)
        self.assertIn('destinatario_solicitado: $input.email_destinatario', transaction)
        self.assertIn('provedor: $email_provider_config.provedor', transaction)
        self.assertIn('codigo_erro: $email_failure_code', transaction)
        self.assertIn('""|uuid', transaction)
        self.assertEqual(post.count("db.add purchase_request_email_delivery {"), 1)
        self.assertNotIn('error = "EMAIL_PROVIDER_CONFIGURATION_INVALID"', post)
        self.assertNotIn("api.request", post)
        self.assertNotIn('function.run "Inventory/dispatch_purchase_request_email"', post)
        self.assertNotIn("db.add inventory_stock", post)
        self.assertNotIn("db.add inventory_movement", post)

    def test_legacy_request_without_email_does_not_create_outbox_row(self):
        post = read("api/inventory_stock/purchase_requests_post.xs")
        self.assertIn("$input.email_destinatario != null)", post)
        self.assertNotIn("email_destinatario: $input.email_destinatario,\n                                status", post)
        self.assertIn('var $initial_email_status { value = "pendente" }', post)
        self.assertIn("email_status: $initial_email_status", post)

    def test_idempotent_post_replay_cannot_enqueue_a_second_delivery(self):
        post = read("api/inventory_stock/purchase_requests_post.xs")
        self.assertEqual(post.count("db.add purchase_request_email_delivery {"), 1)
        self.assertEqual(post.split("db.add purchase_request_email_delivery {", 1)[1].split("}", 1)[0].count('tipo_evento: "solicitacao"'), 1)
        self.assertIn('value = "purchase-request-created/" ~ ($new_request.id|to_text)', post)
        self.assertIn('chave_idempotencia: $original_delivery_idempotency_key', post)
        table = read("table/purchase_request_email_delivery.xs")
        self.assertIn('{type: "btree|unique", field: [{name: "chave_idempotencia"}]}', table)
        self.assertIn('{name: "purchase_request_id"}, {name: "tipo_evento"}', table)

    def test_cancel_queues_notice_only_from_confirmed_original_delivery(self):
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        transaction = cancel.split("db.transaction {", 1)[1].split("\n          }\n        }", 1)[0]
        self.assertIn('evento: "cancelada"', transaction)
        self.assertIn('tipo_evento == "solicitacao"', transaction)
        self.assertIn('status == "enviado"', transaction)
        self.assertIn("id_mensagem_provedor != null", transaction)
        self.assertIn('value = "pendente"', transaction)
        self.assertIn('status: "aguardando_confirmacao_original"', transaction)
        self.assertIn('"purchase-request-cancelled/"', transaction)
        self.assertNotIn("email_destinatario:", transaction)
        self.assertNotIn("api.request", cancel)
        self.assertNotIn('function.run "Inventory/dispatch_purchase_request_email"', cancel)
        self.assertNotIn("db.edit inventory_stock", cancel)
        self.assertNotIn("db.add inventory_movement", cancel)

    def test_cancellation_waits_for_original_confirmation_and_never_sends_itself(self):
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        self.assertIn('original_email_delivery.status == "enviado"', cancel)
        self.assertIn('original_email_delivery.status == "pendente"', cancel)
        self.assertIn('original_email_delivery.status == "processando"', cancel)
        self.assertIn('original_email_delivery.status == "indeterminado"', cancel)
        self.assertIn('status: "aguardando_confirmacao_original"', cancel)
        self.assertNotIn('status == "falhou") {\n                        var $waiting_cancellation_payload', cancel)
        self.assertNotIn("api.request", cancel)

    def test_cancel_intents_inherit_original_provider_and_keep_race_states(self):
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        self.assertEqual(cancel.count('function.run "Inventory/resolve_purchase_request_email_provider"'), 1)
        self.assertIn('provedor_solicitado: $original_email_delivery.provedor', cancel)
        self.assertIn('destinatario_solicitado: $original_email_delivery.destinatario', cancel)
        self.assertIn("provedor: $original_email_delivery.provedor", cancel)
        self.assertEqual(cancel.count("\n                            provedor: $original_email_delivery.provedor"), 2)
        self.assertNotIn('error = "EMAIL_PROVIDER_CONFIGURATION_INVALID"', cancel)
        self.assertLess(cancel.index('function.run "Inventory/resolve_purchase_request_email_provider"'), cancel.index("db.edit purchase_request {"))
        self.assertIn('original_email_delivery.status == "processando"', cancel)
        self.assertIn('original_email_delivery.status == "indeterminado"', cancel)
        self.assertIn('status: "aguardando_confirmacao_original"', cancel)

    def test_invalid_provider_config_does_not_block_purchase_or_cancel_and_is_audited(self):
        post = read("api/inventory_stock/purchase_requests_post.xs")
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        self.assertIn('email_status: $initial_email_status', post)
        self.assertIn('notificacao_email_codigo: $email_failure_code', post)
        self.assertIn('value = "falhou"', post)
        self.assertIn('if ($input.email_destinatario != null && ($email_provider_config.provedor == "brevo" || $email_provider_config.provedor == "resend"))', post)
        self.assertIn('notificacao_cancelamento_estado: $cancel_notice_status', cancel)
        self.assertIn('notificacao_cancelamento_codigo: $cancel_notice_error', cancel)
        self.assertIn('status: $cancel_notice_status', cancel)
        self.assertIn('value = "nao_enviada"', cancel)
        self.assertIn('if ($original_email_delivery.provedor != "brevo" && $original_email_delivery.provedor != "resend")', cancel)

    def test_cancellation_snapshots_keep_original_sender_instead_of_current_selection(self):
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        self.assertEqual(cancel.count("\n                            remetente: $original_email_delivery.payload_snapshot.from"), 2)
        self.assertEqual(cancel.count("\n                            nome_remetente: $original_email_delivery.payload_snapshot.from_name"), 2)
        self.assertEqual(cancel.count("\n                            reply_to: $original_email_delivery.payload_snapshot.reply_to"), 2)
        self.assertNotIn("remetente: $email_provider_config.remetente", cancel)
        self.assertNotIn("nome_remetente: $email_provider_config.nome_remetente", cancel)

    def test_cancel_treats_pending_original_as_racy_and_waits_for_its_outcome(self):
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        transaction = cancel.split("db.transaction {", 1)[1].split("\n          }\n        }", 1)[0]
        self.assertIn('status == "pendente" || $original_email_delivery.status == "processando" || $original_email_delivery.status == "indeterminado"', transaction)
        self.assertIn("a worker may have read it before marking it", transaction)
        self.assertIn('status: "aguardando_confirmacao_original"', transaction)
        self.assertNotIn('status: "suprimido"', transaction)

    def test_dispatcher_suppresses_both_events_when_it_observes_cancelled_request_before_send(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        request_cancelled = worker.split('if ($request != null && $request.status == "cancelada")', 1)[1].split('elseif ($request != null', 1)[0]
        self.assertIn('status: "suprimido"', request_cancelled)
        self.assertIn('tipo_evento == "cancelamento"', request_cancelled)
        self.assertIn('status == "aguardando_confirmacao_original"', request_cancelled)
        self.assertIn('codigo_erro: "ORIGINAL_EMAIL_NOT_SENT"', request_cancelled)
        self.assertLess(worker.index('if ($request != null && $request.status == "cancelada")'), worker.index("api.request {"))

    def test_dispatcher_never_sends_legacy_or_unconfirmed_cancel_events(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        cancellation_branch = worker.split('elseif ($delivery.tipo_evento == "cancelamento" &&', 1)[1]
        self.assertIn('original_delivery.status == "enviado"', cancellation_branch)
        self.assertIn('original_delivery.status == "falhou"', cancellation_branch)
        self.assertIn('original_delivery.status == "suprimido"', cancellation_branch)
        self.assertIn('value = "aguardando_confirmacao_original"', cancellation_branch)
        self.assertIn('if ($delivery.tipo_evento == "solicitacao" && $delivery.status == "pendente")', worker)
        self.assertIn('delivery.status == "pendente" || $delivery.status == "aguardando_confirmacao_original"', worker)
        self.assertIn('$delivery.status == "processando"', worker.split("if ($delivery.status ==", 1)[1].split(") {", 1)[0])

    def test_resend_test_allowlist_is_scoped_only_to_resend_path(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        resend_branch = worker.split('if ($delivery.provedor == "resend")', 1)[1].split('elseif ($delivery.provedor == "brevo")', 1)[0]
        brevo_branch = worker.split('elseif ($delivery.provedor == "brevo")', 1)[1].split("else {", 1)[0]
        gate = resend_branch.split('if ($env.RESEND_API_KEY == null', 1)[1].split(") {", 1)[0]
        self.assertIn('$env.RESEND_FROM_EMAIL != "onboarding@resend.dev"', gate)
        self.assertIn('$delivery.payload_snapshot.from != "onboarding@resend.dev"', gate)
        self.assertIn('$env.RESEND_ALLOWED_TEST_RECIPIENT == null', gate)
        self.assertIn('$delivery.destinatario != $env.RESEND_ALLOWED_TEST_RECIPIENT', gate)
        self.assertIn('$delivery.payload_snapshot.to != $env.RESEND_ALLOWED_TEST_RECIPIENT', gate)
        self.assertIn('value = "configuracao_de_teste_incompleta"', resend_branch)
        self.assertIn('$env.BREVO_API_KEY', brevo_branch)
        self.assertNotIn("RESEND_ALLOWED_TEST_RECIPIENT", brevo_branch)
        self.assertNotIn("debug.log", worker.lower())

    def test_missing_or_unsafe_test_configuration_blocks_the_http_call(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        resend_branch = worker.split('if ($delivery.provedor == "resend")', 1)[1].split('elseif ($delivery.provedor == "brevo")', 1)[0]
        no_config = resend_branch.index('value = "configuracao_de_teste_incompleta"')
        request_call = worker.index("api.request {")
        self.assertLess(no_config, request_call)
        self.assertIn('$env.RESEND_API_KEY == null', worker)
        self.assertIn('$env.RESEND_ALLOWED_TEST_RECIPIENT == null', worker)
        self.assertIn('$env.RESEND_FROM_EMAIL != "onboarding@resend.dev"', worker)
        self.assertIn('status: "processando"', worker)
        self.assertIn('$provider_ready == false && $provider_configuration_error_code != null', worker)
        self.assertIn('status: "falhou"', worker)
        self.assertIn('EMAIL_PROVIDER_CONFIGURATION_INCOMPLETE', worker)

    def test_worker_stores_sender_in_stable_snapshot_before_external_call(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        request_call = worker.index("api.request {")
        self.assertNotIn("payload_snapshot: $send_payload", worker)
        self.assertLess(worker.index("NEXSTOCK_EMAIL_PROVIDER is deliberately not consulted"), request_call)
        self.assertLess(worker.index('if ($delivery.provedor == "resend")'), request_call)
        self.assertLess(worker.index('elseif ($delivery.provedor == "brevo")'), request_call)
        self.assertIn("params = $send_payload", worker)
        self.assertIn('"Idempotency-Key: " ~ $delivery.chave_idempotencia', worker)
        self.assertIn('headers: {IdempotencyKey: $delivery.chave_idempotencia}', worker)
        self.assertIn("payload_snapshot.reply_to", worker)

    def test_internal_dispatcher_uses_backend_secrets_and_provider_idempotency(self):
        worker = read("function/inventory/dispatch_purchase_request_email.xs")
        self.assertIn('var.update $provider_url { value = "https://api.resend.com/emails" }', worker)
        self.assertIn('var.update $provider_url { value = "https://api.brevo.com/v3/smtp/email" }', worker)
        self.assertIn("url = $provider_url", worker)
        self.assertIn('"Authorization: Bearer " ~ $env.RESEND_API_KEY', worker)
        self.assertIn('"api-key: " ~ $env.BREVO_API_KEY', worker)
        self.assertIn('$env.RESEND_FROM_EMAIL', worker)
        self.assertIn('$env.BREVO_FROM_EMAIL', worker)
        self.assertIn('$env.BREVO_FROM_NAME', worker)
        self.assertNotIn('$env.NEXSTOCK_EMAIL_PROVIDER', worker)
        self.assertIn('$env.RESEND_ALLOWED_TEST_RECIPIENT', worker)
        self.assertIn('"Idempotency-Key: " ~ $delivery.chave_idempotencia', worker)
        self.assertIn("payload_snapshot.subject", worker)
        self.assertIn("payload_snapshot.text", worker)
        self.assertIn("textContent: $delivery.payload_snapshot.text", worker)
        self.assertIn("htmlContent: $delivery.payload_snapshot.html", worker)
        self.assertIn("result.messageId", worker)
        self.assertIn('"duplicate_parameter"', worker)
        self.assertIn('status: "processando"', worker)
        self.assertIn('value = "indeterminado"', read("function/inventory/classify_purchase_request_email_response.xs"))
        self.assertNotIn("debug.log", worker.lower())
        self.assertNotIn("$api_result.response.result|json_encode", worker)
        self.assertNotIn("while (", worker)
        self.assertIn('value = "configuracao_de_teste_incompleta"', worker)
        self.assertNotIn("email_status: $classification.status", worker.split('tipo_evento == "solicitacao"', 1)[0])
        self.assertIn('if ($delivery.tipo_evento == "solicitacao" && ($resolved_status == "enviado" || $resolved_status == "falhou"))', worker)

    def test_response_classifier_has_mockable_success_failure_and_ambiguous_cases(self):
        classifier = read("function/inventory/classify_purchase_request_email_response.xs")
        for case in (
            "provider success requires message id",
            "provider rejection is a definite failure",
            "rate limit is a definite rejection and is not retried here",
            "provider timeout remains indeterminate",
            "provider server error remains indeterminate",
            "concurrent idempotent request remains indeterminate",
            "success without provider message id remains indeterminate",
        ):
            with self.subTest(case=case):
                self.assertIn(f'test "{case}"', classifier)

    def test_portuguese_templates_are_plain_text_and_omit_cancellation_reason(self):
        builder = read("function/inventory/build_purchase_request_email_payload.xs")
        self.assertIn("Solicitação de compra #", builder)
        self.assertIn("foi registrada no NexStock", builder)
        self.assertIn("não a compra ou o recebimento", builder)
        self.assertIn("Cancelamento da solicitação #", builder)
        self.assertIn("desconsidere a mensagem anterior", builder)
        self.assertNotIn("justificativa", builder.lower())
        self.assertIn("html: $html_body", builder)
        self.assertIn('$body|replace:"&":"&amp;"|replace:"<":"&lt;"|replace:">":"&gt;"', builder)

    def test_provider_sender_and_optional_reply_to_are_frozen_with_both_event_snapshots(self):
        builder = read("function/inventory/build_purchase_request_email_payload.xs")
        post = read("api/inventory_stock/purchase_requests_post.xs")
        cancel = read("api/inventory_stock/purchase_requests_by_id_cancel_patch.xs")
        self.assertIn("text? remetente?", builder)
        self.assertIn("text? nome_remetente?", builder)
        self.assertIn("email? reply_to?", builder)
        self.assertIn("from: $input.remetente", builder)
        self.assertIn("from_name: $input.nome_remetente", builder)
        self.assertIn("reply_to: $input.reply_to", builder)
        self.assertIn("remetente: $email_provider_config.remetente", post)
        self.assertIn("reply_to: $email_provider_config.reply_to", post)
        self.assertEqual(cancel.count("\n                            remetente: $original_email_delivery.payload_snapshot.from"), 2)
        self.assertEqual(cancel.count("\n                            reply_to: $original_email_delivery.payload_snapshot.reply_to"), 2)
        self.assertIn("payload_snapshot: $email_payload_snapshot", post)
        self.assertIn("payload_snapshot: $cancellation_payload_snapshot", cancel)
        self.assertIn("payload_snapshot: $waiting_cancellation_payload", cancel)

    def test_no_backend_email_secret_or_provider_url_is_added_to_reflex(self):
        replenishment = (ROOT / "Meu_projeto/pages/reposicao.py").read_text(encoding="utf-8")
        self.assertNotIn("RESEND_API_KEY", replenishment)
        self.assertNotIn("BREVO_API_KEY", replenishment)
        self.assertNotIn("NEXSTOCK_EMAIL_PROVIDER", replenishment)
        self.assertNotIn("api.resend.com", replenishment)
        self.assertNotIn("api.brevo.com", replenishment)


if __name__ == "__main__":
    unittest.main()
