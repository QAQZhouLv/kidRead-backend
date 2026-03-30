from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.llm import get_chat_model, get_json_model
from app.agent.tools import (
    classify_intent_tool,
    create_story_tool,
    continue_story_tool,
    ask_story_tool,
    adjust_story_tool,
    safety_redirect_tool,
    end_chat_tool,
)
from app.agent.json_utils import (
    extract_json_block,
    normalize_response_dict,
    to_schema,
)


def build_history_text(req: ChatRequest) -> str:
    lines = []
    for item in req.history[-6:]:
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


def build_structured_messages(req: ChatRequest, intent: str, tool_result: str):
    history_block = build_history_text(req)
    current_story = (req.current_story_content or "").strip()
    draft_story = (req.session_draft_content or "").strip()

    system = f"""
你是儿童故事共创助手。

你必须输出一个严格符合 ChatResponse 结构的结果。

核心目标：
1. 内容适合 {req.age} 岁儿童。
2. 语言温和、具体、易理解。
3. 必须保持角色、称呼、设定、情节前后连贯。
4. 如果故事已经明显接近结尾，不要强行开启新主线，除非用户明确要求继续。
5. bookchat 场景下，续写必须优先基于“当前正式正文”和“本次会话草稿”，而不是旧聊天记录。
6. 历史聊天记录只能作为补充参考，不能覆盖当前正式正文。
7. 如果用户表示结束或离开，必须温和收尾，不再继续故事正文。

三段式要求：
- lead_text：承接用户刚才那句话，要有回应感，回应用户当前这句话中的一个具体点，比如角色、情绪、地点、要求或态度，不要总是泛泛地说“好呀我们继续”。
- story_text：只写故事正文；ask_about_story、unsafety、end_chat 时必须为空字符串。
- guide_text：自然引出下一步；如果是 end_chat，则改成礼貌收尾，不再引导继续创作。
- choices：2~4个，短而自然；end_chat 时可以给“下次再聊”“回书架看看”之类收尾选项。
- should_save：
  - create_story / continue_story 通常为 true
  - ask_about_story / unsafety / end_chat 必须为 false
  - adjust_story 视情况而定

当前 intent：{intent}
当前 scene：{req.scene}
""".strip()

    user = f"""
【用户本轮输入】
{req.text}

【当前正式正文（最高优先级）】
{current_story if current_story else "无"}

【本次会话草稿（第二优先级）】
{draft_story if draft_story else "无"}

【最近聊天记录（仅补充参考）】
{history_block}

【工具结果】
{tool_result}
""".strip()

    return system, user

def build_json_fallback_messages(req: ChatRequest, intent: str, tool_result: str):
    history_block = build_history_text(req)
    current_story = (req.current_story_content or "").strip()
    draft_story = (req.session_draft_content or "").strip()

    system = f"""
你是儿童故事共创助手。

你只能输出 JSON。
不要输出 markdown，不要输出解释，不要输出多余文字。

JSON 格式必须严格为：
{{
  "intent": "{intent}",
  "lead_text": "简短承接语",
  "story_text": "故事正文",
  "guide_text": "下一步引导",
  "choices": ["选项1", "选项2", "选项3"],
  "should_save": true,
  "save_mode": "append"
}}

规则：
1. 内容适合 {req.age} 岁儿童。
2. 必须保持角色、称呼、设定、情节连续。
3. bookchat 场景续写时，优先依据“当前正式正文”和“本次会话草稿”。
4. lead_text 必须回应用户刚刚的话，不能空泛。
5. story_text 只能写正文。
6. ask_about_story、unsafety、end_chat 时，story_text 必须为 ""。
7. end_chat 时不要继续讲故事，只做礼貌收尾。
8. choices 2~4 个。
9. 除 JSON 外不要输出任何字符。
""".strip()

    user = f"""
【用户输入】
{req.text}

【当前正式正文（最高优先级）】
{current_story if current_story else "无"}

【本次会话草稿（第二优先级）】
{draft_story if draft_story else "无"}

【最近聊天记录（仅补充参考）】
{history_block}

【工具结果】
{tool_result}
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


def call_tool_by_intent(req: ChatRequest, intent: str) -> str:
    if intent == "create_story":
        return create_story_tool.invoke({
            "age": req.age,
            "user_text": req.text
        })
    if intent == "continue_story":
        return continue_story_tool.invoke({
            "age": req.age,
            "user_text": req.text
        })
    if intent == "ask_about_story":
        return ask_story_tool.invoke({
            "user_text": req.text
        })
    if intent == "adjust_story":
        return adjust_story_tool.invoke({
            "age": req.age,
            "user_text": req.text
        })
    if intent == "end_chat":
        return end_chat_tool.invoke({})
    return safety_redirect_tool.invoke({})


def run_story_agent(req: ChatRequest) -> ChatResponse:
    # 1. 先分类
    intent = classify_intent_tool.invoke({
        "scene": req.scene,
        "user_text": req.text
    })

    # 2. 跑对应工具
    tool_result = call_tool_by_intent(req, intent)

    # 3. 第一层：LangChain 结构化输出
    try:
        llm = get_chat_model()
        system, user = build_structured_messages(req, intent, tool_result)

        structured_llm = llm.with_structured_output(ChatResponse)
        result = structured_llm.invoke([
            ("system", system),
            ("user", user),
        ])

        return post_process_result(result, intent)

    except Exception as first_error:
        # 4. 第二层：强制 JSON + 手动解析
        try:
            json_llm = get_json_model()
            system, user = build_json_fallback_messages(req, intent, tool_result)

            raw = json_llm.invoke([
                ("system", system),
                ("user", user),
            ])

            content = raw.content if hasattr(raw, "content") else str(raw)
            data = extract_json_block(content)
            data = normalize_response_dict(data)

            # 强制覆盖 intent，避免模型乱改
            data["intent"] = intent
            if intent in ("ask_about_story", "unsafety", "end_chat"):
                data["story_text"] = ""
                data["should_save"] = False

            if not data["choices"]:
                data["choices"] = fill_default_choices(intent)

            result = to_schema(ChatResponse, data)
            return post_process_result(result, intent)

        except Exception as second_error:
            raise RuntimeError(
                f"结构化输出失败。first_error={first_error}; second_error={second_error}"
            )