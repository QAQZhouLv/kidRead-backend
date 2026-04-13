import json
from sqlalchemy.orm import Session

from app.models.story import Story
from app.models.story_session import StorySession
from app.schemas.chat import ChatRequest
from app.services.story_context_service import pack_context_for_prompt


def build_context_snapshot(req: ChatRequest) -> dict:
    return {
        "scene": req.scene,
        "story_id": req.story_id or 0,
        "has_story_spec": bool(req.story_spec),
        "has_story_state": bool(req.story_state),
        "has_story_summary": bool(req.story_summary),
        "current_story_length": len(req.current_story_content or ""),
        "session_draft_length": len(req.session_draft_content or ""),
    }


def enrich_chat_request_from_db(db: Session, req: ChatRequest) -> dict:
    if req.story_id:
        story = (
            db.query(Story)
            .filter(Story.id == req.story_id, Story.is_deleted == False)
            .first()
        )
        if story:
            ctx = pack_context_for_prompt(story)
            req.current_story_content = ctx["content"]
            req.story_spec = ctx["story_spec"]
            req.story_state = ctx["story_state"]
            req.story_summary = ctx["story_summary"]
            if not req.age:
                req.age = story.age or 6

    session = db.query(StorySession).filter(StorySession.session_id == req.session_id).first()
    if session:
        req.session_draft_content = session.draft_content or req.session_draft_content or ""

    return build_context_snapshot(req)


def update_session_context_snapshot(db: Session, session_id: str, snapshot: dict, guard_result: dict | None = None):
    session = db.query(StorySession).filter(StorySession.session_id == session_id).first()
    if not session:
        return None

    session.context_snapshot = json.dumps(snapshot, ensure_ascii=False)
    if guard_result is not None:
        session.last_guard_result = json.dumps(guard_result, ensure_ascii=False)

    db.commit()
    db.refresh(session)
    return session
