import random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.opening_topic import OpeningTopic

router = APIRouter(prefix="/api/openings", tags=["openings"])

GREETINGS = [
    "欢迎来到故事创作世界！",
    "慧童已经准备好和你一起编故事啦！",
    "今天也来一起打开一个新的故事吧！",
    "故事小门已经打开啦，我们出发吧！",
]

GUIDES = [
    "你想让主角先遇见什么呢？可以从下面选一个方向。",
    "今天想写什么类型的故事？先选一个你最感兴趣的主题吧。",
    "我们先决定故事往哪里走，再一起慢慢写下去。",
    "先挑一个故事方向，慧童就能陪你继续展开。",
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/create")
def get_create_opening(db: Session = Depends(get_db)):
    rows = db.query(OpeningTopic).order_by(OpeningTopic.sort_order.asc(), OpeningTopic.id.asc()).all()
    topics = [r.name for r in rows]
    sample = random.sample(topics, k=min(3, len(topics))) if topics else ["森林冒险", "星空旅行", "海底秘密"]

    return {
        "lead_text": random.choice(GREETINGS),
        "guide_text": random.choice(GUIDES),
        "choices": sample
    }