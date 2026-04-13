import json
from sqlalchemy.orm import Session
from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate
from app.services.title_service import build_fast_story_title
from app.services.cover_service import build_fallback_cover
from app.services.archive_story_service import generate_story_spec_and_state
from app.services.content_guard import evaluate_content
from app.services.rule_service import normalize_age_group


def _refresh_story_context(db: Session, story: Story) -> Story:
    content = (story.content or "").strip()
    if not content:
        story.summary = story.summary or ""
        story.target_age = normalize_age_group(story.age or 6)
        story.difficulty_level = story.difficulty_level or "L2"
        story.safety_status = story.safety_status or "passed"
        story.safety_tags = story.safety_tags or json.dumps([], ensure_ascii=False)
        db.commit()
        db.refresh(story)
        return story

    spec, state, summary = generate_story_spec_and_state(story.age or 6, content)
    difficulty = spec.get("difficulty_level", story.difficulty_level or "L2")
    guard = evaluate_content(story.age or 6, difficulty, content)

    story.summary = summary.get("summary_short", story.summary or "")
    story.story_spec = json.dumps(spec, ensure_ascii=False)
    story.story_state = json.dumps(state, ensure_ascii=False)
    story.story_summary = json.dumps(summary, ensure_ascii=False)
    story.target_age = normalize_age_group(story.age or 6)
    story.difficulty_level = difficulty
    story.safety_status = "passed" if guard.get("passed") else "rewrite_needed"
    story.safety_tags = json.dumps(guard.get("risk_tags", []), ensure_ascii=False)

    db.commit()
    db.refresh(story)
    return story


def create_story(db: Session, data: StoryCreate) -> Story:
    content = (data.content or "").strip()
    raw_title = (data.title or "").strip()

    title = raw_title or build_fast_story_title(content, fallback="我的新故事")
    title_source = "manual" if raw_title else "default"

    story = Story(
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

    return _refresh_story_context(db, story)


def get_story(db: Session, story_id: int):
    return db.query(Story).filter(Story.id == story_id).first()


def list_stories(db: Session):
    return db.query(Story).order_by(Story.created_at.desc()).all()


def update_story(db: Session, story_id: int, data: StoryUpdate):
    story = get_story(db, story_id)
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


def append_story_content(db: Session, story_id: int, story_text: str):
    story = get_story(db, story_id)
    if not story:
        return None

    if story.content and not story.content.endswith("\n"):
        story.content += "\n"
    story.content += story_text

    db.commit()
    db.refresh(story)
    return _refresh_story_context(db, story)
