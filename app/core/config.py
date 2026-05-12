import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


APP_NAME = os.getenv("APP_NAME", "KidRead Backend")
DEBUG = _bool("DEBUG", "true")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://kidread:kidread123@localhost:5432/kidread",
)
PG_DATABASE_URL = os.getenv("PG_DATABASE_URL", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "kidread:jobs")

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "qdrant")
QDRANT_URL = os.getenv("QDRANT_URL", os.getenv("VECTOR_URL", "http://localhost:6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "story_chunks")
QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "0") or "0")

ENABLE_REDIS = _bool("ENABLE_REDIS", os.getenv("USE_PG_REDIS_BACKENDS", "true"))
ENABLE_QDRANT = _bool("ENABLE_QDRANT", "true")
ENABLE_RAG = _bool("ENABLE_RAG", os.getenv("USE_VECTOR_RETRIEVAL", "true"))
ENABLE_ASYNC_TASKS = _bool("ENABLE_ASYNC_TASKS", os.getenv("USE_ASYNC_SIDE_EFFECTS", "false"))
ENABLE_FAST_CONTEXT = _bool("ENABLE_FAST_CONTEXT", os.getenv("USE_FAST_CONTEXT", "true"))
ENABLE_TTS_MANIFEST = _bool("ENABLE_TTS_MANIFEST", os.getenv("USE_TTS_MANIFEST", "true"))
ENABLE_PERSISTENT_ASR = _bool("ENABLE_PERSISTENT_ASR", os.getenv("USE_PERSISTENT_ASR", "false"))

USE_PG_REDIS_BACKENDS = ENABLE_REDIS
USE_ASYNC_SIDE_EFFECTS = ENABLE_ASYNC_TASKS
USE_FAST_CONTEXT = ENABLE_FAST_CONTEXT
USE_VECTOR_RETRIEVAL = ENABLE_RAG
USE_TTS_MANIFEST = ENABLE_TTS_MANIFEST
USE_PERSISTENT_ASR = ENABLE_PERSISTENT_ASR

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY or "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", LLM_BASE_URL or "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")

HTTP_PUBLIC_BASE_URL = os.getenv("HTTP_PUBLIC_BASE_URL", "")
TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "./static/tts")

WX_APP_ID = os.getenv("WX_APP_ID", "")
WX_APP_SECRET = os.getenv("WX_APP_SECRET", "")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "kidread-dev-token-secret")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))

if not LLM_API_KEY:
    raise ValueError("❌ 未配置 LLM_API_KEY")
if not LLM_BASE_URL:
    raise ValueError("❌ 未配置 LLM_BASE_URL")
if not LLM_MODEL:
    raise ValueError("❌ 未配置 LLM_MODEL")
