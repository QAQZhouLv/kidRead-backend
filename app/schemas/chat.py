from pydantic import BaseModel, Field
from typing import List, Optional, Literal

IntentType = Literal[
    "create_story",
    "continue_story",
    "ask_about_story",
    "adjust_story",
    "unsafety",
    "end_chat",
]

class HistoryMessage(BaseModel):
    role: str
    text: Optional[str] = None
    lead_text: Optional[str] = None
    story_text: Optional[str] = None
    guide_text: Optional[str] = None
    choices: List[str] = []

class ChatRequest(BaseModel):
    scene: Literal["create", "bookchat"]
    story_id: Optional[int] = None
    session_id: str
    age: int
    input_mode: Literal["text", "voice", "choice"] = "text"
    text: str
    history: List[HistoryMessage] = []

    current_story_content: str = ""
    session_draft_content: str = ""

class ChatResponse(BaseModel):
    intent: IntentType
    lead_text: str = Field(default="")
    story_text: str = Field(default="")
    guide_text: str = Field(default="")
    choices: List[str] = Field(default_factory=list)
    should_save: bool = False
    save_mode: str = "append"