import json
from typing import Any, Dict, Optional

from app.agent.llm import get_chat_model
from app.agent.runner import (
    build_history_text,
    call_tool_by_intent,
    fill_default_choices,
)
from app.agent.tools import classify_intent_tool
from app.schemas.chat import ChatRequest, ChatResponse


OPEN_TAGS = {
    "<LEAD>": "lead",
    "<STORY>": "story",
    "<GUIDE>": "guide",
    "<META>": "meta",
}

CLOSE_TAGS = {
    "lead": "</LEAD>",
    "story": "</STORY>",
    "guide": "</GUIDE>",
    "meta": "</META>",
}

MAX_OPEN_TAG_LEN = max(len(k) for k in OPEN_TAGS.keys())
MAX_CLOSE_TAG_LEN = max(len(v) for v in CLOSE_TAGS.values())


def extract_chunk_text(chunk: Any) -> str:
    """
    尽量从 LangChain / OpenAI-compatible 的 chunk 中提取文本。
    """
    if chunk is None:
        return ""

    content = getattr(chunk, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "text" in item:
                    parts.append(str(item.get("text", "")))
        return "".join(parts)

    return str(content or "")


def build_stream_messages(req: ChatRequest, intent: str, tool_result: str):
    history_block = build_history_text(req)
    current_story = (req.current_story_content or "").strip()
    draft_story = (req.session_draft_content or "").strip()

    system = f"""
你是儿童故事共创助手。

你现在必须按“标签协议”输出内容，不能输出 JSON 主体，不能输出 markdown，不能输出解释。

你必须严格按照下面顺序输出：

<LEAD>
这里写承接语
</LEAD>
<STORY>
这里写故事正文
</STORY>
<GUIDE>
这里写下一步引导
</GUIDE>
<META>
{{"choices":["选项1","选项2","选项3"],"should_save":true,"save_mode":"append"}}
</META>

硬性要求：
1. 内容适合 {req.age} 岁儿童。
2. 语言温和、具体、易理解。
3. 必须保持角色、称呼、设定、情节前后连贯。
4. lead 只写承接用户这句话的回应，要有回应感，不能总是泛泛地说“好呀我们继续”。
5. story 只能写故事正文，不能把解释、提示、选项写进 story。
6. guide 只负责自然引导下一步。
7. META 中只能有这三个字段：
   - choices: 2~4 个短选项
   - should_save: true / false
   - save_mode: 固定为 "append"
8. 当前 intent 是：{intent}
9. ask_about_story、unsafety、end_chat 时，<STORY></STORY> 必须为空。
10. end_chat 时不要继续讲新故事，只做礼貌收尾。
11. 绝对不要输出任何标签以外的额外文字。
12. 所有标签必须闭合。
13. 如果是 bookchat 续写，优先依据“当前正式正文”和“本次会话草稿”，历史记录只作补充参考。

当前 scene：{req.scene}
当前 intent：{intent}
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


def normalize_stream_meta(meta_text: str, intent: str) -> Dict[str, Any]:
    meta_text = (meta_text or "").strip()

    data: Dict[str, Any] = {}
    if meta_text:
        try:
            data = json.loads(meta_text)
        except Exception:
            data = {}

    choices = data.get("choices", [])
    if not isinstance(choices, list):
        choices = []
    choices = [str(x).strip() for x in choices if str(x).strip()][:4]

    if not choices:
        choices = fill_default_choices(intent)

    should_save = bool(data.get("should_save", False))
    save_mode = str(data.get("save_mode", "append") or "append").strip() or "append"

    if intent in ("ask_about_story", "unsafety", "end_chat"):
        should_save = False

    return {
        "choices": choices,
        "should_save": should_save,
        "save_mode": save_mode,
    }


class TagStreamParser:
    def __init__(self, emit):
        self.emit = emit

        self.buffer = ""
        self.current_section: Optional[str] = None

        self.lead_text = ""
        self.story_text = ""
        self.guide_text = ""
        self.meta_text = ""

        self.started_sections = set()

    async def feed(self, text: str):
        if not text:
            return

        self.buffer += text
        await self._drain()

    async def finalize(self):
        # 把剩余 buffer 尽量处理掉
        await self._drain(final=True)

    async def _drain(self, final: bool = False):
        while True:
            if self.current_section is None:
                matched = self._find_next_open_tag()

                if matched is None:
                    # 没有找到完整开始标签，保留一点尾巴防止标签跨 chunk
                    keep = MAX_OPEN_TAG_LEN - 1
                    if final:
                        self.buffer = ""
                    elif len(self.buffer) > keep:
                        self.buffer = self.buffer[-keep:]
                    return

                prefix, tag_text, section = matched
                # 丢掉标签前的无效前缀
                self.buffer = self.buffer[len(prefix):]
                # 再丢掉开始标签本身
                self.buffer = self.buffer[len(tag_text):]

                self.current_section = section

                if section in ("lead", "story", "guide") and section not in self.started_sections:
                    self.started_sections.add(section)

                    #print(f"\n[section_start] {section}", flush=True)   测试输出用的
                    await self.emit({
                        "type": "section_start",
                        "section": section,
                    })

                continue

            close_tag = CLOSE_TAGS[self.current_section]
            idx = self.buffer.find(close_tag)

            if idx != -1:
                content = self.buffer[:idx]
                if content:
                    await self._append_and_emit(self.current_section, content)
                self.buffer = self.buffer[idx + len(close_tag):]
                self.current_section = None
                continue

            # 没找到完整闭合标签
            keep = len(close_tag) - 1

            if final:
                content = self.buffer
                if content:
                    await self._append_and_emit(self.current_section, content)
                self.buffer = ""
                self.current_section = None
                return

            if len(self.buffer) > keep:
                safe_text = self.buffer[:-keep]
                self.buffer = self.buffer[-keep:]
                if safe_text:
                    await self._append_and_emit(self.current_section, safe_text)
                continue

            return

    def _find_next_open_tag(self):
        best_idx = None
        best_tag_text = None
        best_section = None

        for tag_text, section in OPEN_TAGS.items():
            idx = self.buffer.find(tag_text)
            if idx != -1 and (best_idx is None or idx < best_idx):
                best_idx = idx
                best_tag_text = tag_text
                best_section = section

        if best_idx is None:
            return None

        prefix = self.buffer[:best_idx]
        return prefix, best_tag_text, best_section

    async def _append_and_emit(self, section: str, text: str):
        if not text:
            return

        if section == "lead":
            #测试print(f"[lead] {text}", end="", flush=True)     
            self.lead_text += text
            await self.emit({
                "type": "section_delta",
                "section": "lead",
                "delta": text,
            })
            return

        if section == "story":
            #print(f"[story] {text}", end="", flush=True)   
            self.story_text += text
            await self.emit({
                "type": "section_delta",
                "section": "story",
                "delta": text,
            })
            return

        if section == "guide":
            #测试print(f"[guide] {text}", end="", flush=True)    
            self.guide_text += text
            await self.emit({
                "type": "section_delta",
                "section": "guide",
                "delta": text,
            })
            return

        if section == "meta":
            self.meta_text += text
            return


async def run_story_stream(req: ChatRequest, emit):
    """
    真流式主链路：
    1) 先快速判 intent
    2) 再让模型按标签协议流式输出
    3) 解析 lead/story/guide
    4) 最后发 meta + done
    5) 返回完整 ChatResponse 供入库
    """
    intent = classify_intent_tool.invoke({
        "scene": req.scene,
        "user_text": req.text,
    })

    await emit({"type": "start"})
    await emit({"type": "intent", "intent": intent})

    tool_result = call_tool_by_intent(req, intent)
    system, user = build_stream_messages(req, intent, tool_result)

    llm = get_chat_model()
    parser = TagStreamParser(emit)

    async for chunk in llm.astream([
        ("system", system),
        ("user", user),
    ]):
        delta_text = extract_chunk_text(chunk)
        if delta_text:
            #print(delta_text, end="", flush=True)    原始流式输出, 测试用到
            await parser.feed(delta_text)

    await parser.finalize()

    meta = normalize_stream_meta(parser.meta_text, intent)

    # 对几个特殊 intent 做最后兜底
    story_text = parser.story_text
    if intent in ("ask_about_story", "unsafety", "end_chat"):
        story_text = ""
        meta["should_save"] = False

    await emit({
        "type": "meta",
        "choices": meta["choices"],
        "should_save": meta["should_save"],
        "save_mode": meta["save_mode"],
    })

    await emit({
        "type": "done",
    })

    return ChatResponse(
        intent=intent,
        lead_text=parser.lead_text.strip(),
        story_text=story_text.strip(),
        guide_text=parser.guide_text.strip(),
        choices=meta["choices"],
        should_save=meta["should_save"],
        save_mode=meta["save_mode"],
    )