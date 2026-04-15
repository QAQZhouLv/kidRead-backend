from sqlalchemy.orm import Session

from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate
from app.services.title_service import build_fast_story_title
from app.services.cover_service import build_fallback_cover



def create_story(db: Session, data: StoryCreate, *, user_id: int) -> Story:
    content = (data.content or "").strip()
    raw_title = (data.title or "").strip()

    title = raw_title or build_fast_story_title(content, fallback="我的新故事")
    title_source = "manual" if raw_title else "default"

    story = Story(
        user_id=user_id,
        title=title,
        age=data.age,
        summary=data.summary,
        content=content,
        title_source=title_source,
        cover_status="fallback",
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    fallback_cover_url = build_fallback_cover(story)
    story.fallback_cover_url = fallback_cover_url
    db.commit()
    db.refresh(story)
    return story



def get_story(db: Session, story_id: int, *, user_id: int):
    return (
        db.query(Story)
        .filter(Story.id == story_id, Story.user_id == user_id)
        .first()
    )



def list_stories(db: Session, *, user_id: int):
    return (
        db.query(Story)
        .filter(Story.user_id == user_id)
        .order_by(Story.created_at.desc())
        .all()
    )



def update_story(db: Session, story_id: int, data: StoryUpdate, *, user_id: int):
    story = get_story(db, story_id, user_id=user_id)
    if not story:
        return None

    for field in [
        "title", "age", "summary", "content",
        "cover_image_url", "fallback_cover_url", "cover_status",
        "cover_prompt", "title_source"
    ]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(story, field, value)

    db.commit()
    db.refresh(story)
    return story



def append_story_content(db: Session, story_id: int, story_text: str, *, user_id: int):
    story = get_story(db, story_id, user_id=user_id)
    if not story:
        return None

    if story.content and not story.content.endswith("\n"):
        story.content += "\n"
    story.content += story_text

    db.commit()
    db.refresh(story)
    return story
