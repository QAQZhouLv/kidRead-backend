from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MessageRepository(ABC):
    @abstractmethod
    def create_user_message(
        self,
        *,
        user_id: int,
        scene: str,
        story_id: int,
        session_id: str,
        input_mode: str,
        user_text: str,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def create_assistant_message(
        self,
        *,
        user_id: int,
        scene: str,
        story_id: int,
        session_id: str,
        intent: str,
        lead_text: str,
        story_text: str,
        guide_text: str,
        choices: list[str],
        should_save: bool,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def list_recent_history(self, session_id: str, *, user_id: int | None = None, limit: int = 10) -> list[Any]:
        raise NotImplementedError
