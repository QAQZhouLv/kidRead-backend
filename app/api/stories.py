from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.story import Story

router = APIRouter(prefix="/api/stories", tags=["stories"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class StoryRenameRequest(BaseModel):
    title: str


class StoryFavoriteRequest(BaseModel):
    is_favorite: bool


def story_to_dict(story: Story):
    return {
        "id": story.id,
        "title": story.title,
        "age": story.age,
        "summary": story.summary,
        "content": story.content,
        "cover_image_url": story.cover_image_url,
        "fallback_cover_url": story.fallback_cover_url,
        "cover_status": story.cover_status,
        "cover_prompt": story.cover_prompt,
        "title_source": story.title_source,
        "is_favorite": bool(story.is_favorite),
        "is_deleted": bool(story.is_deleted),
        "deleted_at": story.deleted_at.isoformat() if story.deleted_at else None,
        "created_at": story.created_at.isoformat() if story.created_at else None,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


@router.get("")
def list_stories(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Story)

    if not include_deleted:
        query = query.filter(Story.is_deleted == False)

    stories = query.order_by(Story.updated_at.desc()).all()
    return [story_to_dict(s) for s in stories]


@router.get("/{story_id}")
def get_story(
    story_id: int,
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Story).filter(Story.id == story_id)

    if not include_deleted:
        query = query.filter(Story.is_deleted == False)

    story = query.first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return story_to_dict(story)


@router.patch("/{story_id}/rename")
def rename_story(story_id: int, payload: StoryRenameRequest, db: Session = Depends(get_db)):
    story = (
        db.query(Story)
        .filter(Story.id == story_id, Story.is_deleted == False)
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    new_title = (payload.title or "").strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    story.title = new_title
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)

    return {
        "ok": True,
        "id": story.id,
        "title": story.title,
    }


@router.patch("/{story_id}/favorite")
def update_story_favorite(story_id: int, payload: StoryFavoriteRequest, db: Session = Depends(get_db)):
    story = (
        db.query(Story)
        .filter(Story.id == story_id, Story.is_deleted == False)
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.is_favorite = bool(payload.is_favorite)
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)

    return {
        "ok": True,
        "id": story.id,
        "is_favorite": bool(story.is_favorite),
    }


@router.delete("/{story_id}")
def soft_delete_story(story_id: int, db: Session = Depends(get_db)):
    story = (
        db.query(Story)
        .filter(Story.id == story_id, Story.is_deleted == False)
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.is_deleted = True
    story.deleted_at = datetime.utcnow()
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)

    return {
        "ok": True,
        "id": story_id,
        "is_deleted": True,
        "deleted_at": story.deleted_at.isoformat() if story.deleted_at else None,
    }