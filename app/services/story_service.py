from sqlalchemy.orm import Session

from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate
from app.services.rule_service import normalize_age_group
from app.services.title_service import build_fast_story_title


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
        target_age=normalize_age_group(data.age or 6),
        difficulty_level="L2",
        safety_status="passed",
    )
    db.add(story)
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
        "story_spec", "story_state", "story_summary",
        "target_age", "difficulty_level", "safety_status", "safety_tags",
        "cover_image_url", "fallback_cover_url", "cover_status",
        "cover_prompt", "title_source",
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

    clean_story_text = (story_text or "").strip()
    if not clean_story_text:
        return story

    if story.content and not story.content.endswith("\n"):
        story.content += "\n"
    story.content += clean_story_text

    db.commit()
    db.refresh(story)
    return story
