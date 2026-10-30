"""Isolated request-budget, cooldown, and GET single-flight tests."""

from __future__ import annotations

import asyncio
import unittest
from email.utils import formatdate
from unittest.mock import patch

import httpx

from Meu_projeto.services.xano_client import (
    XanoAuthClient,
    XanoAuthError,
    XanoConnectionError,
    XanoPermissionError,
    XanoRateLimitError,
    XanoRequestCoordinator,
    XanoRequestError,
    _configured_positive_int,
)


BASE_URL = "https://nexstock-test.invalid"


class _Clock:
    def __init__(self):
        self.monotonic = 100.0
        self.wall = 1_800_000_000.0

    def tick(self, seconds: float):
        self.monotonic += seconds
        self.wall += seconds


class _BlockingTransport(httpx.AsyncBaseTransport):
    def __init__(self, *, status_code=200, json_body=None):
        self.status_code = status_code
        self.json_body = json_body or {"ok": True}
        self.calls = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return httpx.Response(self.status_code, json=self.json_body, request=request)


class XanoRequestCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    def _client(self, coordinator, transport):
        real_client = httpx.AsyncClient

        def make_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_client(*args, **kwargs)

        context = patch(
            "Meu_projeto.services.xano_client.httpx.AsyncClient",
            side_effect=make_client,
        )
        return XanoAuthClient(base_url=BASE_URL, timeout=0.2, coordinator=coordinator), context

    async def test_retry_after_http_date_is_respected(self):
        clock = _Clock()
        retry_at = formatdate(clock.wall + 17, usegmt=True)
        delay = XanoRequestCoordinator._retry_delay(retry_at, 20, clock.wall)
        self.assertEqual(delay, 17)

    async def test_six_call_report_flow_fits_budget_seven_but_not_five(self):
        async def run_flow(limit):
            coordinator = XanoRequestCoordinator(limit, 20)
            remote_calls = 0

            async def send():
                nonlocal remote_calls
                remote_calls += 1
                return httpx.Response(200, json={"ok": True})

            locally_blocked = 0
            for index in range(6):
                try:
                    await coordinator.request(
                        "GET",
                        f"https://reports.invalid/read/{index}",
                        token="same-session",
                        params=None,
                        send=send,
                    )
                except XanoRateLimitError as exc:
                    self.assertEqual(exc.origin, "local_coordinator")
                    locally_blocked += 1
            return remote_calls, locally_blocked

        self.assertEqual(await run_flow(5), (5, 1))
        self.assertEqual(await run_flow(7), (6, 0))

    async def test_request_budget_environment_value_is_clamped_to_seven(self):
        with patch.dict("os.environ", {"XANO_REQUEST_BUDGET": "9"}):
            self.assertEqual(_configured_positive_int("XANO_REQUEST_BUDGET", 7), 7)
        with patch.dict("os.environ", {"XANO_REQUEST_BUDGET": "3"}):
            self.assertEqual(_configured_positive_int("XANO_REQUEST_BUDGET", 7), 3)

    async def test_sliding_budget_rejects_excess_and_recovers_after_window(self):
        clock = _Clock()
        coordinator = XanoRequestCoordinator(
            2, 20, clock=lambda: clock.monotonic, wall_clock=lambda: clock.wall
        )
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"ok": True}, request=request)

        client, context = self._client(coordinator, httpx.MockTransport(handler))
        with context:
            await client._inventory_request("GET", "/one", "token-a")
            await client._inventory_request("GET", "/two", "token-a")
            with self.assertRaises(XanoRateLimitError) as caught:
                await client._inventory_request("GET", "/three", "token-a")
            self.assertEqual(caught.exception.status_code, 429)
            self.assertGreater(caught.exception.retry_after_seconds, 0)
            self.assertEqual(calls, 2)

            clock.tick(20)
            await client._inventory_request("GET", "/three", "token-a")

        self.assertEqual(calls, 3)

    async def test_identical_gets_share_one_inflight_request_and_reservation(self):
        coordinator = XanoRequestCoordinator(1, 20)
        transport = _BlockingTransport()
        client, context = self._client(coordinator, transport)
        with context:
            first = asyncio.create_task(
                client._inventory_request(
                    "GET", "/products", "same-session", params={"page": 1, "per_page": 10}
                )
            )
            await asyncio.wait_for(transport.started.wait(), timeout=1)
            second = asyncio.create_task(
                client._inventory_request(
                    "GET", "/products", "same-session", params={"per_page": 10, "page": 1}
                )
            )
            await asyncio.sleep(0)
            self.assertEqual(transport.calls, 1)
            transport.release.set()
            self.assertEqual(await asyncio.gather(first, second), [{"ok": True}, {"ok": True}])
        self.assertEqual(transport.calls, 1)

    async def test_distinct_sessions_never_share_gets(self):
        coordinator = XanoRequestCoordinator(2, 20)
        transport = _BlockingTransport()
        client, context = self._client(coordinator, transport)
        with context:
            first = asyncio.create_task(
                client._inventory_request("GET", "/products", "session-a")
            )
            await asyncio.wait_for(transport.started.wait(), timeout=1)
            second = asyncio.create_task(
                client._inventory_request("GET", "/products", "session-b")
            )
            await asyncio.sleep(0)
            self.assertEqual(transport.calls, 2)
            transport.release.set()
            await asyncio.gather(first, second)
        self.assertEqual(transport.calls, 2)

    async def test_simultaneous_distinct_requests_reserve_budget_atomically(self):
        coordinator = XanoRequestCoordinator(3, 20)
        transport = _BlockingTransport()
        client, context = self._client(coordinator, transport)
        with context:
            requests = [
                asyncio.create_task(
                    client._inventory_request("GET", f"/items/{index}", f"session-{index}")
                )
                for index in range(8)
            ]
            await asyncio.wait_for(transport.started.wait(), timeout=1)
            await asyncio.sleep(0)
            self.assertEqual(transport.calls, 3)
            transport.release.set()
            results = await asyncio.gather(*requests, return_exceptions=True)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 3)
        self.assertEqual(sum(isinstance(result, XanoRateLimitError) for result in results), 5)
        self.assertEqual(transport.calls, 3)

    async def test_429_cooldown_is_shared_and_post_is_never_retried_or_deduped(self):
        clock = _Clock()
        coordinator = XanoRequestCoordinator(
            5, 20, clock=lambda: clock.monotonic, wall_clock=lambda: clock.wall
        )
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "5"},
                    json={"code": "TOO_MANY_REQUESTS"},
                    request=request,
                )
            return httpx.Response(200, json={"ok": True}, request=request)

        transport = httpx.MockTransport(handler)
        client_a, context_a = self._client(coordinator, transport)
        client_b, context_b = self._client(coordinator, transport)
        with context_a, context_b:
            with self.assertRaises(XanoRequestError) as caught:
                await client_a._inventory_request(
                    "POST", "/products", "token-a", json_payload={"name": "fake"}
                )
            self.assertEqual(caught.exception.status_code, 429)
            self.assertEqual(caught.exception.retry_after, "5")
            self.assertIn("O Xano", caught.exception.message)
            with self.assertRaises(XanoRateLimitError) as local_block:
                await client_b._inventory_request(
                    "POST", "/products", "token-a", json_payload={"name": "fake"}
                )
            self.assertEqual(local_block.exception.origin, "local_coordinator")
            self.assertIn("Limite local", local_block.exception.message)
            self.assertEqual(calls, 1)

            clock.tick(5)
            await client_b._inventory_request(
                "POST", "/products", "token-a", json_payload={"name": "fake"}
            )
        self.assertEqual(calls, 2)

    async def test_auth_errors_and_timeout_keep_existing_classification_without_retry(self):
        clock = _Clock()
        coordinator = XanoRequestCoordinator(
            5, 20, clock=lambda: clock.monotonic, wall_clock=lambda: clock.wall
        )
        statuses = [401, 403]
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            if statuses:
                status = statuses.pop(0)
                return httpx.Response(status, json={"code": "DENIED"}, request=request)
            raise httpx.ReadTimeout("controlled timeout", request=request)

        client, context = self._client(coordinator, httpx.MockTransport(handler))
        with context:
            with self.assertRaises(XanoAuthError):
                await client._inventory_request("GET", "/one", "token-a")
            with self.assertRaises(XanoPermissionError):
                await client._inventory_request("GET", "/two", "token-a")
            with self.assertRaises(XanoConnectionError):
                await client._inventory_request("GET", "/three", "token-a")
        self.assertEqual(calls, 3)


if __name__ == "__main__":
    unittest.main()
