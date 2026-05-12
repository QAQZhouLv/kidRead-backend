from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.task_record import TaskRecord


class TaskRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, *, task_type: str, target_type: str | None = None, target_id: int | None = None, payload: dict[str, Any] | None = None, task_id: str | None = None) -> TaskRecord:
        row = TaskRecord(
            task_id=task_id or f"task-{uuid4().hex}",
            task_type=task_type,
            target_type=target_type,
            target_id=target_id,
            status="pending",
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_running(self, task_id: str) -> TaskRecord | None:
        row = self.db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not row:
            return None
        row.status = "running"
        row.started_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_success(self, task_id: str, result: dict[str, Any] | None = None) -> TaskRecord | None:
        row = self.db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not row:
            return None
        row.status = "success"
        row.result_json = json.dumps(result or {}, ensure_ascii=False)
        row.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_failed(self, task_id: str, error: str) -> TaskRecord | None:
        row = self.db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not row:
            return None
        row.status = "failed"
        row.error_message = str(error or "")
        row.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_for_target(self, *, target_type: str, target_id: int) -> list[TaskRecord]:
        return (
            self.db.query(TaskRecord)
            .filter(TaskRecord.target_type == target_type, TaskRecord.target_id == target_id)
            .order_by(TaskRecord.created_at.desc(), TaskRecord.id.desc())
            .all()
        )
