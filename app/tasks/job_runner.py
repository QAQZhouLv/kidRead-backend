from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.runtime import build_runtime
from app.repositories.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.services.cover_service import finalize_story_assets
from app.services.story_vector_sync_service import (
    delete_story_from_vector_store,
    sync_story_content_to_vector_store,
)
from app.services.title_service import DEFAULT_SESSION_TITLES, generate_session_title
from app.tasks.job_names import (
    AUTO_TITLE_SESSION,
    DELETE_STORY_VECTORS,
    FINALIZE_STORY_ASSETS,
    SYNC_STORY_VECTORS,
    UPDATE_CONTEXT_SNAPSHOT,
)


def _handle_auto_title_session(db: Session, payload: dict[str, Any]) -> None:
    user_id = payload.get("user_id")
    session_id = payload.get("session_id") or ""
    user_text = payload.get("user_text") or ""
    assistant_text = payload.get("assistant_text") or ""

    repo = SQLAlchemySessionRepository(db)
    session = repo.get_by_session_id(session_id, user_id=user_id)
    if not session:
        return
    if session.title_source == "manual":
        return

    current_title = (session.title or "").strip()
    if current_title not in DEFAULT_SESSION_TITLES and session.is_auto_titled:
        return

    new_title = generate_session_title(
        scene=session.scene,
        user_text=user_text,
        assistant_text=assistant_text,
        fallback=current_title or "新对话",
    )
    if not new_title:
        return

    session.title = new_title
    session.title_source = "auto"
    session.is_auto_titled = True
    db.commit()
    db.refresh(session)


def _handle_update_context_snapshot(db: Session, payload: dict[str, Any]) -> None:
    repo = SQLAlchemySessionRepository(db)
    repo.update_context_snapshot(
        session_id=payload.get("session_id") or "",
        snapshot=payload.get("snapshot") or {},
        guard_result=payload.get("guard_result"),
        user_id=payload.get("user_id"),
    )


def _handle_finalize_story_assets(_: Session, payload: dict[str, Any]) -> None:
    story_id = int(payload.get("story_id") or 0)
    if story_id <= 0:
        return
    finalize_story_assets(story_id)


def _handle_sync_story_vectors(db: Session, payload: dict[str, Any]) -> None:
    story_id = int(payload.get("story_id") or 0)
    content = payload.get("content") or ""
    if story_id <= 0:
        return
    runtime = build_runtime(db)
    sync_story_content_to_vector_store(
        runtime.vector_store,
        story_id=story_id,
        content=content,
    )


def _handle_delete_story_vectors(db: Session, payload: dict[str, Any]) -> None:
    story_id = int(payload.get("story_id") or 0)
    if story_id <= 0:
        return
    runtime = build_runtime(db)
    delete_story_from_vector_store(runtime.vector_store, story_id=story_id)


def handle_job(db: Session, job_name: str, payload: dict[str, Any]) -> None:
    if job_name == AUTO_TITLE_SESSION:
        _handle_auto_title_session(db, payload)
        return
    if job_name == UPDATE_CONTEXT_SNAPSHOT:
        _handle_update_context_snapshot(db, payload)
        return
    if job_name == FINALIZE_STORY_ASSETS:
        _handle_finalize_story_assets(db, payload)
        return
    if job_name == SYNC_STORY_VECTORS:
        _handle_sync_story_vectors(db, payload)
        return
    if job_name == DELETE_STORY_VECTORS:
        _handle_delete_story_vectors(db, payload)
        return


def build_inline_handlers(db: Session) -> dict[str, Callable[[dict[str, Any]], None]]:
    return {
        AUTO_TITLE_SESSION: lambda payload: _handle_auto_title_session(db, payload),
        UPDATE_CONTEXT_SNAPSHOT: lambda payload: _handle_update_context_snapshot(db, payload),
        FINALIZE_STORY_ASSETS: lambda payload: _handle_finalize_story_assets(db, payload),
        SYNC_STORY_VECTORS: lambda payload: _handle_sync_story_vectors(db, payload),
        DELETE_STORY_VECTORS: lambda payload: _handle_delete_story_vectors(db, payload),
    }
