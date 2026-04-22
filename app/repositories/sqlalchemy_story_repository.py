from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.story import Story
from app.repositories.story_repository import StoryRepository


class SQLAlchemyStoryRepository(StoryRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_story_for_prompt(self, story_id: int, *, user_id: int | None = None) -> Story | None:
        query = self.db.query(Story).filter(Story.id == story_id, Story.is_deleted == False)
        if user_id is not None:
            query = query.filter(Story.user_id == user_id)
        return query.first()

    def get_story_age(self, story_id: int, *, user_id: int | None = None) -> int | None:
        story = self.get_story_for_prompt(story_id, user_id=user_id)
        if not story:
            return None
        return story.age
