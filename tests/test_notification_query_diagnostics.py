"""Instrumentação estática temporária; não executa XanoScript ou chamadas HTTP."""

import hashlib
import re
import unittest
from pathlib import Path


XS = (Path(__file__).resolve().parents[1] / "xano/api/inventory_stock/purchase_requests_notifications_get.xs").read_text(encoding="utf-8")


def query_blocks():
    blocks = []
    for match in re.finditer(r"db\.query purchase_request_history \{", XS):
        cursor, depth = match.end(), 1
        while depth:
            if XS[cursor] == "{":
                depth += 1
            elif XS[cursor] == "}":
                depth -= 1
            cursor += 1
        end = XS.index("\n", cursor)
        blocks.append(XS[match.start():end].strip())
    return blocks


class NotificationQueryDiagnosticsTests(unittest.TestCase):
    def test_only_join_names_differ_from_the_pre_diagnostic_queries(self):
        # Mantém a proteção dos filtros/contratos; permite apenas os nomes corrigidos.
        expected = [
            "e51e6f0154e62f47af24cee52e49b2d760f6fc61f6472eff6d7f684490728e8b",
            "abc39482bf5de8bc174b1a296cbaa6194a4925df4944dab4cb195d13c564a169",
        ]
        blocks = [block.replace('purchase_request: {table:', 'request: {table:')
                  .replace('purchase_request_notification_read: {table:', 'read_state: {table:')
                  for block in query_blocks()]
        actual = [hashlib.sha256(re.sub(r"\s+", "", block).encode()).hexdigest()
                  for block in blocks]
        self.assertEqual(actual, expected)

    def test_every_database_reference_uses_a_declared_query_name(self):
        # Regressão estática: request/read_state deixavam os nomes usados sem vínculo.
        for block in query_blocks():
            joins = dict(re.findall(r'(\w+):\s*\{table:\s*"(\w+)"', block))
            self.assertEqual(joins, {
                "purchase_request": "purchase_request",
                "purchase_request_notification_read": "purchase_request_notification_read",
            })
            references = set(re.findall(r'\$db\.(\w+)\.', block))
            self.assertEqual(references - (set(joins) | {"purchase_request_history"}), set())

    def test_each_query_has_its_own_fail_closed_constant_identifier(self):
        for stage, output in (("LIST", "page"), ("COUNT", "unread_total")):
            block = XS.split(f"// BEGIN TEMP NOTIFICATIONS DIAG {stage}", 1)[1].split(f"// END TEMP NOTIFICATIONS DIAG {stage}", 1)[0]
            self.assertEqual(block.count("db.query purchase_request_history"), 1)
            self.assertIn(f"as ${output}", block)
            self.assertIn("try_catch", block)
            catch = block.split("\n      catch {", 1)[1]
            self.assertIn("precondition (false)", catch)
            self.assertIn('error_type = "standard"', catch)
            self.assertIn(f'error = "NOTIFICATIONS_DIAG_{stage}_QUERY_FAILED"', catch)
            self.assertNotIn("return", catch)
            self.assertNotIn("var.update", catch)

    def test_authorization_and_marker_remain_before_diagnostic_queries(self):
        first = XS.index("// BEGIN TEMP NOTIFICATIONS DIAG LIST")
        self.assertLess(XS.index('permission_code: "purchase_request.read"'), first)
        self.assertLess(XS.index('function.run "Inventory/purchase_request_notification_all_access"'), first)
        self.assertLess(XS.index('error = "NOTIFICATIONS_ACTIVATION_MARKER_CONVERSION_FAILED"'), first)
        self.assertLess(XS.index("// END TEMP NOTIFICATIONS DIAG LIST"), XS.index("// BEGIN TEMP NOTIFICATIONS DIAG COUNT"))

    def test_diagnostics_do_not_log_payloads_create_routes_or_perform_writes(self):
        self.assertEqual(XS.count('query "'), 1)
        for forbidden in ("debug.log", "$error", "api.request", "db.add", "db.edit", "db.del", "function.run \"Inventory/dispatch"):
            self.assertNotIn(forbidden, XS)
        self.assertNotIn("NOTIFICATIONS_DIAG_", XS.split("response =", 1)[1])
