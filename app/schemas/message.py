from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

MessageRole = Literal["user", "assistant"]
MessageScene = Literal["create", "bookchat"]


class StoryMessageCreateUser(BaseModel):
    scene: MessageScene
    story_id: int = 0
    session_id: str
    role: Literal["user"] = "user"
    input_mode: Optional[str] = None
    user_text: str


class StoryMessageCreateAssistant(BaseModel):
    scene: MessageScene
    story_id: int = 0
    session_id: str
    role: Literal["assistant"] = "assistant"
    intent: str
    lead_text: str = ""
    story_text: str = ""
    guide_text: str = ""
    choices: List[str] = []
    should_save: bool = False


class StoryMessageOut(BaseModel):
    id: int
    scene: MessageScene
    story_id: int
    session_id: str
    role: MessageRole
    input_mode: Optional[str] = None
    intent: Optional[str] = None
    user_text: Optional[str] = None
    lead_text: Optional[str] = None
    story_text: Optional[str] = None
    guide_text: Optional[str] = None
    choices: List[str] = []
    should_save: bool = False
    created_at: datetime

    class Config:
        from_attributes = True