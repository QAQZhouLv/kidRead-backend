from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import APP_NAME
from app.db.base import Base
from app.db.session import engine

from app.models.story import Story
from app.models.story_message import StoryMessage
from app.models.story_session import StorySession

from app.api.chat import router as chat_router
from app.api.stories import router as stories_router
from app.api.sessions import router as sessions_router
from app.api.asr import router as asr_router
from app.api.messages import router as messages_router
from app.api.chat_stream import router as chat_stream_router
from app.api.tts import router as tts_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("./static")
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "tts").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def root():
    return {"message": "KidRead Backend Running"}


@app.get("/health")
def health():
    return {"ok": True}


app.include_router(chat_router)
app.include_router(stories_router)
app.include_router(sessions_router)
app.include_router(asr_router)
app.include_router(messages_router)
app.include_router(chat_stream_router)
app.include_router(tts_router)
