from __future__ import annotations

from collections.abc import Callable

from app.vectorstore.base import StoryVectorStore

try:
    from pymilvus import MilvusClient
except Exception:  # pragma: no cover
    MilvusClient = None


class MilvusVectorStore(StoryVectorStore):
    def __init__(
        self,
        *,
        uri: str,
        token: str,
        collection_name: str,
        content_field: str,
        embed_query_fn: Callable[[str], list[float]],
        embed_texts_fn: Callable[[list[str]], list[list[float]]],
    ):
        if MilvusClient is None:
            raise RuntimeError("pymilvus is not installed")
        self.client = MilvusClient(uri=uri, token=token or None)
        self.collection_name = collection_name
        self.content_field = content_field
        self.embed_query_fn = embed_query_fn
        self.embed_texts_fn = embed_texts_fn

    def search_story_chunks(
        self,
        *,
        story_id: int,
        query_text: str,
        full_content: str,
        top_k: int = 3,
    ) -> list[str]:
        vector = self.embed_query_fn(query_text)
        if not vector:
            return []

        results = self.client.search(
            collection_name=self.collection_name,
            data=[vector],
            filter=f"story_id == {story_id}",
            limit=top_k,
            output_fields=[self.content_field],
        )

        rows = results[0] if results and isinstance(results, list) else []
        chunks: list[str] = []
        for row in rows:
            entity = row.get("entity") or {}
            content = entity.get(self.content_field) or row.get(self.content_field) or ""
            content = (content or "").strip()
            if content:
                chunks.append(content)
        return chunks

    def upsert_story_chunks(self, *, story_id: int, chunks: list[str]) -> None:
        clean_chunks = [chunk.strip() for chunk in chunks if (chunk or "").strip()]
        if not clean_chunks:
            return

        vectors = self.embed_texts_fn(clean_chunks)
        if len(vectors) != len(clean_chunks):
            return

        rows = []
        for idx, (chunk, vector) in enumerate(zip(clean_chunks, vectors)):
            rows.append(
                {
                    "id": f"story:{story_id}:chunk:{idx}",
                    "story_id": story_id,
                    self.content_field: chunk,
                    "vector": vector,
                    "chunk_index": idx,
                }
            )

        self.delete_story_chunks(story_id=story_id)
        self.client.upsert(collection_name=self.collection_name, data=rows)

    def delete_story_chunks(self, *, story_id: int) -> None:
        self.client.delete(
            collection_name=self.collection_name,
            filter=f"story_id == {story_id}",
        )
