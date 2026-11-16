"""Contrato e estrutura locais; não executa consultas no Xano."""

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from Meu_projeto.services.xano_client import XanoAuthClient, XanoServerError


XS = (Path(__file__).resolve().parents[1] / "xano/api/inventory_stock/purchase_requests_notifications_get.xs").read_text(encoding="utf-8")


class NotificationReadProjectionTests(unittest.IsolatedAsyncioTestCase):
    def test_join_projects_nullable_receipt_id_not_database_boolean_expression(self):
        query = XS.split("} as $page", 1)[0]
        self.assertIn("read_receipt_id: $db.purchase_request_notification_read.id", query)
        self.assertIn('"items.read_receipt_id"', query)
        self.assertNotIn("lida: $db.", query)
        self.assertNotIn("$db.purchase_request_notification_read.id != null", query)
        self.assertIn("lida: ($notification.read_receipt_id !== null)", XS)
        self.assertIn("foreach ($page.items)", XS)
        self.assertIn("array.push $notification_items", XS)
        self.assertNotIn("$page.items|map:", XS)
        self.assertNotIn("read_receipt_id", XS.split("response =", 1)[1])

    def test_user_scoping_count_marker_and_pagination_are_preserved(self):
        self.assertEqual(XS.count("purchase_request_notification_read.user_id == $auth.id"), 2)
        self.assertEqual(XS.count("purchase_request_notification_read.history_id == $db.purchase_request_history.id"), 2)
        self.assertEqual(XS.count("$scope.all_access || $db.purchase_request.solicitante_usuario_id == $auth.id"), 2)
        self.assertIn("$db.purchase_request_notification_read.id == null", XS)
        self.assertIn('return = {type: "count"}', XS)
        self.assertEqual(XS.count("data_evento >= $activation_at"), 2)
        self.assertIn('totals: true', XS)
        for field in ("curPage", "perPage", "itemsTotal"):
            self.assertIn(f"{field}: $page.{field}", XS)
        self.assertIn("unreadTotal: $unread_total", XS)
        self.assertNotIn("db.add", XS)
        self.assertNotIn("db.edit", XS)

    def test_native_history_fields_are_not_redeclared_as_evals(self):
        eval_block = XS.split("eval = {", 1)[1].split("}", 1)[0]
        for key in ("purchase_request_id", "evento", "data_evento", "history_id"):
            self.assertNotIn(f"{key}:", eval_block)
        for key in ("id", "purchase_request_id", "evento", "data_evento"):
            self.assertIn(f'"items.{key}"', XS)
        self.assertIn("history_id: $notification.id", XS)
        self.assertIn("purchase_request_id: $notification.purchase_request_id", XS)
        # A referência entre colunas continua apenas nos dois joins, sem coerção de IDs.
        self.assertEqual(XS.count("$db.purchase_request_history.purchase_request_id"), 2)
        self.assertEqual(XS.count("$db.purchase_request_history.purchase_request_id == $db.purchase_request.id"), 2)
        self.assertNotIn("|to_int", XS.split("db.query purchase_request_history", 1)[1])

    async def test_client_accepts_boolean_read_and_unread_preserving_pagination(self):
        client = XanoAuthClient()
        for read in (False, True):
            payload = {"items": [{"history_id": 1, "purchase_request_id": 2,
                                  "evento": "criada", "descricao": "Solicitação criada",
                                  "data_evento": 1000, "lida": read}],
                       "curPage": 2, "perPage": 10, "itemsTotal": 11,
                       "unreadTotal": 0 if read else 1}
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)) as get:
                self.assertEqual(await client.get_purchase_request_notifications("local-test-token", page=2), payload)
            get.assert_awaited_once()

    async def test_client_rejects_non_boolean_read_state(self):
        client = XanoAuthClient()
        for read in (None, 0, 1, "false", "true"):
            payload = {"items": [{"history_id": 1, "purchase_request_id": 2,
                                  "evento": "criada", "descricao": "Solicitação criada",
                                  "data_evento": 1000, "lida": read}],
                       "curPage": 1, "perPage": 10, "itemsTotal": 1, "unreadTotal": 1}
            with patch.object(client, "_inventory_request", new=AsyncMock(return_value=payload)):
                with self.assertRaises(XanoServerError):
                    await client.get_purchase_request_notifications("local-test-token")
