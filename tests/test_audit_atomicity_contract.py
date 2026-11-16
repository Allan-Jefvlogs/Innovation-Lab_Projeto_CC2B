"""Structural checks for atomic audit writes in the current Xano endpoints.

These checks do not execute Xano or prove database rollback at runtime.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCOPED_ENDPOINTS = (
    "xano/api/inventory_catalog/categories_by_id_activate_patch.xs",
    "xano/api/inventory_catalog/categories_by_id_inactivate_patch.xs",
    "xano/api/inventory_catalog/categories_by_id_patch.xs",
    "xano/api/inventory_catalog/categories_post.xs",
    "xano/api/inventory_catalog/permissions_profiles_profile_code_patch.xs",
    "xano/api/inventory_catalog/products_by_id_activate_patch.xs",
    "xano/api/inventory_catalog/products_by_id_inactivate_patch.xs",
    "xano/api/inventory_catalog/products_by_id_patch.xs",
    "xano/api/inventory_catalog/products_post.xs",
    "xano/api/inventory_catalog/suppliers_by_id_inactivate_patch.xs",
    "xano/api/inventory_catalog/suppliers_by_id_patch.xs",
    "xano/api/inventory_catalog/suppliers_post.xs",
    "xano/api/inventory_catalog/users_by_id_activate_patch.xs",
    "xano/api/inventory_catalog/users_by_id_inactivate_patch.xs",
    "xano/api/inventory_catalog/users_by_id_patch.xs",
    "xano/api/inventory_catalog/users_by_id_profile_patch.xs",
    "xano/api/inventory_catalog/users_by_id_reset_password_patch.xs",
    "xano/api/inventory_catalog/users_post.xs",
)


def block_after(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    for index in range(opening, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"Unclosed block after {marker!r}")


class AuditAtomicityContractTests(unittest.TestCase):
    def test_scoped_mutations_write_audit_inline_in_the_same_transaction(self):
        for relative_path in SCOPED_ENDPOINTS:
            with self.subTest(endpoint=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                transaction = block_after(source, "db.transaction")

                self.assertEqual(transaction.count("db.add inventory_audit_log"), 1)
                self.assertIn('db.get "user" {', transaction)
                self.assertIn('output = ["id", "name"]', transaction)
                self.assertIn('precondition ($audit_actor != null)', transaction)
                self.assertNotIn('function.run "Inventory/record_audit_event"', source)

                writes = list(
                    re.finditer(r"(?m)^\s*db\.(?:add|edit|patch|del|bulk\.(?:add|update|patch|delete))\b", source)
                )
                self.assertTrue(writes, "expected a business or audit database write")
                for write in writes:
                    self.assertIn(
                        write.group(0).strip(),
                        transaction,
                        f"write outside transaction: {write.group(0).strip()}",
                    )

                audit_position = transaction.index("db.add inventory_audit_log")
                business_writes = [
                    match.start()
                    for match in re.finditer(
                        r"(?m)^\s*db\.(?:add|edit|patch|del|bulk\.(?:add|update|patch|delete))\b",
                        transaction,
                    )
                    if not transaction[match.start() :].lstrip().startswith(
                        "db.add inventory_audit_log"
                    )
                ]
                self.assertTrue(business_writes, "expected a business write before audit")
                self.assertLess(max(business_writes), audit_position)

    def test_stock_entry_and_exit_keep_balance_and_movement_without_audit(self):
        for relative_path in (
            "xano/api/inventory_stock/entries_post.xs",
            "xano/api/inventory_stock/exits_post.xs",
        ):
            with self.subTest(endpoint=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                transaction = block_after(source, "db.transaction")
                self.assertIn("db.edit inventory_stock", transaction)
                self.assertIn("db.add inventory_movement", transaction)
                self.assertNotIn("db.add inventory_audit_log", transaction)
                self.assertNotIn("db.add inventory_audit_log", source)
                self.assertLess(
                    transaction.index("db.edit inventory_stock"),
                    transaction.index("db.add inventory_movement"),
                )

    def test_product_creation_keeps_product_stock_and_audit_together(self):
        source = (ROOT / "xano/api/inventory_catalog/products_post.xs").read_text(
            encoding="utf-8"
        )
        transaction = block_after(source, "db.transaction")
        self.assertIn("db.add product", transaction)
        self.assertIn("db.add inventory_stock", transaction)
        self.assertIn("db.add inventory_audit_log", transaction)


if __name__ == "__main__":
    unittest.main()
