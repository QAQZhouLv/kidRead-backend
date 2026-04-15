from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import StoryMessageCreateAssistant, StoryMessageCreateUser
from app.services.chat_service import generate_chat_response
from app.services.message_service import create_assistant_message, create_user_message

router = APIRouter(prefix="/api/chat", tags=["chat"])



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


@router.post("/unified", response_model=ChatResponse)
def unified_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    try:
        create_user_message(
            db,
            StoryMessageCreateUser(
                scene=req.scene,
                story_id=req.story_id or 0,
                session_id=req.session_id,
                input_mode=req.input_mode,
                user_text=req.text,
            ),
            user_id=current_user.id,
        )

        result = generate_chat_response(req)

        create_assistant_message(
            db,
            StoryMessageCreateAssistant(
                scene=req.scene,
                story_id=req.story_id or 0,
                session_id=req.session_id,
                intent=result.intent,
                lead_text=result.lead_text,
                story_text=result.story_text,
                guide_text=result.guide_text,
                choices=result.choices,
                should_save=result.should_save,
            ),
            user_id=current_user.id,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
