from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.tasks.base import TaskQueue


class InlineQueue(TaskQueue):
    def __init__(self, handlers: dict[str, Callable[[dict[str, Any]], None]] | None = None):
        self.handlers = handlers or {}

    def enqueue(self, job_name: str, payload: dict[str, Any]) -> None:
        handler = self.handlers.get(job_name)
        if handler is None:
            return
        handler(payload)
