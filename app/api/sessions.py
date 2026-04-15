from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.session import StorySessionCreate, StorySessionOut, StorySessionRename, StorySessionUpdateDraft
from app.services.session_service import (
    clear_session_draft,
    create_session,
    delete_session,
    get_session_by_session_id,
    list_sessions,
    pin_session,
    rename_session,
    unpin_session,
    update_session_draft,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])



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


@router.post("", response_model=StorySessionOut)
def create_session_api(
    data: StorySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    existing = get_session_by_session_id(db, data.session_id, user_id=current_user.id)
    if existing:
        return existing
    return create_session(db, data, user_id=current_user.id)


@router.get("", response_model=list[StorySessionOut])
def list_sessions_api(
    scene: str = Query(..., description="create or bookchat"),
    story_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    return list_sessions(db, user_id=current_user.id, scene=scene, story_id=story_id)


@router.get("/{session_id}", response_model=StorySessionOut)
def get_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = get_session_by_session_id(db, session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/draft", response_model=StorySessionOut)
def update_session_draft_api(
    session_id: str,
    data: StorySessionUpdateDraft,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = update_session_draft(db, session_id, data.draft_content, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/rename", response_model=StorySessionOut)
def rename_session_api(
    session_id: str,
    data: StorySessionRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = rename_session(db, session_id, data.title, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/pin", response_model=StorySessionOut)
def pin_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = pin_session(db, session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/unpin", response_model=StorySessionOut)
def unpin_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = unpin_session(db, session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    ok = delete_session(db, session_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.post("/{session_id}/merge", response_model=StorySessionOut)
def merge_session_api(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    session = clear_session_draft(db, session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
