import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "KidRead Backend")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kidread.db")

# LLM 配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

# TTS 配置
HTTP_PUBLIC_BASE_URL = os.getenv("HTTP_PUBLIC_BASE_URL", "")
TTS_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "./static/tts")

# 微信与登录态配置
WX_APP_ID = os.getenv("WX_APP_ID", "")
WX_APP_SECRET = os.getenv("WX_APP_SECRET", "")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "kidread-dev-token-secret")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))

# 安全校验
if not LLM_API_KEY:
    raise ValueError("❌ 未配置 LLM_API_KEY")

if not LLM_BASE_URL:
    raise ValueError("❌ 未配置 LLM_BASE_URL")

if not LLM_MODEL:
    raise ValueError("❌ 未配置 LLM_MODEL")
