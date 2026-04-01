from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.session import (
    StorySessionCreate,
    StorySessionUpdateDraft,
    StorySessionRename,
    StorySessionOut,
)
from app.services.session_service import (
    create_session,
    get_session_by_session_id,
    list_sessions,
    update_session_draft,
    rename_session,
    delete_session,
    clear_session_draft,
    pin_session,
    unpin_session,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=StorySessionOut)
def create_session_api(data: StorySessionCreate, db: Session = Depends(get_db)):
    existing = get_session_by_session_id(db, data.session_id)
    if existing:
        return existing
    return create_session(db, data)


@router.get("", response_model=list[StorySessionOut])
def list_sessions_api(
    scene: str = Query(..., description="create or bookchat"),
    story_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return list_sessions(db, scene=scene, story_id=story_id)


@router.get("/{session_id}", response_model=StorySessionOut)
def get_session_api(session_id: str, db: Session = Depends(get_db)):
    session = get_session_by_session_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/draft", response_model=StorySessionOut)
def update_session_draft_api(session_id: str, data: StorySessionUpdateDraft, db: Session = Depends(get_db)):
    session = update_session_draft(db, session_id, data.draft_content)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}/rename", response_model=StorySessionOut)
def rename_session_api(session_id: str, data: StorySessionRename, db: Session = Depends(get_db)):
    session = rename_session(db, session_id, data.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/pin", response_model=StorySessionOut)
def pin_session_api(session_id: str, db: Session = Depends(get_db)):
    session = pin_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/unpin", response_model=StorySessionOut)
def unpin_session_api(session_id: str, db: Session = Depends(get_db)):
    session = unpin_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session_api(session_id: str, db: Session = Depends(get_db)):
    ok = delete_session(db, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.post("/{session_id}/merge", response_model=StorySessionOut)
def merge_session_api(session_id: str, db: Session = Depends(get_db)):
    session = clear_session_draft(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session