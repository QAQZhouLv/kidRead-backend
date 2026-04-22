from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL, PG_DATABASE_URL, USE_PG_REDIS_BACKENDS


def _resolve_database_url() -> str:
    if USE_PG_REDIS_BACKENDS and PG_DATABASE_URL:
        return PG_DATABASE_URL
    return DATABASE_URL


RESOLVED_DATABASE_URL = _resolve_database_url()

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
}

if RESOLVED_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(RESOLVED_DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
