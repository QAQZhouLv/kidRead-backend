from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    wx_openid = Column(String(255), nullable=False, unique=True, index=True)
    wx_unionid = Column(String(255), nullable=True, index=True)

    nickname = Column(String(255), nullable=True)
    avatar_url = Column(String(1000), nullable=True)
    display_name = Column(String(255), nullable=True)

    role = Column(String(50), nullable=False, default="user")
    is_demo_user = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
