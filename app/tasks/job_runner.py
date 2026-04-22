from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.services.title_service import DEFAULT_SESSION_TITLES, generate_session_title
from app.tasks.job_names import AUTO_TITLE_SESSION, UPDATE_CONTEXT_SNAPSHOT


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


def handle_job(db: Session, job_name: str, payload: dict[str, Any]) -> None:
    if job_name == AUTO_TITLE_SESSION:
        _handle_auto_title_session(db, payload)
        return

    if job_name == UPDATE_CONTEXT_SNAPSHOT:
        _handle_update_context_snapshot(db, payload)
        return


def build_inline_handlers(db: Session) -> dict[str, Callable[[dict[str, Any]], None]]:
    return {
        AUTO_TITLE_SESSION: lambda payload: _handle_auto_title_session(db, payload),
        UPDATE_CONTEXT_SNAPSHOT: lambda payload: _handle_update_context_snapshot(db, payload),
    }
