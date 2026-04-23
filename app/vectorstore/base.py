from __future__ import annotations

from abc import ABC, abstractmethod


class StoryVectorStore(ABC):
    @abstractmethod
    def search_story_chunks(
        self,
        *,
        story_id: int,
        query_text: str,
        full_content: str,
        top_k: int = 3,
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def upsert_story_chunks(self, *, story_id: int, chunks: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_story_chunks(self, *, story_id: int) -> None:
        raise NotImplementedError
