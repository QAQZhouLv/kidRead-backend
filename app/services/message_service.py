import json

from sqlalchemy.orm import Session

from app.models.story_message import StoryMessage
from app.schemas.message import StoryMessageCreateAssistant, StoryMessageCreateUser



def create_user_message(db: Session, data: StoryMessageCreateUser, *, user_id: int) -> StoryMessage:
    msg = StoryMessage(
        user_id=user_id,
        scene=data.scene,
        story_id=data.story_id,
        session_id=data.session_id,
        role="user",
        input_mode=data.input_mode,
        user_text=data.user_text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg



def create_assistant_message(db: Session, data: StoryMessageCreateAssistant, *, user_id: int) -> StoryMessage:
    msg = StoryMessage(
        user_id=user_id,
        scene=data.scene,
        story_id=data.story_id,
        session_id=data.session_id,
        role="assistant",
        intent=data.intent,
        lead_text=data.lead_text,
        story_text=data.story_text,
        guide_text=data.guide_text,
        choices_json=json.dumps(data.choices, ensure_ascii=False),
        should_save=data.should_save,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg



def list_messages_by_session(db: Session, session_id: str, *, user_id: int):
    return (
        db.query(StoryMessage)
        .filter(
            StoryMessage.session_id == session_id,
            StoryMessage.user_id == user_id,
        )
        .order_by(StoryMessage.created_at.asc(), StoryMessage.id.asc())
        .all()
    )
