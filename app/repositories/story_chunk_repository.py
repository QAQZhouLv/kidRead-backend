from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.story_chunk import StoryChunk


class StoryChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_story_chunks(self, *, story_id: int, chunks: list[str]) -> list[StoryChunk]:
        self.db.query(StoryChunk).filter(StoryChunk.story_id == story_id).delete()
        rows: list[StoryChunk] = []
        now = datetime.utcnow()
        for idx, chunk in enumerate(chunks):
            text = (chunk or "").strip()
            if not text:
                continue
            point_id = f"story-{story_id}-chunk-{idx}"
            row = StoryChunk(
                story_id=story_id,
                chunk_index=idx,
                chunk_text=text,
                qdrant_point_id=point_id,
                metadata_json=json.dumps({"story_id": story_id, "chunk_index": idx, "source": "story"}, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            rows.append(row)
        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        return rows

    def delete_story_chunks(self, *, story_id: int) -> int:
        count = self.db.query(StoryChunk).filter(StoryChunk.story_id == story_id).delete()
        self.db.commit()
        return int(count or 0)

    def list_story_chunks(self, *, story_id: int) -> list[StoryChunk]:
        return (
            self.db.query(StoryChunk)
            .filter(StoryChunk.story_id == story_id)
            .order_by(StoryChunk.chunk_index.asc(), StoryChunk.id.asc())
            .all()
        )

    @staticmethod
    def to_dict(row: StoryChunk) -> dict[str, Any]:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except Exception:
            metadata = {}
        return {
            "id": row.id,
            "story_id": row.story_id,
            "chunk_index": row.chunk_index,
            "chunk_text": row.chunk_text,
            "qdrant_point_id": row.qdrant_point_id,
            "metadata": metadata,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
