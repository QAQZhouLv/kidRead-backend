from dataclasses import dataclass

from app.core.config import (
    ENABLE_ASYNC_TASKS,
    ENABLE_FAST_CONTEXT,
    ENABLE_PERSISTENT_ASR,
    ENABLE_QDRANT,
    ENABLE_RAG,
    ENABLE_REDIS,
    ENABLE_TTS_MANIFEST,
)


@dataclass(frozen=True)
class FeatureFlags:
    enable_redis: bool = ENABLE_REDIS
    enable_qdrant: bool = ENABLE_QDRANT
    enable_rag: bool = ENABLE_RAG
    use_async_side_effects: bool = ENABLE_ASYNC_TASKS
    use_fast_context: bool = ENABLE_FAST_CONTEXT
    use_tts_manifest: bool = ENABLE_TTS_MANIFEST
    use_persistent_asr: bool = ENABLE_PERSISTENT_ASR

    @property
    def use_pg_redis_backends(self) -> bool:
        return self.enable_redis

    @property
    def use_vector_retrieval(self) -> bool:
        return self.enable_rag


def get_feature_flags() -> FeatureFlags:
    return FeatureFlags()
