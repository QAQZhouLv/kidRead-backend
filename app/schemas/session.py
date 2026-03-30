from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

SessionScene = Literal["create", "bookchat"]


class StorySessionCreate(BaseModel):
    scene: SessionScene
    story_id: int = 0
    session_id: str
    title: str = "新对话"
    summary: Optional[str] = None


class StorySessionUpdateDraft(BaseModel):
    draft_content: str


class StorySessionRename(BaseModel):
    title: str


class StorySessionOut(BaseModel):
    id: int
    scene: SessionScene
    story_id: int
    session_id: str
    title: str
    summary: Optional[str] = None
    draft_content: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True