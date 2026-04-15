from datetime import datetime

from sqlalchemy.orm import Session

from app.models.story_session import StorySession
from app.schemas.session import StorySessionCreate
from app.services.title_service import DEFAULT_SESSION_TITLES, generate_session_title



def create_session(db: Session, data: StorySessionCreate, *, user_id: int) -> StorySession:
    session = StorySession(
        user_id=user_id,
        scene=data.scene,
        story_id=data.story_id,
        session_id=data.session_id,
        title=data.title,
        summary=data.summary,
        draft_content="",
        status="active",
        is_pinned=False,
        title_source="default",
        is_auto_titled=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session



def get_session_by_session_id(db: Session, session_id: str, *, user_id: int):
    return (
        db.query(StorySession)
        .filter(
            StorySession.session_id == session_id,
            StorySession.user_id == user_id,
        )
        .first()
    )



def list_sessions(db: Session, *, user_id: int, scene: str, story_id: int | None = None):
    query = db.query(StorySession).filter(
        StorySession.scene == scene,
        StorySession.user_id == user_id,
    )

    if scene == "bookchat":
        query = query.filter(StorySession.story_id == (story_id or 0))

    return query.order_by(
        StorySession.is_pinned.desc(),
        StorySession.pinned_at.desc().nullslast(),
        StorySession.updated_at.desc(),
    ).all()



def update_session_draft(db: Session, session_id: str, draft_content: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    session.draft_content = draft_content
    db.commit()
    db.refresh(session)
    return session



def rename_session(db: Session, session_id: str, title: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    clean = (title or "").strip()
    if clean:
        session.title = clean
        session.title_source = "manual"

    db.commit()
    db.refresh(session)
    return session



def pin_session(db: Session, session_id: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    session.is_pinned = True
    session.pinned_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session



def unpin_session(db: Session, session_id: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    session.is_pinned = False
    session.pinned_at = None
    db.commit()
    db.refresh(session)
    return session



def delete_session(db: Session, session_id: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    db.delete(session)
    db.commit()
    return True



def clear_session_draft(db: Session, session_id: str, *, user_id: int):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    session.draft_content = ""
    session.status = "merged"
    db.commit()
    db.refresh(session)
    return session



def auto_title_session_if_needed(
    db: Session,
    *,
    user_id: int,
    session_id: str,
    user_text: str,
    assistant_text: str,
):
    session = get_session_by_session_id(db, session_id, user_id=user_id)
    if not session:
        return None

    if session.title_source == "manual":
        return session

    current_title = (session.title or "").strip()
    if current_title not in DEFAULT_SESSION_TITLES and session.is_auto_titled:
        return session

    new_title = generate_session_title(
        scene=session.scene,
        user_text=user_text,
        assistant_text=assistant_text,
        fallback=current_title or "新对话",
    )

    if new_title:
        session.title = new_title
        session.title_source = "auto"
        session.is_auto_titled = True
        db.commit()
        db.refresh(session)

    return session
