import json

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.user import User
from app.services.message_service import list_messages_by_session

router = APIRouter(prefix="/api/messages", tags=["messages"])



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_current_user_dep(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    return get_current_user(db=db, authorization=authorization)


@router.get("/session/{session_id}")
def get_messages_by_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    rows = list_messages_by_session(db, session_id, user_id=current_user.id)

    result = []
    for item in rows:
        choices = []
        if item.choices_json:
            try:
                choices = json.loads(item.choices_json)
            except Exception:
                choices = []

        result.append(
            {
                "id": item.id,
                "scene": item.scene,
                "story_id": item.story_id,
                "session_id": item.session_id,
                "role": item.role,
                "input_mode": item.input_mode,
                "intent": item.intent,
                "user_text": item.user_text,
                "lead_text": item.lead_text,
                "story_text": item.story_text,
                "guide_text": item.guide_text,
                "choices": choices,
                "should_save": item.should_save,
                "created_at": item.created_at,
            }
        )

    return result
