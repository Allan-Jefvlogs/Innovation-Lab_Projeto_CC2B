"""Contract tests for the report filter options client endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from Meu_projeto.services.xano_client import (
    XanoAuthClient,
    XanoPermissionError,
    XanoRequestCoordinator,
    XanoRequestError,
    XanoServerError,
)


MOCK_BASE_URL = "https://nexstock-test.invalid"
MOCK_TOKEN = "test-token-never-logged"
REPORT_OPTIONS_PATH = "/api:estoque/report_options"


class ReportOptionsContractTests(unittest.IsolatedAsyncioTestCase):
    def _install_transport(self, transport: httpx.MockTransport):
        real_async_client = httpx.AsyncClient

        def make_client(*args, **kwargs):
            kwargs["transport"] = transport
            return real_async_client(*args, **kwargs)

        return patch(
            "Meu_projeto.services.xano_client.httpx.AsyncClient",
            side_effect=make_client,
        )

    def _client(self) -> XanoAuthClient:
        return XanoAuthClient(
            base_url=MOCK_BASE_URL,
            timeout=0.2,
            coordinator=XanoRequestCoordinator(5, 20),
        )

    async def test_product_and_supplier_options_preserve_paginated_response_contract(self):
        calls: list[tuple[str, str, str, str]] = []
        responses = {
            "product": {
                "items": [{"id": 23, "codigo": "P-23", "nome": "Produto 23"}],
                "curPage": 1,
                "perPage": 100,
                "nextPage": None,
                "pageTotal": 1,
                "itemsTotal": 1,
            },
            "supplier": {
                "items": [{"id": 8, "nome_razao_social": "Fornecedor 8"}],
                "curPage": 2,
                "perPage": 50,
                "nextPage": 3,
                "pageTotal": 3,
                "itemsTotal": 121,
            },
        }

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(
                (
                    request.method,
                    request.url.path,
                    request.url.params.get("kind", ""),
                    request.url.params.get("page", ""),
                )
            )
            kind = request.url.params["kind"]
            return httpx.Response(200, json=responses[kind], request=request)

        transport = httpx.MockTransport(handler)
        client = self._client()
        with self._install_transport(transport):
            products = await client.list_report_options(
                MOCK_TOKEN, "product", page=1, per_page=100
            )
            suppliers = await client.list_report_options(
                MOCK_TOKEN, "supplier", page=2, per_page=50
            )

        self.assertEqual(products, responses["product"])
        self.assertEqual(suppliers, responses["supplier"])
        self.assertEqual(
            calls,
            [
                ("GET", REPORT_OPTIONS_PATH, "product", "1"),
                ("GET", REPORT_OPTIONS_PATH, "supplier", "2"),
            ],
        )

    async def test_malformed_response_is_not_converted_to_an_empty_options_list(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"items": None}, request=request)

        client = self._client()
        with self._install_transport(httpx.MockTransport(handler)):
            with self.assertRaises(XanoServerError):
                await client.list_report_options(MOCK_TOKEN, "supplier")

        self.assertEqual(calls, 1)

    async def test_server_error_propagates_instead_of_returning_empty_options(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                500,
                json={"code": "ERROR_FATAL", "message": "Unable to locate variable"},
                request=request,
            )

        client = self._client()
        with self._install_transport(httpx.MockTransport(handler)):
            with self.assertRaises(XanoRequestError) as caught:
                await client.list_report_options(MOCK_TOKEN, "supplier")

        self.assertEqual(caught.exception.status_code, 500)
        # The HTTP client intentionally normalizes unknown backend codes;
        # it still propagates the failure instead of manufacturing options.
        self.assertEqual(caught.exception.error_code, "API_ERROR")
        self.assertEqual(calls, 1)

    async def test_http_429_403_and_404_keep_their_error_classification(self):
        cases = [
            (429, {"Retry-After": "5"}, XanoRequestError),
            (403, {}, XanoPermissionError),
            (404, {}, XanoRequestError),
        ]
        for status, headers, error_type in cases:
            with self.subTest(status=status):
                calls = 0

                def handler(request: httpx.Request) -> httpx.Response:
                    nonlocal calls
                    calls += 1
                    return httpx.Response(
                        status,
                        headers=headers,
                        json={"code": "TEST_ERROR", "message": "Simulated response"},
                        request=request,
                    )

                client = self._client()
                with self._install_transport(httpx.MockTransport(handler)):
                    with self.assertRaises(error_type) as caught:
                        await client.list_report_options(MOCK_TOKEN, "supplier")

                self.assertEqual(caught.exception.status_code, status)
                if status == 429:
                    self.assertEqual(caught.exception.retry_after, "5")
                self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
