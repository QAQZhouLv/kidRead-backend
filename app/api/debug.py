from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import DEBUG, QDRANT_COLLECTION, QDRANT_URL, REDIS_URL, VECTOR_BACKEND
from app.core.runtime import build_runtime
from app.db.session import RESOLVED_DATABASE_URL, SessionLocal
from app.repositories.story_chunk_repository import StoryChunkRepository
from app.repositories.task_record_repository import TaskRecordRepository

router = APIRouter(prefix="/api/debug", tags=["debug"])


def _debug_enabled():
    if not DEBUG:
        raise HTTPException(status_code=404, detail="Debug endpoints are disabled")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/runtime")
def debug_runtime(db: Session = Depends(get_db)):
    _debug_enabled()
    runtime = build_runtime(db)
    return {
        "database_url": RESOLVED_DATABASE_URL.split("@")[0] + "@***" if "@" in RESOLVED_DATABASE_URL else RESOLVED_DATABASE_URL,
        "redis_url": REDIS_URL,
        "vector_backend_config": VECTOR_BACKEND,
        "vector_store_class": runtime.vector_store.__class__.__name__,
        "cache_class": runtime.cache.__class__.__name__,
        "task_queue_class": runtime.task_queue.__class__.__name__,
        "qdrant_url": QDRANT_URL,
        "qdrant_collection": QDRANT_COLLECTION,
        "flags": runtime.flags.__dict__,
    }


@router.get("/story/{story_id}/chunks")
def debug_story_chunks(story_id: int, db: Session = Depends(get_db)):
    _debug_enabled()
    repo = StoryChunkRepository(db)
    return [repo.to_dict(row) for row in repo.list_story_chunks(story_id=story_id)]


@router.get("/story/{story_id}/tasks")
def debug_story_tasks(story_id: int, db: Session = Depends(get_db)):
    _debug_enabled()
    repo = TaskRecordRepository(db)
    rows = repo.list_for_target(target_type="story", target_id=story_id)
    return [
        {
            "task_id": row.task_id,
            "task_type": row.task_type,
            "status": row.status,
            "error_message": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]
