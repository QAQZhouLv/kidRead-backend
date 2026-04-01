from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StoryCreate(BaseModel):
    title: Optional[str] = None
    age: int = 6
    summary: Optional[str] = None
    content: str = ""


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    age: Optional[int] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[str] = None
    fallback_cover_url: Optional[str] = None
    cover_status: Optional[str] = None
    cover_prompt: Optional[str] = None
    title_source: Optional[str] = None


class StoryAppendRequest(BaseModel):
    story_text: str


class StoryOut(BaseModel):
    id: int
    title: str
    age: int
    summary: Optional[str] = None
    content: str

    cover_image_url: Optional[str] = None
    fallback_cover_url: Optional[str] = None
    cover_status: str
    cover_prompt: Optional[str] = None
    title_source: str

    created_at: datetime
    updated_at: datetime

    @property
    def display_cover_url(self):
        return self.cover_image_url or self.fallback_cover_url

    class Config:
        from_attributes = True