"""Cache efemero, em memoria e isolado por sessao para leituras privadas."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from typing import Any


CacheKey = tuple[str, str, str, str]
CACHE_MISS = object()


class SessionReadCache:
    """Armazena respostas projetadas sem reter tokens ou grants."""

    def __init__(self, max_entries: int = 512) -> None:
        self._entries: dict[CacheKey, tuple[float, float, Any]] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries

    @staticmethod
    def session_fingerprint(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def key(
        cls,
        authorization_scope: str,
        endpoint: str,
        token: str,
        params: dict[str, Any],
    ) -> CacheKey:
        normalized_params = json.dumps(
            params, sort_keys=True, separators=(",", ":"), default=str
        )
        return (
            authorization_scope,
            endpoint,
            cls.session_fingerprint(token),
            normalized_params,
        )

    def get(
        self, key: CacheKey, ttl: float, *, allow_stale: bool = False
    ) -> tuple[Any, bool]:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return CACHE_MISS, False
            created_at, _stored_ttl, value = entry
            age = max(0.0, now - created_at)
            if ttl > 0 and age <= ttl:
                return copy.deepcopy(value), True
            if ttl > 0 and allow_stale and age <= max(ttl * 5, ttl + 30):
                return copy.deepcopy(value), False
            self._entries.pop(key, None)
            return CACHE_MISS, False

    def set(self, key: CacheKey, value: Any, ttl: float) -> None:
        with self._lock:
            now = time.monotonic()
            self._entries[key] = (now, ttl, copy.deepcopy(value))
            for cached_key, (created_at, cached_ttl, _cached_value) in list(
                self._entries.items()
            ):
                if now - created_at > max(cached_ttl * 5, cached_ttl + 30):
                    self._entries.pop(cached_key, None)
            while len(self._entries) > self._max_entries:
                oldest_key = min(
                    self._entries, key=lambda item: self._entries[item][0]
                )
                self._entries.pop(oldest_key, None)

    def update_preserving_age(self, key: CacheKey, value: Any) -> None:
        """Atualiza um registro conhecido sem renovar a confianca da listagem."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                created_at, ttl, _old_value = entry
                self._entries[key] = (created_at, ttl, copy.deepcopy(value))

    def invalidate(self, *, endpoint: str, token: str) -> None:
        fingerprint = self.session_fingerprint(token)
        with self._lock:
            for key in list(self._entries):
                if key[1] == endpoint and key[2] == fingerprint:
                    self._entries.pop(key, None)

    def clear_session(self, token: str) -> None:
        if not token:
            return
        fingerprint = self.session_fingerprint(token)
        with self._lock:
            for key in list(self._entries):
                if key[2] == fingerprint:
                    self._entries.pop(key, None)

    def clear(self) -> None:
        """Limpa o cache do processo, inclusive para isolamento de testes."""
        with self._lock:
            self._entries.clear()


session_read_cache = SessionReadCache()


def clear_session_read_cache(token: str) -> None:
    """Remove leituras privadas associadas a uma sessao encerrada."""
    session_read_cache.clear_session(token)
