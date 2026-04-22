from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.story_message import StoryMessage
from app.repositories.message_repository import MessageRepository


class SQLAlchemyMessageRepository(MessageRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_user_message(
        self,
        *,
        user_id: int,
        scene: str,
        story_id: int,
        session_id: str,
        input_mode: str,
        user_text: str,
    ) -> StoryMessage:
        msg = StoryMessage(
            user_id=user_id,
            scene=scene,
            story_id=story_id,
            session_id=session_id,
            role="user",
            input_mode=input_mode,
            user_text=user_text,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def create_assistant_message(
        self,
        *,
        user_id: int,
        scene: str,
        story_id: int,
        session_id: str,
        intent: str,
        lead_text: str,
        story_text: str,
        guide_text: str,
        choices: list[str],
        should_save: bool,
    ) -> StoryMessage:
        msg = StoryMessage(
            user_id=user_id,
            scene=scene,
            story_id=story_id,
            session_id=session_id,
            role="assistant",
            intent=intent,
            lead_text=lead_text,
            story_text=story_text,
            guide_text=guide_text,
            choices_json=json.dumps(choices, ensure_ascii=False),
            should_save=should_save,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def list_recent_history(self, session_id: str, *, user_id: int | None = None, limit: int = 10) -> list[StoryMessage]:
        query = self.db.query(StoryMessage).filter(StoryMessage.session_id == session_id)
        if user_id is not None:
            query = query.filter(StoryMessage.user_id == user_id)
        rows = query.order_by(StoryMessage.created_at.desc(), StoryMessage.id.desc()).limit(limit + 1).all()
        rows.reverse()
        return rows
