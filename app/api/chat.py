from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.message import (
    StoryMessageCreateUser,
    StoryMessageCreateAssistant,
)
from app.services.chat_service import generate_chat_response
from app.services.message_service import (
    create_user_message,
    create_assistant_message,
)
from app.services.chat_context_service import (
    enrich_chat_request_from_db,
    update_session_context_snapshot,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/unified", response_model=ChatResponse)
def unified_chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        create_user_message(
            db,
            StoryMessageCreateUser(
                scene=req.scene,
                story_id=req.story_id or 0,
                session_id=req.session_id,
                input_mode=req.input_mode,
                user_text=req.text,
            )
        )

        snapshot = enrich_chat_request_from_db(db, req)
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
            )
        )

        guard_result = getattr(result, "_guard_result", None)
        update_session_context_snapshot(db, req.session_id, snapshot, guard_result)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
