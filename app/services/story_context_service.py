import json
from typing import Any


FAST_CONTEXT_MAX_CHARS = 1600
FAST_CONTEXT_TAIL_PARAGRAPHS = 2


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


def _split_paragraphs(full_content: str) -> list[str]:
    paragraphs = [p.strip() for p in (full_content or "").replace("\r", "").split("\n")]
    return [p for p in paragraphs if p]


def _pick_tail_excerpt(paragraphs: list[str], *, max_chars: int, tail_paragraphs: int) -> str:
    if not paragraphs:
        return ""

    selected: list[str] = []
    total = 0
    for para in reversed(paragraphs[-tail_paragraphs:]):
        candidate_len = len(para) + (1 if selected else 0)
        if selected and total + candidate_len > max_chars:
            break
        selected.append(para)
        total += candidate_len

    if not selected:
        joined = "\n".join(paragraphs)
        return joined[-max_chars:]

    selected.reverse()
    excerpt = "\n".join(selected).strip()
    return excerpt[-max_chars:] if len(excerpt) > max_chars else excerpt


def _normalize_retrieved_chunks(retrieved_chunks: list[str] | None) -> list[str]:
    if not retrieved_chunks:
        return []
    result = []
    seen = set()
    for chunk in retrieved_chunks:
        chunk = (chunk or "").strip()
        if not chunk or chunk in seen:
            continue
        seen.add(chunk)
        result.append(chunk)
    return result


def build_fast_story_context(full_content: str, retrieved_chunks: list[str] | None = None) -> tuple[str, dict]:
    paragraphs = _split_paragraphs(full_content)
    tail_excerpt = _pick_tail_excerpt(paragraphs, max_chars=900, tail_paragraphs=FAST_CONTEXT_TAIL_PARAGRAPHS)
    hits = _normalize_retrieved_chunks(retrieved_chunks)

    sections: list[str] = []
    if hits:
        sections.append("【命中片段】\n" + "\n".join(hits))
    if tail_excerpt:
        sections.append("【最近片段】\n" + tail_excerpt)

    if not sections:
        return full_content[-FAST_CONTEXT_MAX_CHARS:], {"hit_count": 0}

    content = "\n\n".join(sections).strip()
    if len(content) > FAST_CONTEXT_MAX_CHARS:
        content = content[:FAST_CONTEXT_MAX_CHARS]

    return content, {"hit_count": len(hits)}


def pack_context_for_prompt(
    story,
    use_fast_context: bool = False,
    query_text: str = "",
    retrieved_chunks: list[str] | None = None,
) -> dict:
    age = getattr(story, "age", None) or 6
    difficulty = getattr(story, "difficulty_level", None) or "L2"
    full_content = getattr(story, "content", "") or ""
    story_summary = safe_json_load(
        getattr(story, "story_summary", None),
        build_story_summary(full_content),
    )

    if not isinstance(story_summary, dict):
        story_summary = build_story_summary(full_content)

    selected_content = full_content
    context_mode = "full"
    fast_meta = {"hit_count": 0}
    if use_fast_context:
        selected_content, fast_meta = build_fast_story_context(full_content, retrieved_chunks=retrieved_chunks)
        context_mode = "fast"

    story_summary = {
        **story_summary,
        "_context_mode": context_mode,
        "_full_content_length": len(full_content),
        "_selected_content_length": len(selected_content or ""),
        "_hit_count": fast_meta.get("hit_count", 0),
        "_query_text": query_text or "",
    }

    return {
        "story_spec": safe_json_load(getattr(story, "story_spec", None), build_empty_story_spec(age, difficulty)),
        "story_state": safe_json_load(getattr(story, "story_state", None), build_empty_story_state()),
        "story_summary": story_summary,
        "content": selected_content,
        "full_content": full_content,
    }
