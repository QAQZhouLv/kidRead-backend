from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base


class OpeningTopic(Base):
    __tablename__ = "opening_topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=True, default="general")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)