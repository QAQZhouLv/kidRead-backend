from __future__ import annotations

import json
from typing import Any

from app.tasks.base import TaskQueue

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class RedisQueue(TaskQueue):
    def __init__(self, redis_url: str, queue_name: str = "kidread:jobs"):
        if redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.queue_name = queue_name

    def enqueue(self, job_name: str, payload: dict[str, Any]) -> None:
        job = {"job_name": job_name, "payload": payload}
        self.client.rpush(self.queue_name, json.dumps(job, ensure_ascii=False))
