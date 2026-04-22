import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "KidRead Backend")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kidread.db")
PG_DATABASE_URL = os.getenv("PG_DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "kidread:jobs")
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "")
VECTOR_URL = os.getenv("VECTOR_URL", "")

USE_PG_REDIS_BACKENDS = os.getenv("USE_PG_REDIS_BACKENDS", "false").lower() == "true"
USE_ASYNC_SIDE_EFFECTS = os.getenv("USE_ASYNC_SIDE_EFFECTS", "false").lower() == "true"
USE_FAST_CONTEXT = os.getenv("USE_FAST_CONTEXT", "false").lower() == "true"
USE_VECTOR_RETRIEVAL = os.getenv("USE_VECTOR_RETRIEVAL", "false").lower() == "true"
USE_TTS_MANIFEST = os.getenv("USE_TTS_MANIFEST", "false").lower() == "true"
USE_PERSISTENT_ASR = os.getenv("USE_PERSISTENT_ASR", "false").lower() == "true"

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

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
