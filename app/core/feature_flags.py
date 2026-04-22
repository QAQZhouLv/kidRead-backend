from dataclasses import dataclass

from app.core.config import (
    USE_ASYNC_SIDE_EFFECTS,
    USE_FAST_CONTEXT,
    USE_PG_REDIS_BACKENDS,
    USE_PERSISTENT_ASR,
    USE_TTS_MANIFEST,
    USE_VECTOR_RETRIEVAL,
)


@dataclass(frozen=True)
class FeatureFlags:
    use_pg_redis_backends: bool = USE_PG_REDIS_BACKENDS
    use_async_side_effects: bool = USE_ASYNC_SIDE_EFFECTS
    use_fast_context: bool = USE_FAST_CONTEXT
    use_vector_retrieval: bool = USE_VECTOR_RETRIEVAL
    use_tts_manifest: bool = USE_TTS_MANIFEST
    use_persistent_asr: bool = USE_PERSISTENT_ASR


def get_feature_flags() -> FeatureFlags:
    return FeatureFlags()
