from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StoryRepository(ABC):
    @abstractmethod
    def get_story_for_prompt(self, story_id: int, *, user_id: int | None = None) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def get_story_age(self, story_id: int, *, user_id: int | None = None) -> int | None:
        raise NotImplementedError
