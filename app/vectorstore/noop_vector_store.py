from __future__ import annotations

from app.vectorstore.base import StoryVectorStore


class NoopVectorStore(StoryVectorStore):
    def search_story_chunks(
        self,
        *,
        story_id: int,
        query_text: str,
        full_content: str,
        top_k: int = 3,
    ) -> list[str]:
        return []

    def upsert_story_chunks(self, *, story_id: int, chunks: list[str]) -> None:
        return None

    def delete_story_chunks(self, *, story_id: int) -> None:
        return None
