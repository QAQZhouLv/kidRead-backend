from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.cache.base import CacheBackend
from app.cache.noop_cache import NoopCache
from app.cache.redis_cache import RedisCache
from app.core.config import (
    MILVUS_COLLECTION,
    MILVUS_CONTENT_FIELD,
    MILVUS_TOKEN,
    MILVUS_URI,
    REDIS_QUEUE_NAME,
    REDIS_URL,
    VECTOR_BACKEND,
)
from app.core.feature_flags import FeatureFlags, get_feature_flags
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sqlalchemy_message_repository import SQLAlchemyMessageRepository
from app.repositories.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.repositories.sqlalchemy_story_repository import SQLAlchemyStoryRepository
from app.repositories.story_repository import StoryRepository
from app.services.embedding_service import embed_query
from app.tasks.base import TaskQueue
from app.tasks.inline_queue import InlineQueue
from app.tasks.job_runner import build_inline_handlers
from app.tasks.redis_queue import RedisQueue
from app.vectorstore.base import StoryVectorStore
from app.vectorstore.milvus_vector_store import MilvusVectorStore
from app.vectorstore.noop_vector_store import NoopVectorStore
from app.vectorstore.simple_text_vector_store import SimpleTextVectorStore


@dataclass
class AppRuntime:
    flags: FeatureFlags
    story_repo: StoryRepository
    session_repo: SessionRepository
    message_repo: MessageRepository
    cache: CacheBackend
    task_queue: TaskQueue
    vector_store: StoryVectorStore


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


def _build_vector_store(flags: FeatureFlags) -> StoryVectorStore:
    if not flags.use_vector_retrieval:
        return NoopVectorStore()

    backend = (VECTOR_BACKEND or "simple").strip().lower()
    if backend in ("", "simple", "lexical"):
        return SimpleTextVectorStore()

    if backend == "milvus":
        try:
            return MilvusVectorStore(
                uri=MILVUS_URI,
                token=MILVUS_TOKEN,
                collection_name=MILVUS_COLLECTION,
                content_field=MILVUS_CONTENT_FIELD,
                embed_query_fn=embed_query,
            )
        except Exception:
            return NoopVectorStore()

    return NoopVectorStore()


def build_runtime(db: Session) -> AppRuntime:
    flags = get_feature_flags()
    return AppRuntime(
        flags=flags,
        story_repo=SQLAlchemyStoryRepository(db),
        session_repo=SQLAlchemySessionRepository(db),
        message_repo=SQLAlchemyMessageRepository(db),
        cache=_build_cache(flags),
        task_queue=_build_task_queue(flags, db),
        vector_store=_build_vector_store(flags),
    )
