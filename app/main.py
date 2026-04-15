from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.app_config import router as app_config_router
from app.api.asr import router as asr_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.chat_stream import router as chat_stream_router
from app.api.messages import router as messages_router
from app.api.openings import router as openings_router
from app.api.sessions import router as sessions_router
from app.api.stories import router as stories_router
from app.api.tts import router as tts_router
from app.core.config import APP_NAME
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.opening_topic import OpeningTopic
from app.models.story import Story
from app.models.story_message import StoryMessage
from app.models.story_session import StorySession
from app.models.user import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "tts").mkdir(parents=True, exist_ok=True)
(static_dir / "covers").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")



def seed_opening_topics():
    db = SessionLocal()
    try:
        exists = db.query(OpeningTopic).count()
        if exists > 0:
            return

        default_topics = [
            "森林冒险", "小猫奇遇", "月亮朋友", "魔法校园", "海底秘密",
            "云朵王国", "星空旅行", "会说话的玩具", "神奇列车", "时间小屋",
            "公主与骑士", "勇敢小狐狸", "节日惊喜", "龙与宝藏", "晚安星球"
        ]
        for idx, name in enumerate(default_topics):
            db.add(OpeningTopic(name=name, category="story_theme", sort_order=idx))
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    seed_opening_topics()


@app.get("/")
def root():
    return {"message": "KidRead Backend Running"}


@app.get("/health")
def health():
    return {"ok": True}


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(stories_router)
app.include_router(sessions_router)
app.include_router(asr_router)
app.include_router(messages_router)
app.include_router(chat_stream_router)
app.include_router(tts_router)
app.include_router(openings_router)
app.include_router(app_config_router)
