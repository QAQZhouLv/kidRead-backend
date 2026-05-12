# KidRead Backend

This upgraded backend aligns the runnable project with the thesis description: FastAPI + PostgreSQL + Redis + Qdrant, with structured story context and retrieval-augmented in-story dialogue.

## 1. Start middleware

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, and Qdrant.

## 2. Prepare environment

Copy `.env.example` to `.env` and fill in the LLM and embedding keys.

```bash
copy .env.example .env
```

## 3. Install dependencies

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## 4. Initialize database

```bash
python scripts/init_db.py
```

## 5. Start API service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If `ENABLE_ASYNC_TASKS=true`, also start the worker:

```bash
python -m app.tasks.redis_worker
```

For stable local demonstration, `ENABLE_ASYNC_TASKS=false` keeps side effects inline/background while still writing `task_records`.

## 6. Key thesis-aligned flow

1. Create or log in as a user.
2. Generate a story through `/api/chat/unified`.
3. Archive the story through `/api/stories`.
4. The backend generates `story_spec`, `story_state`, and `story_summary`.
5. The story is split into `story_chunks` in PostgreSQL.
6. Chunk vectors are written to Qdrant when embedding is available.
7. In bookchat, Qdrant retrieval supplies story fragments to the prompt.
8. Story append updates the official content, context, chunks, and vector index.

## 7. Debug endpoints

Debug endpoints are enabled only when `DEBUG=true`:

- `GET /api/debug/runtime`
- `GET /api/debug/story/{story_id}/chunks`
- `GET /api/debug/story/{story_id}/tasks`

