"""Isolation and lifecycle tests for the in-memory Products read cache."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from Meu_projeto.pages import produtos
from Meu_projeto.services.session_read_cache import session_read_cache
from Meu_projeto.state.auth import AuthState


class SessionReadCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        session_read_cache.clear()

    def tearDown(self) -> None:
        session_read_cache.clear()

    def test_key_separates_session_scope_endpoint_and_normalized_parameters(self):
        first = produtos._cache_key(
            "products", "secret-session-a", {"page": 1, "per_page": 100}
        )
        same_query = produtos._cache_key(
            "products", "secret-session-a", {"per_page": 100, "page": 1}
        )
        other_session = produtos._cache_key(
            "products", "secret-session-b", {"page": 1, "per_page": 100}
        )
        other_scope = session_read_cache.key(
            "product_reference_read",
            "GET /products",
            "secret-session-a",
            {"page": 1, "per_page": 100},
        )
        other_params = produtos._cache_key(
            "products", "secret-session-a", {"page": 2, "per_page": 100}
        )

        self.assertEqual(first, same_query)
        self.assertNotEqual(first, other_session)
        self.assertNotEqual(first, other_scope)
        self.assertNotEqual(first, other_params)
        self.assertNotIn("secret-session-a", repr(first))

    def test_logout_removes_only_the_ending_sessions_cached_data(self):
        token_a, token_b = "private-session-a", "private-session-b"
        key_a = produtos._products_listing_key(token_a)
        key_b = produtos._products_listing_key(token_b)
        produtos._cache_set(key_a, {"items": [{"id": "1"}]})
        produtos._cache_set(key_b, {"items": [{"id": "2"}]})

        state = object.__new__(AuthState)
        object.__setattr__(state, "dirty_vars", set())
        state.auth_token = token_a
        state.error_message = ""
        state.password_change_notice = ""
        with patch("Meu_projeto.state.auth.rx.redirect", return_value="redirect"):
            self.assertEqual(state.logout(), "redirect")

        value_a, _ = produtos._cache_get(
            key_a, produtos.PRODUCTS_CACHE_TTL_SECONDS
        )
        value_b, fresh_b = produtos._cache_get(
            key_b, produtos.PRODUCTS_CACHE_TTL_SECONDS
        )
        self.assertIs(value_a, produtos._CACHE_MISS)
        self.assertEqual(value_b, {"items": [{"id": "2"}]})
        self.assertTrue(fresh_b)


if __name__ == "__main__":
    unittest.main()
