from app.agent.graph import prepare_chat_state
from app.agent.json_utils import extract_json_block, normalize_response_dict, to_schema
from app.agent.llm import get_chat_model, get_json_model
from app.agent.tools import (
    adjust_story_tool,
    ask_story_tool,
    continue_story_tool,
    create_story_tool,
    end_chat_tool,
    safety_redirect_tool,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.content_guard import build_rewrite_instruction, evaluate_content
from app.services.rule_service import normalize_age_group


SKILL_HINTS = {
    "create": "你在 create 场景里负责从零开始共创故事。应优先建立角色、场景、目标和第一步推进。",
    "continue": "你负责在现有设定上继续推进情节。必须承接已有正文和会话草稿，不能像重新开题。",
    "qa": "你负责解释、回答和澄清故事内容。不要新增正文情节，重点是解释当前书里的内容与因果。",
    "adjust": "你负责根据用户要求微调已有故事。优先局部调整语气、节奏、角色表现或最近一段，不要粗暴重置全局设定。",
    "unsafe": "你负责把不安全方向温和重定向到安全、适龄的儿童故事方向。",
    "end": "你负责礼貌收尾，不新增正文，不开启新情节。",
}


def build_history_text(req: ChatRequest) -> str:
    lines = []
    for item in (req.history or [])[-8:]:
        if item.role == "user":
            lines.append(f"用户：{item.text or ''}")
        else:
            parts = []
            if item.lead_text:
                parts.append(f"承接：{item.lead_text}")
            if item.story_text:
                parts.append(f"故事：{item.story_text}")
            if item.guide_text:
                parts.append(f"引导：{item.guide_text}")
            if item.choices:
                parts.append(f"选项：{', '.join(item.choices)}")
            lines.append("AI：" + "；".join(parts))
    return "\n".join(lines) if lines else "无"


def build_skill_instruction(skill: str) -> str:
    return SKILL_HINTS.get(skill, SKILL_HINTS["continue"])


def call_tool_by_intent(req: ChatRequest, intent: str) -> str:
    if intent == "create_story":
        return create_story_tool.invoke({"age": req.age, "user_text": req.text})
    if intent == "continue_story":
        return continue_story_tool.invoke({"age": req.age, "user_text": req.text})
    if intent == "ask_about_story":
        return ask_story_tool.invoke({"user_text": req.text})
    if intent == "adjust_story":
        return adjust_story_tool.invoke({"age": req.age, "user_text": req.text})
    if intent == "end_chat":
        return end_chat_tool.invoke({})
    return safety_redirect_tool.invoke({})


def build_structured_messages(req: ChatRequest, intent: str, tool_result: str, skill: str):
    history_block = build_history_text(req)
    current_story = (req.current_story_content or "").strip()
    draft_story = (req.session_draft_content or "").strip()
    story_spec = req.story_spec or {}
    story_state = req.story_state or {}
    story_summary = req.story_summary or {}

    system = f"""
你是儿童故事共创助手，也是一个受控技能节点。

技能说明：
{build_skill_instruction(skill)}

你必须输出一个严格符合 ChatResponse 结构的结果。

总要求：
1. 内容适合 {req.age} 岁儿童，年龄档为 {normalize_age_group(req.age)}。
2. 语言温和、具体、易理解。
3. 必须保持角色、称呼、设定、情节前后连贯。
4. 在 bookchat 场景下，优先依据正式正文、story_spec、story_state、story_summary 和会话草稿；历史聊天只作补充。
5. 不要把解释、选项、提示混进 story_text。
6. 用户若明确表示结束，不再继续正文。

三段式要求：
- lead_text：回应用户当前输入中的具体点，要有承接感
- story_text：只写故事正文；ask_about_story、unsafety、end_chat 时必须为空字符串
- guide_text：自然引导下一步；end_chat 时改成礼貌收尾
- choices：2~4 个简短可点击选项
- should_save：
  - create_story / continue_story 通常为 true
  - ask_about_story / unsafety / end_chat 必须为 false
  - adjust_story 视是否产出新正文而定

当前 intent：{intent}
当前 scene：{req.scene}
""".strip()

    user = f"""
〖用户本轮输入〗
{req.text}

〖story_spec（静态设定）〗
{story_spec}

〖story_state（动态剧情台账）〗
{story_state}

〖story_summary（压缩摘要）〗
{story_summary}

〖当前正式正文〗
{current_story if current_story else '无'}

〖本次会话草稿〗
{draft_story if draft_story else '无'}

〖最近聊天记录（仅补充参考）〗
{history_block}

〖工具结果〗
{tool_result}
""".strip()

    return system, user


def build_json_fallback_messages(req: ChatRequest, intent: str, tool_result: str, skill: str):
    system, user = build_structured_messages(req, intent, tool_result, skill)
    system += """

你只能输出 JSON。
不要输出 markdown，不要输出解释，不要输出额外文字。
JSON 必须严格符合 ChatResponse。
""".strip()
    return system, user


def fill_default_choices(intent: str):
    if intent in ("create_story", "continue_story"):
        return ["继续写下去", "换一个地点", "加一个新朋友"]
    if intent == "adjust_story":
        return ["变得更搞笑", "变得更温柔", "重新写这一段"]
    if intent == "ask_about_story":
        return ["继续解释", "继续写故事", "换个角度问"]
    if intent == "end_chat":
        return ["下次再聊", "回书架看看", "先休息一下"]
    return ["神奇动物", "勇敢冒险", "搞笑故事"]


def post_process_result(result: ChatResponse, intent: str) -> ChatResponse:
    result.intent = intent
    result.save_mode = "append"

    if intent in ("ask_about_story", "unsafety", "end_chat"):
        result.story_text = ""
        result.should_save = False

    if not result.choices:
        result.choices = fill_default_choices(intent)

    result.choices = result.choices[:4]
    return result


def _rewrite_story_text(req: ChatRequest, story_text: str, guard: dict) -> str:
    llm = get_chat_model()
    system = f"""
你是儿童故事安全改写助手。
请将内容改写为更适合 {req.age} 岁儿童的版本。
必须保留核心情节方向，但语言更简单、句子更短、氛围更温和。
只输出改写后的故事正文，不要输出解释。
""".strip()
    user = f"""
原正文：
{story_text}

改写要求：
{build_rewrite_instruction(guard)}
""".strip()
    rewritten = llm.invoke([("system", system), ("user", user)])
    content = rewritten.content if hasattr(rewritten, "content") else str(rewritten)
    return content.strip()


def evaluate_and_maybe_rewrite(req: ChatRequest, result: ChatResponse):
    if not result.story_text:
        return result, None

    difficulty_level = "L2"
    if req.story_spec and isinstance(req.story_spec, dict):
        difficulty_level = req.story_spec.get("difficulty_level", "L2")

    guard = evaluate_content(req.age, difficulty_level, result.story_text)
    if guard["passed"] or not guard["need_rewrite"]:
        return result, guard

    rewritten_story = _rewrite_story_text(req, result.story_text, guard)
    result.story_text = rewritten_story

    final_guard = evaluate_content(req.age, difficulty_level, result.story_text)
    final_guard["rewritten"] = True
    final_guard["original_risk_tags"] = guard.get("risk_tags", [])
    return result, final_guard


def _invoke_structured_generation(req: ChatRequest, intent: str, tool_result: str, skill: str) -> ChatResponse:
    llm = get_chat_model()
    system, user = build_structured_messages(req, intent, tool_result, skill)
    structured_llm = llm.with_structured_output(ChatResponse)
    result = structured_llm.invoke([("system", system), ("user", user)])
    return result


def _invoke_json_fallback(req: ChatRequest, intent: str, tool_result: str, skill: str) -> ChatResponse:
    json_llm = get_json_model()
    system, user = build_json_fallback_messages(req, intent, tool_result, skill)
    raw = json_llm.invoke([("system", system), ("user", user)])
    content = raw.content if hasattr(raw, "content") else str(raw)
    data = extract_json_block(content)
    data = normalize_response_dict(data)
    data["intent"] = intent

    if intent in ("ask_about_story", "unsafety", "end_chat"):
        data["story_text"] = ""
        data["should_save"] = False

    if not data.get("choices"):
        data["choices"] = fill_default_choices(intent)

    return to_schema(ChatResponse, data)


def run_story_agent(req: ChatRequest, *, user_id: int | None = None) -> ChatResponse:
    prepared = prepare_chat_state(req, user_id=user_id)
    intent = prepared["intent"]
    skill = prepared.get("skill", "continue")
    tool_result = call_tool_by_intent(req, intent)

    try:
        result = _invoke_structured_generation(req, intent, tool_result, skill)
    except Exception as first_error:
        try:
            result = _invoke_json_fallback(req, intent, tool_result, skill)
        except Exception as second_error:
            raise RuntimeError(
                f"结构化输出失败。first_error={first_error}; second_error={second_error}"
            )

    result = post_process_result(result, intent)
    result, guard = evaluate_and_maybe_rewrite(req, result)
    if guard is not None:
        object.__setattr__(result, "_guard_result", guard)
    object.__setattr__(result, "_context_snapshot", prepared.get("snapshot") or {})
    return result
