from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.opening_topic import OpeningTopic
from app.models.story import Story  # noqa: F401
from app.models.story_chunk import StoryChunk  # noqa: F401
from app.models.story_message import StoryMessage  # noqa: F401
from app.models.story_session import StorySession  # noqa: F401
from app.models.task_record import TaskRecord  # noqa: F401
from app.models.user import User  # noqa: F401


def seed_opening_topics() -> None:
    db = SessionLocal()
    try:
        if db.query(OpeningTopic).count() > 0:
            return
        topics = [
            "森林冒险", "小猫奇遇", "月亮朋友", "魔法校园", "海底秘密",
            "云朵王国", "星空旅行", "会说话的玩具", "神奇列车", "时间小屋",
            "公主与骑士", "勇敢小狐狸", "节日惊喜", "龙与宝藏", "晚安星球",
        ]
        for idx, name in enumerate(topics):
            db.add(OpeningTopic(name=name, category="story_theme", sort_order=idx, enabled=True))
        db.commit()
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    seed_opening_topics()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
