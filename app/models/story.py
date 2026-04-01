from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="未命名故事")
    age = Column(Integer, nullable=False, default=6)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False, default="")

    cover_image_url = Column(String(500), nullable=True)
    fallback_cover_url = Column(String(500), nullable=True)
    cover_status = Column(String(50), nullable=False, default="fallback")  # fallback / generating / ready / failed
    cover_prompt = Column(Text, nullable=True)
    title_source = Column(String(50), nullable=False, default="default")  # default / auto / manual

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)