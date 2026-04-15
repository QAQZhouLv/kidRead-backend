from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.base import Base


class StorySession(Base):
    __tablename__ = "story_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, default=0)

    scene = Column(String(50), nullable=False, index=True, default="bookchat")
    story_id = Column(Integer, nullable=False, index=True, default=0)
    session_id = Column(String(255), nullable=False, unique=True, index=True)

    title = Column(String(255), nullable=False, default="新对话")
    summary = Column(Text, nullable=True)
    draft_content = Column(Text, nullable=False, default="")
    status = Column(String(50), nullable=False, default="active")

    is_pinned = Column(Boolean, nullable=False, default=False)
    pinned_at = Column(DateTime, nullable=True)
    title_source = Column(String(50), nullable=False, default="default")  # default / auto / manual
    is_auto_titled = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
