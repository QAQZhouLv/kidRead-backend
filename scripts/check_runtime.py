from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.runtime import build_runtime
from app.db.session import RESOLVED_DATABASE_URL, SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        runtime = build_runtime(db)
        print("database:", RESOLVED_DATABASE_URL)
        print("cache:", runtime.cache.__class__.__name__)
        print("task_queue:", runtime.task_queue.__class__.__name__)
        print("vector_store:", runtime.vector_store.__class__.__name__)
        print("flags:", runtime.flags)
    finally:
        db.close()


if __name__ == "__main__":
    main()
