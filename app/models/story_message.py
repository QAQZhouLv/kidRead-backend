from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.db.base import Base


class StoryMessage(Base):
    __tablename__ = "story_messages"

    id = Column(Integer, primary_key=True, index=True)

    scene = Column(String(50), nullable=False, index=True, default="bookchat")
    story_id = Column(Integer, nullable=False, index=True, default=0)
    session_id = Column(String(255), nullable=False, index=True)

    role = Column(String(50), nullable=False)  # user / assistant
    input_mode = Column(String(50), nullable=True)

    intent = Column(String(50), nullable=True)

    # user
    user_text = Column(Text, nullable=True)

    # assistant
    lead_text = Column(Text, nullable=True)
    story_text = Column(Text, nullable=True)
    guide_text = Column(Text, nullable=True)
    choices_json = Column(Text, nullable=True)

    should_save = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)