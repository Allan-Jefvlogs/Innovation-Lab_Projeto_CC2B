"""Static security contract checks for the internal Brevo connectivity probe.

These checks do not call Brevo or execute XanoScript. Remote connectivity,
runtime exception wording, and Xano egress IP behavior remain unverified.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "xano" / "function" / "inventory" / "diagnose_brevo_connectivity.xs"


class BrevoConnectivityDiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_is_internal_no_input_function(self):
        self.assertIn('function "Inventory/diagnose_brevo_connectivity"', self.source)
        self.assertRegex(self.source, r"(?m)^\s*input\s*\{\s*\}")
        self.assertNotIn("api/", self.source.lower())

    def test_performs_only_the_required_read_only_get(self):
        self.assertEqual(self.source.count("api.request {"), 1)
        self.assertIn(
            'url = "https://api.brevo.com/v3/smtp/statistics/aggregatedReport?days=1"',
            self.source,
        )
        self.assertIn('method = "GET"', self.source)
        self.assertNotRegex(self.source, r"(?m)^\s*params\s*=")
        self.assertNotRegex(self.source, r"(?m)^\s*db\.")
        self.assertNotIn("dispatch_purchase_request_email", self.source)

    def test_secret_is_read_only_from_xano_environment(self):
        self.assertIn("$env.BREVO_API_KEY", self.source)
        self.assertNotIn("debug.log", self.source.lower())
        self.assertNotRegex(self.source, r"(?i)(api[_-]?key\s*[:=]\s*)['\"][^$\"]{8,}")

    def test_result_is_sanitized_and_excludes_response_details(self):
        response = self.source.split("response = {", 1)[1].split("\n  }", 1)[0]
        for field in ("success:", "http_status:", "error_category:"):
            with self.subTest(field=field):
                self.assertIn(field, response)
        for forbidden in ("BREVO_API_KEY", ".headers", ".result", "$error.message"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, response)
        self.assertNotIn("$brevo_result.response.result", self.source)
        self.assertNotIn("$brevo_result.response.headers", self.source)

    def test_http_and_transport_failures_are_distinguished(self):
        for category in (
            "configuration_missing",
            "http_401_unauthorized",
            "http_403_forbidden",
            "http_error",
            "timeout",
            "connection_error",
        ):
            with self.subTest(category=category):
                self.assertIn(f'"{category}"', self.source)
        self.assertIn("$brevo_result.response.status == 401", self.source)
        self.assertIn("$brevo_result.response.status == 403", self.source)
        self.assertIn("$normalized_error_message|contains:\"timeout\"", self.source)
        self.assertIn("$normalized_error_message|contains:\"timed out\"", self.source)

    def test_function_contains_no_mutating_or_scheduling_operations(self):
        forbidden = re.compile(
            r"\b(?:POST|PATCH|PUT|DELETE)\b|\bdb\.(?:add|edit|del|transaction)\b|"
            r"\brun\.job\b|\btask\.run\b",
            re.IGNORECASE,
        )
        self.assertIsNone(forbidden.search(self.source))
        self.assertNotIn("purchase_request_email_delivery", self.source)
        self.assertNotIn("purchase_request_history", self.source)
        self.assertNotIn("inventory_stock", self.source)


if __name__ == "__main__":
    unittest.main()
