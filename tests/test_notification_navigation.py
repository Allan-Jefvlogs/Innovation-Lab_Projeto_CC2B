"""Notification navigation and read confirmation with mocked Xano operations."""

import unittest
from unittest.mock import AsyncMock, patch

from Meu_projeto.components.layout import _notification_item
from Meu_projeto.services.session_read_cache import session_read_cache
from Meu_projeto.services.xano_client import XanoAuthError, XanoConnectionError, XanoServerError, auth_client
from Meu_projeto.state.dashboard_notifications import DashboardNotificationsState
from tests.test_dashboard_periods_notifications import auth, drain, notification, state


async def events(generator):
    return [event async for event in generator if event is not None]


def redirect_paths(output):
    return [str(value) for event in output if hasattr(event, "args")
            for key, value in event.args if str(key) == "path"]


class NotificationNavigationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()
        self.obj = state(DashboardNotificationsState)
        self.obj.enabled = self.obj.panel_open = True

    def tearDown(self):
        session_read_cache.clear()

    async def prime(self, *, read=False, manage=True, event="status_alterado", status="em_analise"):
        data = notification()
        data["items"][0].update(purchase_request_id=12, lida=read, evento=event, status_novo=status)
        data["unreadTotal"] = 0 if read else 1
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth(manage=manage))), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=data)):
            await drain(self.obj.load_page())

    async def test_unread_click_marks_once_and_navigates_only_after_confirmation(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 8, "lida": True})) as mark:
            click = self.obj.open_notification(8)
            await anext(click)
            self.assertFalse(self.obj.items[0]["lida"])
            self.assertEqual(self.obj.unread_count, 1)
            self.assertEqual(await events(self.obj.open_notification(8)), [])
            result = await events(click)
            self.assertEqual(redirect_paths(result), ['"/compras/12"'])
            self.assertTrue(self.obj.items[0]["lida"])
            self.assertEqual(self.obj.unread_count, 0)
            self.assertFalse(self.obj.panel_open)
            # Duplicate events still queued after completion must not repeat work.
            self.assertEqual(await events(self.obj.open_notification(8)), [])
        mark.assert_awaited_once_with("local-session", 8)

    async def test_read_notification_only_navigates(self):
        await self.prime(read=True)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock()) as mark:
            result = await events(self.obj.open_notification(8))
        mark.assert_not_awaited()
        self.assertEqual(redirect_paths(result), ['"/compras/12"'])

    async def test_failed_or_ambiguous_read_still_navigates_without_decrement_or_retry(self):
        for error in (XanoServerError("controlled failure", status_code=500), XanoConnectionError("controlled timeout")):
            session_read_cache.clear()
            self.obj = state(DashboardNotificationsState)
            self.obj.enabled = self.obj.panel_open = True
            await self.prime()
            with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
                 patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(side_effect=error)) as mark:
                result = await events(self.obj.open_notification(8))
                await drain(self.obj.open_notification(8))
                await drain(self.obj.mark_read(8))
            self.assertEqual(redirect_paths(result), ['"/compras/12"'])
            self.assertFalse(self.obj.items[0]["lida"])
            self.assertEqual(self.obj.unread_count, 1)
            mark.assert_awaited_once()

    async def test_separate_read_action_does_not_navigate(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 8, "lida": True})) as mark:
            self.assertEqual(redirect_paths(await events(self.obj.mark_read(8))), [])
        mark.assert_awaited_once()

    async def test_read_only_user_marks_own_notification_then_navigates(self):
        await self.prime(manage=False)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth(manage=False))), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 8, "lida": True})) as mark:
            result = await events(self.obj.open_notification(8))
        self.assertEqual(redirect_paths(result), ['"/compras/12"'])
        mark.assert_awaited_once_with("local-session", 8)
        self.assertTrue(self.obj.items[0]["lida"])
        self.assertEqual(self.obj.unread_count, 0)

    async def test_unknown_event_or_other_session_does_not_mark_or_redirect(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock()) as mark:
            self.assertEqual(await events(self.obj.open_notification(999)), [])
        mark.assert_not_awaited()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth("other-session"))), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock()) as mark:
            self.assertEqual(await events(self.obj.open_notification(8)), [])
        mark.assert_not_awaited()

    async def test_closed_or_completed_requests_are_not_filtered_by_notification_action(self):
        for event, status in (("cancelada", "cancelada"), ("recebimento_registrado", "concluida")):
            session_read_cache.clear()
            self.obj = state(DashboardNotificationsState)
            self.obj.enabled = self.obj.panel_open = True
            await self.prime(read=True, event=event, status=status)
            with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())):
                self.assertEqual(redirect_paths(await events(self.obj.open_notification(8))), ['"/compras/12"'])

    async def test_expired_session_does_not_redirect_to_detail_after_read_401(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(side_effect=XanoAuthError("expired", status_code=401))):
            output = await events(self.obj.open_notification(8))
        self.assertEqual(redirect_paths(output), [])
        self.assertFalse(self.obj.items[0]["lida"])

    async def test_reopening_panel_releases_navigation_latch(self):
        await self.prime(read=True)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())):
            await drain(self.obj.open_notification(8))
            self.obj.set_panel_open(True)
            self.assertEqual(redirect_paths(await events(self.obj.open_notification(8))), ['"/compras/12"'])

    async def test_session_change_during_read_does_not_navigate_with_old_notification(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(side_effect=[auth(), auth(), auth("other-session"), auth("other-session")])), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 8, "lida": True})) as mark:
            result = await events(self.obj.open_notification(8))
        mark.assert_awaited_once()
        self.assertEqual(redirect_paths(result), [])
        self.assertEqual(self.obj.items, [])
        self.assertIsNone(self.obj.unread_count)

    async def test_existing_read_cooldown_allows_navigation_without_sending_patch(self):
        await self.prime()
        self.obj.retry_after_epoch = float("inf")
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock()) as mark:
            result = await events(self.obj.open_notification(8))
        mark.assert_not_awaited()
        self.assertEqual(redirect_paths(result), ['"/compras/12"'])
        self.assertFalse(self.obj.items[0]["lida"])

    def test_keyboard_button_and_read_action_are_siblings_and_stop_bubbling(self):
        item = {"history_id": 8, "purchase_request_id": 12, "descricao": "Evento", "data_formatada": "01/01/2026", "lida": False}
        component = _notification_item(item)
        primary = component.children[0]
        self.assertEqual(primary.tag, "Button")
        self.assertTrue(primary.event_triggers["on_click"].events[0].event_actions["stopPropagation"])
        rendered = str(component)
        self.assertIn("Marcar como lida", rendered)
        self.assertIn("open_notification", rendered)
        self.assertIn("mark_read", rendered)
        self.assertGreaterEqual(rendered.count('stopPropagation'), 2)
