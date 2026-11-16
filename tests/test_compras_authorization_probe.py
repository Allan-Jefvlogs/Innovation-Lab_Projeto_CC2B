"""Somente transporte simulado: não acessa Xano."""

from contextlib import redirect_stdout
import io
import unittest

import httpx

from scripts.verificar_autorizacao_compras import classify, project_urls, run_checks


class AuthorizationProbeTests(unittest.TestCase):
    def test_only_get_no_auth_me_no_payloads_and_expected_grants(self):
        requests = []

        def respond(request):
            requests.append(request)
            self.assertEqual(request.method, "GET")
            self.assertNotIn("auth/me", request.url.path)
            self.assertEqual(request.content, b"")
            if request.url.path.endswith("/purchase_requests"):
                return httpx.Response(200, json={"items": [{"id": 11, "private": "DO_NOT_PRINT"}], "itemsTotal": 1, "curPage": 1, "perPage": 1})
            if request.url.path.endswith("/by_id/11"):
                return httpx.Response(200, json={"solicitacao": {"id": 11}, "private": "DO_NOT_PRINT"})
            return httpx.Response(403, json={"code": "ERROR_CODE_ACCESS_DENIED", "message": "PERMISSION_DENIED", "private": "DO_NOT_PRINT"})

        output = io.StringIO()
        with httpx.Client(transport=httpx.MockTransport(respond)) as client, redirect_stdout(output):
            self.assertEqual(run_checks(client, project_urls(), pause=lambda _: None), 0)
        self.assertEqual(len(requests), 6)
        self.assertNotIn("DO_NOT_PRINT", output.getvalue())

    def test_unknown_403_401_404_and_429_do_not_pass(self):
        for status, body in ((401, {}), (403, {"message": "USER_INACTIVE"}), (404, {}), (429, {})):
            self.assertNotEqual(classify(status, 403, body), "APROVADO")

    def test_rate_limit_stops_without_retry(self):
        calls = []

        def respond(request):
            calls.append(request)
            return httpx.Response(429, headers={"Retry-After": "20"}, json={})

        with httpx.Client(transport=httpx.MockTransport(respond)) as client, redirect_stdout(io.StringIO()):
            self.assertEqual(run_checks(client, project_urls(), pause=lambda _: None), 2)
        self.assertEqual(len(calls), 1)

    def test_empty_list_does_not_guess_detail_id(self):
        calls = []

        def respond(request):
            calls.append(request)
            if request.url.path.endswith("/purchase_requests"):
                return httpx.Response(200, json={"items": [], "itemsTotal": 0, "curPage": 1, "perPage": 1})
            return httpx.Response(403, json={"message": "PERMISSION_DENIED"})

        with httpx.Client(transport=httpx.MockTransport(respond)) as client, redirect_stdout(io.StringIO()):
            self.assertEqual(run_checks(client, project_urls(), pause=lambda _: None), 2)
        self.assertEqual(len(calls), 5)
        self.assertFalse(any("/by_id/" in r.url.path for r in calls))
