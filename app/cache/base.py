from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @contextmanager
    def lock(self, key: str, ttl: int = 30) -> Iterator[bool]:
        yield True
