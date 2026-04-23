import json

from sqlalchemy.orm import Session

from app.models.story import Story
from app.models.story_message import StoryMessage
from app.models.story_session import StorySession
from app.schemas.chat import ChatRequest, HistoryMessage
from app.services.story_context_service import pack_context_for_prompt

try:
    from app.core.runtime import build_runtime
except Exception:  # pragma: no cover
    build_runtime = None


def build_context_snapshot(req: ChatRequest) -> dict:
    summary = req.story_summary or {}
    return {
        "scene": req.scene,
        "story_id": req.story_id or 0,
        "history_count": len(req.history or []),
        "has_story_spec": bool(req.story_spec),
        "has_story_state": bool(req.story_state),
        "has_story_summary": bool(req.story_summary),
        "current_story_length": len(req.current_story_content or ""),
        "session_draft_length": len(req.session_draft_content or ""),
        "context_mode": summary.get("_context_mode", "full") if isinstance(summary, dict) else "full",
        "full_story_length": summary.get("_full_content_length", 0) if isinstance(summary, dict) else 0,
        "selected_story_length": summary.get("_selected_content_length", len(req.current_story_content or "")) if isinstance(summary, dict) else len(req.current_story_content or ""),
        "context_hit_count": summary.get("_hit_count", 0) if isinstance(summary, dict) else 0,
        "vector_retrieval_enabled": bool(summary.get("_context_mode") == "fast") if isinstance(summary, dict) else False,
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
    if build_runtime is not None:
        try:
            runtime = build_runtime(db)
            rows = runtime.message_repo.list_recent_history(req.session_id, user_id=user_id, limit=limit)
            history = [_to_history_message(row) for row in rows]
            if history:
                last = history[-1]
                if last.role == "user" and (last.text or "").strip() == (req.text or "").strip():
                    history = history[:-1]
            return history
        except Exception:
            pass

    query = db.query(StoryMessage).filter(StoryMessage.session_id == req.session_id)
    if user_id is not None:
        query = query.filter(StoryMessage.user_id == user_id)

    rows = query.order_by(StoryMessage.created_at.desc(), StoryMessage.id.desc()).limit(limit + 1).all()
    rows.reverse()
    history = [_to_history_message(row) for row in rows]
    if history:
        last = history[-1]
        if last.role == "user" and (last.text or "").strip() == (req.text or "").strip():
            history = history[:-1]
    return history


def enrich_chat_request_from_db(db: Session, req: ChatRequest, user_id: int | None = None) -> dict:
    use_fast_context = False
    use_vector_retrieval = False
    story = None
    session = None
    retrieved_chunks: list[str] = []

    if build_runtime is not None:
        try:
            runtime = build_runtime(db)
            use_fast_context = bool(getattr(runtime.flags, "use_fast_context", False))
            use_vector_retrieval = bool(getattr(runtime.flags, "use_vector_retrieval", False))
            if req.story_id:
                story = runtime.story_repo.get_story_for_prompt(req.story_id, user_id=user_id)
                if story and use_fast_context and use_vector_retrieval:
                    retrieved_chunks = runtime.vector_store.search_story_chunks(
                        story_id=req.story_id,
                        query_text=req.text or "",
                        full_content=getattr(story, "content", "") or "",
                        top_k=3,
                    )
            session = runtime.session_repo.get_by_session_id(req.session_id, user_id=user_id)
        except Exception:
            story = None
            session = None
            retrieved_chunks = []

    if req.story_id and story is None:
        query = db.query(Story).filter(Story.id == req.story_id, Story.is_deleted == False)
        if user_id is not None:
            query = query.filter(Story.user_id == user_id)
        story = query.first()

    if story:
        ctx = pack_context_for_prompt(
            story,
            use_fast_context=use_fast_context,
            query_text=req.text or "",
            retrieved_chunks=retrieved_chunks,
        )
        req.current_story_content = ctx["content"]
        req.story_spec = ctx["story_spec"]
        req.story_state = ctx["story_state"]
        req.story_summary = ctx["story_summary"]
        if not req.age:
            req.age = story.age or 6

    if session is None:
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
    if build_runtime is not None:
        try:
            runtime = build_runtime(db)
            return runtime.session_repo.update_context_snapshot(
                session_id=session_id,
                snapshot=snapshot,
                guard_result=guard_result,
                user_id=user_id,
            )
        except Exception:
            pass

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
