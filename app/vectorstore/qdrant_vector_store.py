from __future__ import annotations

from collections.abc import Callable
from uuid import NAMESPACE_URL, uuid5

from app.core.config import QDRANT_VECTOR_SIZE
from app.vectorstore.base import StoryVectorStore

try:  # qdrant-client is optional at import time but required for qdrant mode.
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover
    QdrantClient = None
    qmodels = None


class QdrantVectorStore(StoryVectorStore):
    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        collection_name: str,
        embed_query_fn: Callable[[str], list[float]],
        embed_texts_fn: Callable[[list[str]], list[list[float]]],
    ):
        if QdrantClient is None or qmodels is None:
            raise RuntimeError("qdrant-client package is not installed")
        self.client = QdrantClient(url=url, api_key=api_key or None)
        self.collection_name = collection_name
        self.embed_query_fn = embed_query_fn
        self.embed_texts_fn = embed_texts_fn
        self.vector_size = QDRANT_VECTOR_SIZE or 0

    @staticmethod
    def _point_id(story_id: int, chunk_index: int) -> str:
        return str(uuid5(NAMESPACE_URL, f"kidread-story-{story_id}-chunk-{chunk_index}"))

    def _ensure_collection(self, vector_size: int) -> None:
        if not vector_size:
            return
        try:
            self.client.get_collection(self.collection_name)
            return
        except Exception:
            pass
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )

    def search_story_chunks(self, *, story_id: int, query_text: str, full_content: str, top_k: int = 3) -> list[str]:
        vector = self.embed_query_fn(query_text)
        if not vector:
            return []
        self._ensure_collection(len(vector))

        story_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="story_id", match=qmodels.MatchValue(value=int(story_id)))]
        )

        try:
            if hasattr(self.client, "search"):
                rows = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    query_filter=story_filter,
                    limit=top_k,
                    with_payload=True,
                )
            else:
                result = self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    query_filter=story_filter,
                    limit=top_k,
                    with_payload=True,
                )
                rows = getattr(result, "points", result)
        except Exception:
            return []

        chunks: list[str] = []
        for row in rows or []:
            payload = getattr(row, "payload", None) or {}
            content = (payload.get("content") or payload.get("chunk_text") or "").strip()
            if content:
                chunks.append(content)
        return chunks

    def upsert_story_chunks(self, *, story_id: int, chunks: list[str]) -> None:
        clean_chunks = [chunk.strip() for chunk in chunks if (chunk or "").strip()]
        if not clean_chunks:
            return
        vectors = self.embed_texts_fn(clean_chunks)
        if len(vectors) != len(clean_chunks) or not vectors or not vectors[0]:
            return
        self._ensure_collection(len(vectors[0]))
        self.delete_story_chunks(story_id=story_id)

        points = []
        for idx, (chunk, vector) in enumerate(zip(clean_chunks, vectors)):
            if not vector:
                continue
            point_id = self._point_id(story_id, idx)
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "story_id": int(story_id),
                        "chunk_index": idx,
                        "content": chunk,
                        "source": "story",
                        "point_id": point_id,
                    },
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    def delete_story_chunks(self, *, story_id: int) -> None:
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[qmodels.FieldCondition(key="story_id", match=qmodels.MatchValue(value=int(story_id)))]
                    )
                ),
                wait=True,
            )
        except Exception:
            return None
