# KidRead Runbook

## Local startup

```bash
docker compose up -d
copy .env.example .env
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Optional worker

```bash
python -m app.tasks.redis_worker
```

Use this only when `ENABLE_ASYNC_TASKS=true`.

## Check runtime

```bash
python scripts/check_runtime.py
```

Or request:

```text
GET http://127.0.0.1:8000/api/debug/runtime
```

## Smoke test

```bash
python scripts/smoke_test.py
```

## Expected data after archiving a story

- `stories`: official story content and structured context.
- `story_chunks`: PostgreSQL metadata of story fragments.
- `task_records`: vector sync and delete task status.
- Qdrant collection `story_chunks`: story fragment vectors.

