from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StoryCreate(BaseModel):
    title: str
    age: int = 6
    summary: Optional[str] = None
    content: str = ""

class StoryUpdate(BaseModel):
    title: Optional[str] = None
    age: Optional[int] = None
    summary: Optional[str] = None
    content: Optional[str] = None

class StoryAppendRequest(BaseModel):
    story_text: str

class StoryOut(BaseModel):
    id: int
    title: str
    age: int
    summary: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True