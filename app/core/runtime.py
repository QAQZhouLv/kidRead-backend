from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.cache.base import CacheBackend
from app.cache.noop_cache import NoopCache
from app.cache.redis_cache import RedisCache
from app.core.config import REDIS_QUEUE_NAME, REDIS_URL
from app.core.feature_flags import FeatureFlags, get_feature_flags
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sqlalchemy_message_repository import SQLAlchemyMessageRepository
from app.repositories.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.repositories.sqlalchemy_story_repository import SQLAlchemyStoryRepository
from app.repositories.story_repository import StoryRepository
from app.tasks.base import TaskQueue
from app.tasks.inline_queue import InlineQueue
from app.tasks.job_runner import build_inline_handlers
from app.tasks.redis_queue import RedisQueue


@dataclass
class AppRuntime:
    flags: FeatureFlags
    story_repo: StoryRepository
    session_repo: SessionRepository
    message_repo: MessageRepository
    cache: CacheBackend
    task_queue: TaskQueue


def _build_cache(flags: FeatureFlags) -> CacheBackend:
    if flags.use_pg_redis_backends and REDIS_URL:
        try:
            return RedisCache(REDIS_URL)
        except Exception:
            return NoopCache()
    return NoopCache()


def _build_task_queue(flags: FeatureFlags, db: Session) -> TaskQueue:
    if flags.use_async_side_effects and flags.use_pg_redis_backends and REDIS_URL:
        try:
            return RedisQueue(REDIS_URL, queue_name=REDIS_QUEUE_NAME)
        except Exception:
            return InlineQueue(build_inline_handlers(db))
    return InlineQueue(build_inline_handlers(db))


def build_runtime(db: Session) -> AppRuntime:
    flags = get_feature_flags()
    return AppRuntime(
        flags=flags,
        story_repo=SQLAlchemyStoryRepository(db),
        session_repo=SQLAlchemySessionRepository(db),
        message_repo=SQLAlchemyMessageRepository(db),
        cache=_build_cache(flags),
        task_queue=_build_task_queue(flags, db),
    )
