from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="未命名故事")
    age = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    # 三层故事上下文
    story_spec = Column(Text, nullable=True)        # JSON string
    story_state = Column(Text, nullable=True)       # JSON string
    story_summary = Column(Text, nullable=True)     # JSON string

    # 分级与安全
    target_age = Column(String(20), nullable=True)         # 3-5 / 6-8 / 9-12
    difficulty_level = Column(String(20), nullable=True)   # L1 / L2 / L3
    safety_status = Column(String(20), nullable=False, default="passed")
    safety_tags = Column(Text, nullable=True)              # JSON string

    cover_image_url = Column(String(500), nullable=True)
    fallback_cover_url = Column(String(500), nullable=True)
    cover_status = Column(String(50), nullable=False, default="fallback")
    cover_prompt = Column(Text, nullable=True)
    title_source = Column(String(50), nullable=False, default="default")

    is_favorite = Column(Boolean, nullable=False, default=False)

    # 软删除字段
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
