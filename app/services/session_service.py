from sqlalchemy.orm import Session
from app.models.story_session import StorySession
from app.schemas.session import StorySessionCreate


def create_session(db: Session, data: StorySessionCreate) -> StorySession:
    session = StorySession(
        scene=data.scene,
        story_id=data.story_id,
        session_id=data.session_id,
        title=data.title,
        summary=data.summary,
        draft_content="",
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_session_id(db: Session, session_id: str):
    return db.query(StorySession).filter(StorySession.session_id == session_id).first()


def list_sessions(
    db: Session,
    scene: str,
    story_id: int | None = None,
):
    query = db.query(StorySession).filter(StorySession.scene == scene)

    if scene == "bookchat":
        query = query.filter(StorySession.story_id == (story_id or 0))

    return query.order_by(StorySession.updated_at.desc()).all()


def update_session_draft(
    db: Session,
    session_id: str,
    draft_content: str,
):
    session = get_session_by_session_id(db, session_id)
    if not session:
        return None

    session.draft_content = draft_content
    db.commit()
    db.refresh(session)
    return session


def rename_session(db: Session, session_id: str, title: str):
    session = get_session_by_session_id(db, session_id)
    if not session:
        return None

    session.title = title.strip() or session.title
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: str):
    session = get_session_by_session_id(db, session_id)
    if not session:
        return None

    db.delete(session)
    db.commit()
    return True


def clear_session_draft(db: Session, session_id: str):
    session = get_session_by_session_id(db, session_id)
    if not session:
        return None

    session.draft_content = ""
    session.status = "merged"
    db.commit()
    db.refresh(session)
    return session