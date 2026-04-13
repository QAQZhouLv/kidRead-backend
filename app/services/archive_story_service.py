from app.agent.json_utils import extract_json_block
from app.agent.llm import get_chat_model
from app.services.story_context_service import (
    build_empty_story_spec,
    build_empty_story_state,
    build_story_summary,
)


def generate_story_spec_and_state(age: int, full_content: str) -> tuple[dict, dict, dict]:
    llm = get_chat_model()

    system = """
你是故事结构化分析助手。
请从给定儿童故事中提取：
1. story_spec：静态设定
2. story_state：动态剧情状态
3. story_summary：简短摘要

只输出 JSON：
{
  "story_spec": {...},
  "story_state": {...},
  "story_summary": {...}
}
""".strip()

    user = f"""
目标年龄：{age}
故事全文：
{full_content}
""".strip()

    try:
        raw = llm.invoke([("system", system), ("user", user)])
        content = raw.content if hasattr(raw, "content") else str(raw)
        data = extract_json_block(content)

        spec = data.get("story_spec") or build_empty_story_spec(age)
        state = data.get("story_state") or build_empty_story_state()
        summary = data.get("story_summary") or build_story_summary(full_content)
        return spec, state, summary
    except Exception:
        return (
            build_empty_story_spec(age),
            build_empty_story_state(),
            build_story_summary(full_content),
        )
