from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.task_record_repository import TaskRecordRepository


def _task_key(task_id: str) -> str:
    return f"kidread:task:{task_id}"


def _safe_cache_set(db: Session, task_id: str, payload: dict[str, Any]) -> None:
    try:
        from app.core.runtime import build_runtime

        runtime = build_runtime(db)
        runtime.cache.set(_task_key(task_id), payload, ttl=3600)
    except Exception:
        pass


def create_task_record(db: Session, *, task_type: str, target_type: str | None = None, target_id: int | None = None, payload: dict[str, Any] | None = None) -> str:
    repo = TaskRecordRepository(db)
    row = repo.create_task(task_type=task_type, target_type=target_type, target_id=target_id, payload=payload)
    _safe_cache_set(
        db,
        row.task_id,
        {
            "task_id": row.task_id,
            "task_type": task_type,
            "target_type": target_type,
            "target_id": target_id,
            "status": "pending",
        },
    )
    return row.task_id


def update_task_status(db: Session, *, task_id: str, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
    repo = TaskRecordRepository(db)
    if status == "running":
        repo.mark_running(task_id)
    elif status == "success":
        repo.mark_success(task_id, result or {})
    elif status == "failed":
        repo.mark_failed(task_id, error or "")
    _safe_cache_set(db, task_id, {"task_id": task_id, "status": status, "result": result or {}, "error": error or ""})
