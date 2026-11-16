"""Local state and rendered component checks; all Xano calls are mocked."""

import copy
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from Meu_projeto.components.layout import _topbar
from Meu_projeto.services.session_read_cache import session_read_cache
from Meu_projeto.services.xano_client import XanoRateLimitError, XanoServerError, auth_client
from Meu_projeto.state.dashboard_notifications import DashboardNotificationsState
from tests.test_dashboard_periods_notifications import auth, drain, notification, state


def page(number, ids, total=30, unread=20):
    base = notification()["items"][0]
    return {"items": [{**base, "history_id": i} for i in ids],
            "curPage": number, "perPage": 10, "itemsTotal": total, "unreadTotal": unread}


class IncrementalNotificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        session_read_cache.clear()
        self.obj = state(DashboardNotificationsState)
        self.obj.enabled = True
        self.obj.panel_open = True

    def tearDown(self):
        session_read_cache.clear()

    async def prime(self, data=None):
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=data or page(1, range(30, 20, -1)))):
            await drain(self.obj.load_page())

    async def test_empty_and_small_lists_do_not_request_another_page(self):
        for ids in ([], [4, 3]):
            session_read_cache.clear()
            self.obj = state(DashboardNotificationsState)
            self.obj.enabled = self.obj.panel_open = True
            await self.prime(page(1, ids, total=len(ids), unread=len(ids)))
            with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
                 patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock()) as get:
                await drain(self.obj.on_list_scroll({"near_end": True, "page": 1}))
            get.assert_not_awaited()
            self.assertEqual(len(self.obj.items), len(ids))
            self.assertFalse(self.obj.has_next)

    async def test_scroll_appends_pages_preserving_order_and_removing_overlap(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=[page(2, [21, 20, 19]), page(3, [19, 18], unread=17)])) as get:
            await drain(self.obj.on_list_scroll({"near_end": False, "page": 1}))
            get.assert_not_awaited()
            await drain(self.obj.on_list_scroll({"near_end": True, "page": 1}))
            # A delayed duplicate event for page 1 must not fetch page 3.
            await drain(self.obj.on_list_scroll({"near_end": True, "page": 1}))
            self.assertEqual(get.await_count, 1)
            await drain(self.obj.on_list_scroll({"near_end": True, "page": 2}))
        self.assertEqual([item["history_id"] for item in self.obj.items], list(range(30, 17, -1)))
        self.assertEqual(self.obj.page, 3)
        self.assertFalse(self.obj.has_next)
        self.assertEqual(self.obj.unread_count, 17)
        self.assertEqual([call.kwargs["page"] for call in get.await_args_list], [2, 3])

    async def test_closed_panel_and_invalid_scroll_values_do_not_fetch(self):
        await self.prime()
        self.obj.set_panel_open(False)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock()) as get:
            for position in ({"near_end": True, "page": 1}, {}, {"near_end": True, "page": True}):
                await drain(self.obj.on_list_scroll(position))
        get.assert_not_awaited()

    async def test_loading_guard_blocks_simultaneous_incremental_events(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=page(2, [20]))) as get:
            first = self.obj.load_more(1)
            await anext(first)  # loading=true has been emitted before starting HTTP.
            await drain(self.obj.load_more(1))
            self.assertTrue(self.obj.loading)
            await drain(first)
        get.assert_awaited_once()

    async def test_incremental_failure_preserves_list_page_and_manual_retry_target(self):
        await self.prime()
        old_items = copy.deepcopy(self.obj.items)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=XanoServerError("controlled", status_code=500))) as get:
            await drain(self.obj.load_more(1))
            await drain(self.obj.on_list_scroll({"near_end": True, "page": 1}))
            self.assertEqual(self.obj.items, old_items)
            self.assertEqual(self.obj.page, 1)
            self.assertTrue(self.obj.error)
            self.assertIsNotNone(self.obj.reload())
        get.assert_awaited_once()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=page(2, [20]))) as retry:
            await drain(self.obj.load_more(1))
        self.assertEqual(retry.await_args.kwargs["page"], 2)
        self.assertEqual(self.obj.page, 2)
        self.assertEqual(len(self.obj.items), len(old_items) + 1)

    async def test_rate_limit_stops_scroll_until_explicit_retry_after_cooldown(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=XanoRateLimitError(20))) as get:
            await drain(self.obj.load_more(1))
            await drain(self.obj.load_more(1))
            self.assertIsNone(self.obj.reload())
        get.assert_awaited_once()
        self.assertEqual(self.obj.page, 1)
        self.assertEqual(len(self.obj.items), 10)

    async def test_wrong_page_does_not_replace_existing_items_or_advance_cursor(self):
        await self.prime()
        before = copy.deepcopy(self.obj.items)
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=page(1, [20]))):
            await drain(self.obj.load_more(1))
        self.assertEqual(self.obj.page, 1)
        self.assertEqual(self.obj.items, before)
        self.assertTrue(self.obj.error)

    async def test_mark_read_does_not_automatically_retry_a_failed_incremental_page(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(side_effect=XanoServerError("controlled", status_code=500))) as get, \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 30, "lida": True})):
            await drain(self.obj.load_more(1))
            await drain(self.obj.mark_read(30))
            self.assertTrue(self.obj.error)
            self.assertTrue(self.obj.items[0]["lida"])
            await drain(self.obj.on_list_scroll({"near_end": True, "page": 1}))
        get.assert_awaited_once()

    async def test_scope_change_during_append_discards_private_items(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(side_effect=[auth(), auth("other-session")])), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=page(2, [20]))):
            await drain(self.obj.load_more(1))
        self.assertEqual(self.obj.items, [])
        self.assertIsNone(self.obj.unread_count)
        self.assertEqual(self.obj.owner_user_id, 0)

    async def test_mark_read_updates_appended_item_only_after_confirmation(self):
        await self.prime()
        with patch.object(DashboardNotificationsState, "get_state", new=AsyncMock(return_value=auth())), \
             patch.object(auth_client, "get_purchase_request_notifications", new=AsyncMock(return_value=page(2, [20], unread=2))), \
             patch.object(auth_client, "mark_purchase_request_notification_read", new=AsyncMock(return_value={"history_id": 20, "lida": True})) as mark:
            await drain(self.obj.load_more(1))
            pending = self.obj.mark_read(20)
            await anext(pending)
            self.assertFalse(self.obj.items[-1]["lida"])
            self.assertEqual(self.obj.unread_count, 2)
            await drain(pending)
            self.assertTrue(self.obj.items[-1]["lida"])
            self.assertEqual(self.obj.unread_count, 1)
        mark.assert_awaited_once()

    def test_counter_caps_display_only_at_nine_plus(self):
        for value, label in ((0, "0"), (1, "1"), (2, "2"), (9, "9"), (10, "9+"), (37, "9+")):
            obj = state(DashboardNotificationsState)
            obj.unread_count = value
            self.assertEqual(obj.badge_label, label)
            self.assertEqual(obj.unread_count, value)

    def test_component_has_bounded_list_attached_badge_and_keyboard_fallback(self):
        rendered = str(_topbar("Dashboard"))
        for fragment in ("notification-scroll-list", "data-page", "on_list_scroll", "Carregar mais", "9+", "absolute", "relative", "min(420px, 86vw)", "min(48vh, 380px)"):
            # The capped label is a computed state var, not literal JSX text.
            if fragment == "9+":
                self.assertIn("badge_label", rendered)
            else:
                self.assertIn(fragment, rendered)
        self.assertNotIn("previous_page", rendered)
        self.assertNotIn("next_page", rendered)
        source = (Path(__file__).resolve().parents[1] / "Meu_projeto/components/layout.py").read_text(encoding="utf-8")
        self.assertIn(".throttle(600)", source)
        self.assertIn('overflow_x="hidden"', source)
