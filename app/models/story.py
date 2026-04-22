from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, default=0)

    title = Column(String(255), default="未命名故事")
    age = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    # 结构化上下文
    story_spec = Column(Text, nullable=True)
    story_state = Column(Text, nullable=True)
    story_summary = Column(Text, nullable=True)
    target_age = Column(String(20), nullable=True)
    difficulty_level = Column(String(20), nullable=True)
    safety_status = Column(String(20), nullable=False, default="passed")
    safety_tags = Column(Text, nullable=True)

    # 封面与标题
    cover_image_url = Column(String(500), nullable=True)
    # 保留旧字段，兼容旧库；新逻辑不再主动生成 fallback 图片
    fallback_cover_url = Column(String(500), nullable=True)
    cover_status = Column(String(50), nullable=False, default="fallback")
    cover_prompt = Column(Text, nullable=True)
    title_source = Column(String(50), nullable=False, default="default")

    is_favorite = Column(Boolean, nullable=False, default=False)

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
