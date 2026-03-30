from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.base import Base


class StorySession(Base):
    __tablename__ = "story_sessions"

    id = Column(Integer, primary_key=True, index=True)

    scene = Column(String(50), nullable=False, index=True, default="bookchat")
    story_id = Column(Integer, nullable=False, index=True, default=0)

    session_id = Column(String(255), nullable=False, unique=True, index=True)

    title = Column(String(255), nullable=False, default="新对话")
    summary = Column(Text, nullable=True)
    draft_content = Column(Text, nullable=False, default="")
    status = Column(String(50), nullable=False, default="active")  # active / archived / merged

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)