from __future__ import annotations

import json
from contextlib import contextmanager

from app.cache.base import CacheBackend

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class RedisCache(CacheBackend):
    def __init__(self, redis_url: str):
        if redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str, default=None):
        value = self.client.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except Exception:
            return value

    def set(self, key: str, value, ttl: int | None = None) -> None:
        payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        self.client.set(name=key, value=payload, ex=ttl)

    def delete(self, key: str) -> None:
        self.client.delete(key)

    @contextmanager
    def lock(self, key: str, ttl: int = 30):
        lock = self.client.lock(name=key, timeout=ttl)
        acquired = lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    lock.release()
                except Exception:
                    pass
