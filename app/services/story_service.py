from sqlalchemy.orm import Session
from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate

def create_story(db: Session, data: StoryCreate) -> Story:
    story = Story(
        title=data.title,
        age=data.age,
        summary=data.summary,
        content=data.content,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story

def get_story(db: Session, story_id: int):
    return db.query(Story).filter(Story.id == story_id).first()

def list_stories(db: Session):
    return db.query(Story).order_by(Story.created_at.desc()).all()

def update_story(db: Session, story_id: int, data: StoryUpdate):
    story = get_story(db, story_id)
    if not story:
        return None

    if data.title is not None:
        story.title = data.title
    if data.age is not None:
        story.age = data.age
    if data.summary is not None:
        story.summary = data.summary
    if data.content is not None:
        story.content = data.content

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
    return story