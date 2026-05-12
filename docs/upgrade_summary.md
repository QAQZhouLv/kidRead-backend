# Project Upgrade Summary

## Completed in this upgrade package

- Added PostgreSQL-first `.env.example` configuration.
- Added `docker-compose.yml` for PostgreSQL, Redis, and Qdrant.
- Added dependencies: `psycopg[binary]`, `redis`, and `qdrant-client`.
- Added `story_chunks` ORM model and repository.
- Added `task_records` ORM model and repository.
- Added Redis-aware task status service that stores task state in Redis and persistent task records in PostgreSQL.
- Replaced the old vector-store implementation with `qdrant_vector_store.py`.
- The upgraded code package now uses Qdrant as the vector backend.
- Upgraded story archiving to generate `story_spec`, `story_state`, and `story_summary`.
- Upgraded story vector sync to write PostgreSQL `story_chunks` and Qdrant points.
- Upgraded story append to refresh structured context and vector chunks.
- Added debug endpoints for runtime, chunks, and task records.
- Expanded the LangGraph preparation workflow so the code exposes request preprocessing, context loading, intent routing, retrieval boundary, and prompt context assembly.
- Added scripts for database initialization, runtime checking, reset, and smoke testing.
- Updated Mini Program login payload so user age and theme preference can be persisted by the backend.

## Important notes

- Qdrant vector writing depends on a working embedding configuration.
- If Qdrant or Redis is unavailable, the main story flow degrades instead of crashing.
- Generated static audio and cover files are intentionally excluded from the package.
- The backend still requires valid LLM settings in `.env` before startup.

