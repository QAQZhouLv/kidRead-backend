from __future__ import annotations

from app.cache.base import CacheBackend


class NoopCache(CacheBackend):
    def get(self, key: str, default=None):
        return default

    def set(self, key: str, value, ttl: int | None = None) -> None:
        return None

    def delete(self, key: str) -> None:
        return None
