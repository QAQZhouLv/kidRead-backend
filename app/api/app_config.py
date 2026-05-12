from fastapi import APIRouter

from app.core.feature_flags import get_feature_flags

router = APIRouter(prefix="/api/app", tags=["app"])


@router.get("/bootstrap")
def get_bootstrap_config():
    flags = get_feature_flags()
    return {
        "force_show_onboarding": False,
        "features": {
            "redis": flags.enable_redis,
            "qdrant": flags.enable_qdrant,
            "rag": flags.enable_rag,
            "fast_context": flags.use_fast_context,
            "tts_manifest": flags.use_tts_manifest,
            "persistent_asr": flags.use_persistent_asr,
        },
    }
