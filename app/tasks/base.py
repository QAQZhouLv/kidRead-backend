from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TaskQueue(ABC):
    @abstractmethod
    def enqueue(self, job_name: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError
