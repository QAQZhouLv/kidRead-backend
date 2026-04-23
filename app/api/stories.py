from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.runtime import build_runtime
from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.story import Story
from app.models.user import User
from app.schemas.story import StoryAppendRequest, StoryCreate
from app.services.cover_service import finalize_story_assets
from app.services.story_service import (
    append_story_content,
    create_story as service_create_story,
    get_story as service_get_story,
)
from app.services.story_vector_sync_service import (
    delete_story_vectors_task,
    sync_story_vectors_task,
)
from app.tasks.job_names import (
    DELETE_STORY_VECTORS,
    FINALIZE_STORY_ASSETS,
    SYNC_STORY_VECTORS,
)

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
        "user_id": story.user_id,
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


def get_current_user_dep(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    return get_current_user(db=db, authorization=authorization)


def _build_vector_payload(story: Story) -> dict:
    return {
        "story_id": story.id,
        "content": story.content or "",
    }


def _enqueue_story_side_effects(runtime, story: Story) -> None:
    payload = {"story_id": story.id}
    runtime.task_queue.enqueue(FINALIZE_STORY_ASSETS, payload)
    runtime.task_queue.enqueue(SYNC_STORY_VECTORS, _build_vector_payload(story))


def _background_story_side_effects(background_tasks: BackgroundTasks, story: Story) -> None:
    background_tasks.add_task(finalize_story_assets, story.id)
    background_tasks.add_task(sync_story_vectors_task, story.id)


def _enqueue_story_delete_side_effects(runtime, story_id: int) -> None:
    runtime.task_queue.enqueue(DELETE_STORY_VECTORS, {"story_id": story_id})


def _background_story_delete_side_effects(background_tasks: BackgroundTasks, story_id: int) -> None:
    background_tasks.add_task(delete_story_vectors_task, story_id)


@router.get("")
def list_stories(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    query = db.query(Story).filter(Story.user_id == current_user.id)
    if not include_deleted:
        query = query.filter(Story.is_deleted == False)
    stories = query.order_by(Story.updated_at.desc()).all()
    return [story_to_dict(s) for s in stories]


@router.get("/{story_id}")
def get_story(
    story_id: int,
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    query = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id,
    )
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    story = service_create_story(db, data, user_id=current_user.id)
    runtime = build_runtime(db)

    if runtime.flags.use_async_side_effects:
        _enqueue_story_side_effects(runtime, story)
    else:
        _background_story_side_effects(background_tasks, story)

    return story_to_dict(story)


@router.post("/{story_id}/append")
def append_story_api(
    story_id: int,
    data: StoryAppendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    story_text = (data.story_text or "").strip()
    if not story_text:
        raise HTTPException(status_code=400, detail="story_text cannot be empty")

    story = service_get_story(db, story_id, user_id=current_user.id)
    if not story or story.is_deleted:
        raise HTTPException(status_code=404, detail="Story not found")

    story = append_story_content(db, story_id, story_text, user_id=current_user.id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    runtime = build_runtime(db)
    if runtime.flags.use_async_side_effects:
        _enqueue_story_side_effects(runtime, story)
    else:
        _background_story_side_effects(background_tasks, story)

    return story_to_dict(story)


@router.patch("/{story_id}/rename")
def rename_story(
    story_id: int,
    payload: StoryRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.user_id == current_user.id,
            Story.is_deleted == False,
        )
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
    return {"ok": True, "id": story.id, "title": story.title}


@router.patch("/{story_id}/favorite")
def update_story_favorite(
    story_id: int,
    payload: StoryFavoriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.user_id == current_user.id,
            Story.is_deleted == False,
        )
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.is_favorite = bool(payload.is_favorite)
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)
    return {"ok": True, "id": story.id, "is_favorite": bool(story.is_favorite)}


@router.delete("/{story_id}")
def soft_delete_story(
    story_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    story = (
        db.query(Story)
        .filter(
            Story.id == story_id,
            Story.user_id == current_user.id,
            Story.is_deleted == False,
        )
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.is_deleted = True
    story.deleted_at = datetime.utcnow()
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)

    runtime = build_runtime(db)
    if runtime.flags.use_async_side_effects:
        _enqueue_story_delete_side_effects(runtime, story_id)
    else:
        _background_story_delete_side_effects(background_tasks, story_id)

    return {
        "ok": True,
        "id": story_id,
        "is_deleted": True,
        "deleted_at": story.deleted_at.isoformat() if story.deleted_at else None,
    }
