"""Static safety checks for the one-off internal Brevo test function.

These tests do not execute XanoScript, call Brevo, or prove Request History
redaction. Running the function remains blocked until that redaction behavior
is verified in the Xano workspace.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "xano"
    / "function"
    / "inventory"
    / "test_brevo_transactional_email.xs"
)


class BrevoTransactionalEmailContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_is_internal_and_requires_explicit_confirmation(self):
        self.assertIn('function "Inventory/test_brevo_transactional_email"', self.source)
        self.assertRegex(self.source, r"(?m)^\s*bool confirm_send\s*$")
        self.assertIn("if ($input.confirm_send == true)", self.source)
        self.assertNotIn("api/", self.source.lower())

    def test_uses_exactly_one_brevo_send_request_and_fixed_test_content(self):
        self.assertEqual(self.source.count("api.request {"), 1)
        self.assertIn('url = "https://api.brevo.com/v3/smtp/email"', self.source)
        self.assertIn('method = "POST"', self.source)
        self.assertIn('"NexStock - Teste tecnico Xano Brevo"', self.source)
        self.assertNotIn("dispatch_purchase_request_email", self.source)

    def test_reads_only_the_four_approved_environment_variables(self):
        env_refs = set(re.findall(r"\$env\.([A-Z0-9_]+)", self.source))
        self.assertEqual(
            env_refs,
            {
                "BREVO_API_KEY",
                "BREVO_FROM_EMAIL",
                "BREVO_FROM_NAME",
                "BREVO_TEST_RECIPIENT",
            },
        )
        self.assertNotRegex(self.source, r"(?i)xkeysib-[a-z0-9-]{12,}")
        self.assertNotRegex(
            self.source,
            r"(?i)['\"][a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}['\"]",
        )

    def test_response_is_sanitized_and_has_no_message_or_payload(self):
        response = self.source.split("response = {", 1)[1].split("\n  }", 1)[0]
        self.assertEqual(
            re.findall(r"(?m)^\s*(\w+):", response),
            ["success", "http_status", "error_category"],
        )
        for forbidden in (
            "BREVO_API_KEY",
            "BREVO_TEST_RECIPIENT",
            ".headers",
            ".params",
            ".result",
            "messageId",
            "$error.message",
            "debug.log",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), response.lower())

    def test_transport_and_ambiguous_http_results_are_never_retried(self):
        for category in (
            "timeout_or_transport_indeterminate",
            "http_408_indeterminate",
            "http_5xx_indeterminate",
            "http_status_indeterminate",
            "http_401_unauthorized",
            "http_403_forbidden",
            "http_429_rejected",
            "http_4xx_rejected",
        ):
            with self.subTest(category=category):
                self.assertIn(f'"{category}"', self.source)
        self.assertNotRegex(self.source, r"(?i)\bwhile\s*\(")
        self.assertNotRegex(self.source, r"(?i)\b(?:retry|retries|sleep)\b")
        self.assertIn("timeout = 15", self.source)

    def test_has_no_database_dispatcher_or_scheduling_operations(self):
        forbidden = re.compile(
            r"\bdb\.(?:query|get|add|edit|del|transaction)\b|"
            r"\b(?:run\.job|task\.run)\b|"
            r"purchase_request|purchase_request_email_delivery|inventory_stock",
            re.IGNORECASE,
        )
        self.assertIsNone(forbidden.search(self.source))


if __name__ == "__main__":
    unittest.main()
