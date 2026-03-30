import json
import re
from typing import Any, Dict, Type, TypeVar

from pydantic import ValidationError

T = TypeVar("T")


def extract_json_block(text: str) -> Dict[str, Any]:
    """
    从模型返回文本里尽量提取 JSON。
    1. 纯 JSON
    2. ```json ... ``` 包裹
    3. 文本里夹了 JSON
    """
    text = text.strip()

    # 1) 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) 提取 ```json ... ```
    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1)
        return json.loads(candidate)

    # 3) 提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        return json.loads(candidate)

    raise ValueError(f"未找到可解析的 JSON。原始输出：{text}")


def normalize_response_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    对字段做兜底清洗，避免模型缺字段或类型不稳。
    """
    result = {
        "intent": str(data.get("intent", "")).strip(),
        "lead_text": str(data.get("lead_text", "")).strip(),
        "story_text": str(data.get("story_text", "")).strip(),
        "guide_text": str(data.get("guide_text", "")).strip(),
        "choices": data.get("choices", []),
        "should_save": bool(data.get("should_save", False)),
        "save_mode": str(data.get("save_mode", "append")).strip() or "append",
    }

    if not isinstance(result["choices"], list):
        result["choices"] = []

    result["choices"] = [
        str(x).strip() for x in result["choices"] if str(x).strip()
    ][:4]

    return result


def to_schema(schema_cls: Type[T], data: Dict[str, Any]) -> T:
    """
    dict -> Pydantic schema
    """
    try:
        return schema_cls(**data)
    except ValidationError as e:
        raise ValueError(f"结构化校验失败：{e}")