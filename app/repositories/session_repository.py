from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SessionRepository(ABC):
    @abstractmethod
    def get_by_session_id(self, session_id: str, *, user_id: int | None = None) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def update_context_snapshot(
        self,
        session_id: str,
        snapshot: dict,
        guard_result: dict | None = None,
        *,
        user_id: int | None = None,
    ) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def update_draft(self, session_id: str, draft_content: str, *, user_id: int | None = None) -> Any | None:
        raise NotImplementedError
