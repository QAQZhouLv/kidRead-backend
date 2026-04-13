import re
from app.services.rule_service import get_age_rule, get_difficulty_rule, get_safety_rule, normalize_age_group


def avg_sentence_length(text: str) -> float:
    parts = re.split(r"[。！？!?]", text or "")
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return 0.0
    return sum(len(p) for p in parts) / len(parts)


def paragraph_count(text: str) -> int:
    return len([p for p in (text or "").split("\n") if p.strip()])


def keyword_hit(text: str, keywords: list[str]) -> list[str]:
    text = text or ""
    return [kw for kw in keywords if kw in text]


def evaluate_content(age: int, difficulty_level: str, text: str) -> dict:
    age_rule = get_age_rule(age)
    diff_rule = get_difficulty_rule(difficulty_level)
    safety_rule = get_safety_rule()

    risks: list[str] = []

    if paragraph_count(text) > age_rule["max_paragraphs"]:
        risks.append("too_many_paragraphs")

    if avg_sentence_length(text) > diff_rule["avg_sentence_len_max"]:
        risks.append("too_complex")

    hard_hits = keyword_hit(text, safety_rule["forbidden_keywords"])
    if hard_hits:
        risks.append("forbidden_theme")

    soft_hits = keyword_hit(text, safety_rule["soft_risk_keywords"])
    if soft_hits:
        risks.append("soft_risk_theme")

    need_rewrite = any(tag in risks for tag in ("forbidden_theme", "too_complex", "too_many_paragraphs"))

    return {
        "passed": not need_rewrite,
        "target_age": normalize_age_group(age),
        "difficulty_level": difficulty_level or "L2",
        "risk_tags": risks,
        "hard_hits": hard_hits,
        "soft_hits": soft_hits,
        "need_rewrite": need_rewrite,
    }


def build_rewrite_instruction(guard_result: dict) -> str:
    risk_tags = guard_result.get("risk_tags", [])
    risk_text = ", ".join(risk_tags) if risk_tags else "无"
    return (
        "请在不改变核心情节方向的前提下，将内容改写得更适合目标年龄儿童，"
        "语言更简单、句子更短、情节更温和，并修正这些问题："
        f"{risk_text}。"
    )
