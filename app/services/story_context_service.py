import json
from typing import Any


def safe_json_load(text: str | None, default: Any):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def build_empty_story_spec(age: int, difficulty_level: str = "L2") -> dict:
    return {
        "target_age": age,
        "difficulty_level": difficulty_level,
        "genre": "",
        "world_setting": "",
        "characters": [],
        "narrative_style": "温柔儿童故事",
        "allowed_themes": [],
        "forbidden_themes": [],
    }


def build_empty_story_state() -> dict:
    return {
        "current_chapter": 1,
        "current_location": "",
        "current_goal": "",
        "plot_flags": {},
        "character_status": {},
        "pending_foreshadowing": [],
        "safety_review_passed": True,
        "risk_tags": [],
        "rewrite_count": 0,
    }


def build_story_summary(full_content: str) -> dict:
    text = (full_content or "").strip()
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    last_excerpt = "\n".join(lines[-3:]) if lines else ""
    short = text[:220] if len(text) > 220 else text
    return {
        "summary_short": short,
        "summary_structured": {
            "main_characters": [],
            "key_events": [],
            "open_loops": [],
        },
        "last_excerpt": last_excerpt,
    }


def pack_context_for_prompt(story) -> dict:
    age = getattr(story, "age", None) or 6
    difficulty = getattr(story, "difficulty_level", None) or "L2"
    return {
        "story_spec": safe_json_load(getattr(story, "story_spec", None), build_empty_story_spec(age, difficulty)),
        "story_state": safe_json_load(getattr(story, "story_state", None), build_empty_story_state()),
        "story_summary": safe_json_load(
            getattr(story, "story_summary", None),
            build_story_summary(getattr(story, "content", "") or ""),
        ),
        "content": getattr(story, "content", "") or "",
    }
