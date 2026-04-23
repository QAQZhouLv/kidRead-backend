import json
import re
from typing import Any, Dict, Optional, Tuple

from app.agent.graph import prepare_chat_state
from app.agent.llm import get_chat_model
from app.agent.runner import (
    build_history_text,
    build_skill_instruction,
    build_story_reference_block,
    build_story_reference_rules,
    call_tool_by_intent,
    evaluate_and_maybe_rewrite,
    fill_default_choices,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rule_service import normalize_age_group

# Prefer the new [[TAG]] protocol, but keep legacy <TAG> compatibility so
# partially migrated prompts / cached model habits do not leak raw markers.
OPEN_TAGS = {
    "[[LEAD]]": "lead",
    "[[STORY]]": "story",
    "[[GUIDE]]": "guide",
    "[[META]]": "meta",
    "<LEAD>": "lead",
    "<STORY>": "story",
    "<GUIDE>": "guide",
    "<META>": "meta",
}
CLOSE_TAGS = {
    "lead": ["[[/LEAD]]", "</LEAD>"],
    "story": ["[[/STORY]]", "</STORY>"],
    "guide": ["[[/GUIDE]]", "</GUIDE>"],
    "meta": ["[[/META]]", "</META>"],
}
MAX_TAG_LEN = max(
    max(len(k) for k in OPEN_TAGS.keys()),
    max(len(v) for values in CLOSE_TAGS.values() for v in values),
)
MARKER_RE = re.compile(
    r"\[\[(?:/?LEAD|/?STORY|/?GUIDE|/?META)\]\]|</?(?:LEAD|STORY|GUIDE|META)>"
)


def _compact_block(value: Any) -> str:
    if value is None:
        return "无"
    if isinstance(value, str):
        return value or "无"
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(value)



def extract_chunk_text(chunk: Any) -> str:
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



def build_stream_messages(req: ChatRequest, intent: str, tool_result: str, skill: str):
    history_block = build_history_text(req)
    draft_story = (req.session_draft_content or "").strip()
    story_spec = req.story_spec or {}
    story_state = req.story_state or {}
    story_summary = req.story_summary or {}
    story_reference_block = build_story_reference_block(req)
    story_reference_rules = build_story_reference_rules(req)

    system = f"""
你是儿童故事共创助手，也是一个受控技能节点。

技能说明：
{build_skill_instruction(skill)}

你现在必须按“标签协议”输出内容，不能输出 JSON 主体，不能输出 markdown，不能输出解释。

你必须严格按照下面顺序输出：
[[LEAD]]这里写承接语[[/LEAD]]
[[STORY]]这里写故事正文[[/STORY]]
[[GUIDE]]这里写下一步引导[[/GUIDE]]
[[META]]{{"choices":["选项1","选项2","选项3"],"should_save":true,"save_mode":"append"}}[[/META]]

硬性要求：
1. 内容适合 {req.age} 岁儿童，年龄档为 {normalize_age_group(req.age)}。
2. 语言温和、具体、易理解。
3. 必须保持角色、称呼、设定、情节前后连贯。
4. lead 只写承接用户这句话的回应，要有回应感。
5. story 只能写故事正文，不能把解释、提示、选项写进 story。
6. guide 只负责自然引导下一步。
7. META 中只能有：choices / should_save / save_mode。
8. ask_about_story、unsafety、end_chat 时，story 必须为空。
9. end_chat 时只做礼貌收尾，不开启新情节。
10. 在 bookchat 场景下，{story_reference_rules}
11. 不要输出任何标签以外的额外文字。
12. 所有标签必须闭合；如果出错，请优先补齐闭合标签，而不是输出解释。
13. 不要重复输出标签名，不要把 [[STORY]]、[[GUIDE]]、[[META]] 当正文内容输出。

当前 scene：{req.scene}
当前 intent：{intent}
""".strip()

    user = f"""
〖用户本轮输入〗
{req.text}

〖story_spec（静态设定）〗
{_compact_block(story_spec)}

〖story_state（动态剧情台账）〗
{_compact_block(story_state)}

〖story_summary（压缩摘要）〗
{_compact_block(story_summary)}

{story_reference_block}

〖本次会话草稿（第二优先级）〗
{draft_story if draft_story else '无'}

〖最近聊天记录（仅补充参考）〗
{history_block}

〖工具结果〗
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



def _strip_protocol_markers(text: str) -> str:
    return MARKER_RE.sub("", text or "")


class TagStreamParser:
    def __init__(self, emit):
        self.emit = emit
        self.buffer = ""
        self.raw_output = ""
        self.current_section: Optional[str] = None
        self.lead_text = ""
        self.story_text = ""
        self.guide_text = ""
        self.meta_text = ""
        self.started_sections = set()

    async def feed(self, text: str):
        if not text:
            return
        self.raw_output += text
        self.buffer += text
        await self._drain()

    async def finalize(self):
        await self._drain(final=True)

    def _find_next_open_tag(self) -> Optional[Tuple[str, str, str]]:
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

    def _find_next_boundary(self, section: str):
        best = None  # (idx, kind, token, next_section)
        for close_tag in CLOSE_TAGS[section]:
            idx = self.buffer.find(close_tag)
            if idx != -1 and (best is None or idx < best[0]):
                best = (idx, "close", close_tag, None)
        for open_tag, next_section in OPEN_TAGS.items():
            idx = self.buffer.find(open_tag)
            if idx != -1 and (best is None or idx < best[0]):
                best = (idx, "open", open_tag, next_section)
        return best

    async def _start_section(self, section: str):
        self.current_section = section
        if section in ("lead", "story", "guide") and section not in self.started_sections:
            self.started_sections.add(section)
            await self.emit({"type": "section_start", "section": section})

    async def _append_and_emit(self, section: str, text: str):
        text = _strip_protocol_markers(text)
        if not text:
            return
        if section == "lead":
            self.lead_text += text
            await self.emit({"type": "section_delta", "section": "lead", "delta": text})
            return
        if section == "story":
            self.story_text += text
            await self.emit({"type": "section_delta", "section": "story", "delta": text})
            return
        if section == "guide":
            self.guide_text += text
            await self.emit({"type": "section_delta", "section": "guide", "delta": text})
            return
        if section == "meta":
            self.meta_text += text

    async def _drain(self, final: bool = False):
        while True:
            if self.current_section is None:
                matched = self._find_next_open_tag()
                if matched is None:
                    keep = MAX_TAG_LEN - 1
                    if final:
                        self.buffer = ""
                    elif len(self.buffer) > keep:
                        self.buffer = self.buffer[-keep:]
                    return

                prefix, tag_text, section = matched
                # Drop anything before the next valid tag. It is malformed protocol noise.
                self.buffer = self.buffer[len(prefix):]
                self.buffer = self.buffer[len(tag_text):]
                await self._start_section(section)
                continue

            boundary = self._find_next_boundary(self.current_section)
            if boundary is None:
                keep = MAX_TAG_LEN - 1
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

            idx, kind, token, next_section = boundary
            content = self.buffer[:idx]
            if content:
                await self._append_and_emit(self.current_section, content)

            self.buffer = self.buffer[idx + len(token):]

            if kind == "close":
                self.current_section = None
                continue

            # A new open tag appeared before the current section's close tag.
            # Treat it as malformed-but-recoverable output: implicitly close the
            # current section and switch to the new one instead of leaking markers.
            self.current_section = None
            await self._start_section(next_section)
            continue



def _regex_extract_section(raw_text: str, section: str) -> str:
    patterns = {
        "lead": [r"\[\[LEAD\]\](.*?)\[\[/LEAD\]\]", r"<LEAD>(.*?)</LEAD>"],
        "story": [r"\[\[STORY\]\](.*?)\[\[/STORY\]\]", r"<STORY>(.*?)</STORY>"],
        "guide": [r"\[\[GUIDE\]\](.*?)\[\[/GUIDE\]\]", r"<GUIDE>(.*?)</GUIDE>"],
        "meta": [r"\[\[META\]\](.*?)\[\[/META\]\]", r"<META>(.*?)</META>"],
    }
    for p in patterns[section]:
        m = re.search(p, raw_text, flags=re.DOTALL)
        if m:
            return _strip_protocol_markers(m.group(1)).strip()
    return ""



def _salvage_if_needed(parser: TagStreamParser):
    if not parser.raw_output:
        return
    if not parser.lead_text:
        parser.lead_text = _regex_extract_section(parser.raw_output, "lead")
    if not parser.story_text:
        parser.story_text = _regex_extract_section(parser.raw_output, "story")
    if not parser.guide_text:
        parser.guide_text = _regex_extract_section(parser.raw_output, "guide")
    if not parser.meta_text:
        parser.meta_text = _regex_extract_section(parser.raw_output, "meta")
    parser.lead_text = _strip_protocol_markers(parser.lead_text).strip()
    parser.story_text = _strip_protocol_markers(parser.story_text).strip()
    parser.guide_text = _strip_protocol_markers(parser.guide_text).strip()
    parser.meta_text = _strip_protocol_markers(parser.meta_text).strip()



def _post_process_stream_result(intent: str, result: ChatResponse) -> ChatResponse:
    result.intent = intent
    result.save_mode = result.save_mode or "append"
    if intent in ("ask_about_story", "unsafety", "end_chat"):
        result.story_text = ""
        result.should_save = False
    if not result.choices:
        result.choices = fill_default_choices(intent)
    result.choices = result.choices[:4]
    return result


async def run_story_stream(req: ChatRequest, emit, *, user_id: int | None = None):
    prepared = prepare_chat_state(req, user_id=user_id)
    intent = prepared["intent"]
    skill = prepared.get("skill", "continue")

    await emit({"type": "start"})
    await emit({"type": "intent", "intent": intent})

    tool_result = call_tool_by_intent(req, intent)
    system, user = build_stream_messages(req, intent, tool_result, skill)

    llm = get_chat_model()
    parser = TagStreamParser(emit)

    async for chunk in llm.astream([("system", system), ("user", user)]):
        delta_text = extract_chunk_text(chunk)
        if delta_text:
            await parser.feed(delta_text)

    await parser.finalize()
    _salvage_if_needed(parser)

    meta = normalize_stream_meta(parser.meta_text, intent)
    result = ChatResponse(
        intent=intent,
        lead_text=parser.lead_text.strip(),
        story_text=parser.story_text.strip(),
        guide_text=parser.guide_text.strip(),
        choices=meta["choices"],
        should_save=meta["should_save"],
        save_mode=meta["save_mode"],
    )
    result = _post_process_stream_result(intent, result)
    result, guard = evaluate_and_maybe_rewrite(req, result)

    object.__setattr__(result, "_context_snapshot", prepared.get("snapshot") or {})
    if guard is not None:
        object.__setattr__(result, "_guard_result", guard)

    if result.story_text != parser.story_text.strip():
        await emit({"type": "section_replace", "section": "story", "content": result.story_text})

    await emit(
        {
            "type": "meta",
            "choices": result.choices,
            "should_save": result.should_save,
            "save_mode": result.save_mode,
        }
    )
    await emit({"type": "done"})
    return result
