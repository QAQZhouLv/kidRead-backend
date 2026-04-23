from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.runtime import build_runtime
from app.db.session import SessionLocal
from app.models.story import Story

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def split_story_chunks(
    full_content: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    text = (full_content or "").replace("\r", "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return [text[:chunk_size]]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = para if not current else f"{current}\n{para}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            if chunk_overlap > 0 and len(current) > chunk_overlap:
                current = current[-chunk_overlap:] + "\n" + para
            else:
                current = para
        else:
            chunks.append(para[:chunk_size].strip())
            tail_start = max(0, chunk_size - chunk_overlap)
            current = para[tail_start:].strip()

    if current.strip():
        chunks.append(current.strip())

    cleaned: list[str] = []
    seen = set()
    for chunk in chunks:
        value = (chunk or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def sync_story_content_to_vector_store(vector_store, *, story_id: int, content: str) -> None:
    chunks = split_story_chunks(content or "")
    vector_store.upsert_story_chunks(story_id=story_id, chunks=chunks)


def delete_story_from_vector_store(vector_store, *, story_id: int) -> None:
    vector_store.delete_story_chunks(story_id=story_id)


def sync_story_to_vector_store(db: Session, story: Story) -> None:
    runtime = build_runtime(db)
    sync_story_content_to_vector_store(
        runtime.vector_store,
        story_id=story.id,
        content=story.content or "",
    )


def delete_story_vectors_by_id(db: Session, *, story_id: int) -> None:
    runtime = build_runtime(db)
    delete_story_from_vector_store(runtime.vector_store, story_id=story_id)


def sync_story_vectors_task(story_id: int) -> None:
    db = SessionLocal()
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story or getattr(story, "is_deleted", False):
            return
        sync_story_to_vector_store(db, story)
    finally:
        db.close()


def delete_story_vectors_task(story_id: int) -> None:
    db = SessionLocal()
    try:
        delete_story_vectors_by_id(db, story_id=story_id)
    finally:
        db.close()
