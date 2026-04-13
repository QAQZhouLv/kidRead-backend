from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.story import Story
from app.schemas.story import StoryCreate, StoryAppendRequest
from app.services.story_service import (
    create_story as service_create_story,
    get_story as service_get_story,
    append_story_content,
)
from app.services.cover_service import finalize_story_assets

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
        "story_spec": story.story_spec,
        "story_state": story.story_state,
        "story_summary": story.story_summary,
        "target_age": story.target_age,
        "difficulty_level": story.difficulty_level,
        "safety_status": story.safety_status,
        "safety_tags": story.safety_tags,
        "cover_image_url": story.cover_image_url,
        "fallback_cover_url": story.fallback_cover_url,
        "display_cover_url": story.cover_image_url or story.fallback_cover_url,
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


@router.post("")
def create_story_api(
    data: StoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    story = service_create_story(db, data)
    background_tasks.add_task(finalize_story_assets, story.id)
    return story_to_dict(story)


@router.post("/{story_id}/append")
def append_story_api(
    story_id: int,
    data: StoryAppendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    story_text = (data.story_text or "").strip()
    if not story_text:
        raise HTTPException(status_code=400, detail="story_text cannot be empty")

    story = service_get_story(db, story_id)
    if not story or story.is_deleted:
        raise HTTPException(status_code=404, detail="Story not found")

    story = append_story_content(db, story_id, story_text)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    background_tasks.add_task(finalize_story_assets, story.id)
    return story_to_dict(story)


@router.patch("/{story_id}/rename")
def rename_story(
    story_id: int,
    payload: StoryRenameRequest,
    db: Session = Depends(get_db)
):
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
    story.title_source = "manual"
    story.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(story)

    return {
        "ok": True,
        "id": story.id,
        "title": story.title,
    }


@router.patch("/{story_id}/favorite")
def update_story_favorite(
    story_id: int,
    payload: StoryFavoriteRequest,
    db: Session = Depends(get_db)
):
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
