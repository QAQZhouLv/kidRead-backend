from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.story import Story
from app.repositories.story_chunk_repository import StoryChunkRepository
from app.services.task_status_service import create_task_record, update_task_status

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def split_story_chunks(full_content: str, *, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
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
            chunks.append(current)
            if chunk_overlap > 0 and len(current) > chunk_overlap:
                current = current[-chunk_overlap:] + "\n" + para
            else:
                current = para
        else:
            chunks.append(para[:chunk_size])
            current = para[chunk_size - chunk_overlap :] if len(para) > chunk_size else ""

    if current.strip():
        chunks.append(current.strip())

    cleaned: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or chunk in seen:
            continue
        seen.add(chunk)
        cleaned.append(chunk)
    return cleaned


def sync_story_to_vector_store(db: Session, story: Story) -> dict:
    from app.core.runtime import build_runtime

    chunks = split_story_chunks(story.content or "")
    chunk_repo = StoryChunkRepository(db)
    chunk_rows = chunk_repo.replace_story_chunks(story_id=story.id, chunks=chunks)

    runtime = build_runtime(db)
    qdrant_synced = False
    try:
        runtime.vector_store.upsert_story_chunks(story_id=story.id, chunks=chunks)
        qdrant_synced = True
    except Exception:
        qdrant_synced = False

    return {
        "story_id": story.id,
        "chunk_count": len(chunk_rows),
        "vector_backend": runtime.vector_store.__class__.__name__,
        "qdrant_synced": qdrant_synced,
    }


def delete_story_from_vector_store(db: Session, story_id: int) -> dict:
    from app.core.runtime import build_runtime

    chunk_repo = StoryChunkRepository(db)
    deleted_chunks = chunk_repo.delete_story_chunks(story_id=story_id)
    runtime = build_runtime(db)
    try:
        runtime.vector_store.delete_story_chunks(story_id=story_id)
    except Exception:
        pass
    return {"story_id": story_id, "deleted_chunks": deleted_chunks}


def sync_story_vectors_task(story_id: int, task_id: str | None = None) -> None:
    db = SessionLocal()
    local_task_id = task_id
    try:
        if not local_task_id:
            local_task_id = create_task_record(
                db,
                task_type="sync_story_vectors",
                target_type="story",
                target_id=story_id,
                payload={"story_id": story_id},
            )
        update_task_status(db, task_id=local_task_id, status="running")
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story or getattr(story, "is_deleted", False):
            update_task_status(db, task_id=local_task_id, status="failed", error="Story not found or deleted")
            return
        result = sync_story_to_vector_store(db, story)
        update_task_status(db, task_id=local_task_id, status="success", result=result)
    except Exception as exc:
        if local_task_id:
            update_task_status(db, task_id=local_task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


def delete_story_vectors_task(story_id: int, task_id: str | None = None) -> None:
    db = SessionLocal()
    local_task_id = task_id
    try:
        if not local_task_id:
            local_task_id = create_task_record(
                db,
                task_type="delete_story_vectors",
                target_type="story",
                target_id=story_id,
                payload={"story_id": story_id},
            )
        update_task_status(db, task_id=local_task_id, status="running")
        result = delete_story_from_vector_store(db, story_id)
        update_task_status(db, task_id=local_task_id, status="success", result=result)
    except Exception as exc:
        if local_task_id:
            update_task_status(db, task_id=local_task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()
