from __future__ import annotations

import json

from app.core.config import REDIS_QUEUE_NAME, REDIS_URL
from app.db.session import SessionLocal
from app.tasks.job_runner import handle_job

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


def run_worker(block_timeout: int = 5):
    if redis is None:
        raise RuntimeError("redis package is not installed")
    if not REDIS_URL:
        raise RuntimeError("REDIS_URL is empty")

    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    while True:
        item = client.brpop(REDIS_QUEUE_NAME, timeout=block_timeout)
        if not item:
            continue

        _, raw = item
        try:
            job = json.loads(raw)
            job_name = job.get("job_name") or ""
            payload = job.get("payload") or {}
        except Exception:
            continue

        db = SessionLocal()
        try:
            handle_job(db, job_name, payload)
        finally:
            db.close()


if __name__ == "__main__":
    run_worker()
