import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.story import Story
from app.models.story_message import StoryMessage
from app.models.story_session import StorySession
from app.schemas.chat import ChatRequest, HistoryMessage
from app.services.story_context_service import pack_context_for_prompt


def build_context_snapshot(req: ChatRequest) -> dict:
    return {
        "scene": req.scene,
        "story_id": req.story_id or 0,
        "history_count": len(req.history or []),
        "has_story_spec": bool(req.story_spec),
        "has_story_state": bool(req.story_state),
        "has_story_summary": bool(req.story_summary),
        "current_story_length": len(req.current_story_content or ""),
        "session_draft_length": len(req.session_draft_content or ""),
    }


def _to_history_message(row: StoryMessage) -> HistoryMessage:
    choices = []
    if row.choices_json:
        try:
            choices = json.loads(row.choices_json)
        except Exception:
            choices = []
    return HistoryMessage(
        role=row.role,
        text=row.user_text or "",
        lead_text=row.lead_text or "",
        story_text=row.story_text or "",
        guide_text=row.guide_text or "",
        choices=choices,
    )


def _load_recent_history(db: Session, req: ChatRequest, user_id: int | None = None, limit: int = 10) -> list[HistoryMessage]:
    query = db.query(StoryMessage).filter(StoryMessage.session_id == req.session_id)
    if user_id is not None:
        query = query.filter(StoryMessage.user_id == user_id)

    rows = query.order_by(StoryMessage.created_at.desc(), StoryMessage.id.desc()).limit(limit + 1).all()
    rows.reverse()
    history = [_to_history_message(row) for row in rows]

    # chat 接口在主链里会先落一条当前 user message，避免把当前输入重复放入 history
    if history:
        last = history[-1]
        if last.role == "user" and (last.text or "").strip() == (req.text or "").strip():
            history = history[:-1]
    return history


def enrich_chat_request_from_db(db: Session, req: ChatRequest, user_id: int | None = None) -> dict:
    if req.story_id:
        query = db.query(Story).filter(Story.id == req.story_id, Story.is_deleted == False)
        if user_id is not None:
            query = query.filter(Story.user_id == user_id)
        story = query.first()
        if story:
            ctx = pack_context_for_prompt(story)
            req.current_story_content = ctx["content"]
            req.story_spec = ctx["story_spec"]
            req.story_state = ctx["story_state"]
            req.story_summary = ctx["story_summary"]
            if not req.age:
                req.age = story.age or 6

    session_query = db.query(StorySession).filter(StorySession.session_id == req.session_id)
    if user_id is not None:
        session_query = session_query.filter(StorySession.user_id == user_id)
    session = session_query.first()
    if session:
        req.session_draft_content = session.draft_content or ""

    db_history = _load_recent_history(db, req=req, user_id=user_id)
    if db_history:
        req.history = db_history

    return build_context_snapshot(req)


def update_session_context_snapshot(
    db: Session,
    session_id: str,
    snapshot: dict,
    guard_result: dict | None = None,
    *,
    user_id: int | None = None,
):
    query = db.query(StorySession).filter(StorySession.session_id == session_id)
    if user_id is not None:
        query = query.filter(StorySession.user_id == user_id)

    session = query.first()
    if not session:
        return None

    session.context_snapshot = json.dumps(snapshot or {}, ensure_ascii=False)
    if guard_result is not None:
        session.last_guard_result = json.dumps(guard_result, ensure_ascii=False)

    db.commit()
    db.refresh(session)
    return session
