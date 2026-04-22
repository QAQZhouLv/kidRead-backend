from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.story_session import StorySession
from app.repositories.session_repository import SessionRepository


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_session_id(self, session_id: str, *, user_id: int | None = None) -> StorySession | None:
        query = self.db.query(StorySession).filter(StorySession.session_id == session_id)
        if user_id is not None:
            query = query.filter(StorySession.user_id == user_id)
        return query.first()

    def update_context_snapshot(
        self,
        session_id: str,
        snapshot: dict,
        guard_result: dict | None = None,
        *,
        user_id: int | None = None,
    ) -> StorySession | None:
        session = self.get_by_session_id(session_id, user_id=user_id)
        if not session:
            return None

        session.context_snapshot = json.dumps(snapshot or {}, ensure_ascii=False)
        if guard_result is not None:
            session.last_guard_result = json.dumps(guard_result, ensure_ascii=False)

        self.db.commit()
        self.db.refresh(session)
        return session

    def update_draft(self, session_id: str, draft_content: str, *, user_id: int | None = None) -> StorySession | None:
        session = self.get_by_session_id(session_id, user_id=user_id)
        if not session:
            return None

        session.draft_content = draft_content
        self.db.commit()
        self.db.refresh(session)
        return session
