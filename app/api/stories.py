from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.story import StoryCreate, StoryOut, StoryUpdate, StoryAppendRequest
from app.services.story_service import (
    create_story,
    get_story,
    list_stories,
    update_story,
    append_story_content,
)

router = APIRouter(prefix="/api/stories", tags=["stories"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=list[StoryOut])
def get_story_list(db: Session = Depends(get_db)):
    return list_stories(db)

@router.post("", response_model=StoryOut)
def create_story_api(data: StoryCreate, db: Session = Depends(get_db)):
    return create_story(db, data)

@router.get("/{story_id}", response_model=StoryOut)
def get_story_api(story_id: int, db: Session = Depends(get_db)):
    story = get_story(db, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.put("/{story_id}", response_model=StoryOut)
def update_story_api(story_id: int, data: StoryUpdate, db: Session = Depends(get_db)):
    story = update_story(db, story_id, data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.post("/{story_id}/append", response_model=StoryOut)
def append_story_api(story_id: int, data: StoryAppendRequest, db: Session = Depends(get_db)):
    story = append_story_content(db, story_id, data.story_text)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story