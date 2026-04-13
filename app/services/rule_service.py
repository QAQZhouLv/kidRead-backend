import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def _load_json(filename: str):
    with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


AGE_RULES = _load_json("age_rules.json")
DIFFICULTY_RULES = _load_json("difficulty_rules.json")
SAFETY_RULES = _load_json("safety_rules.json")


def normalize_age_group(age: int) -> str:
    if age <= 5:
        return "3-5"
    if age <= 8:
        return "6-8"
    return "9-12"


def get_age_rule(age: int):
    return AGE_RULES[normalize_age_group(age)]


def get_difficulty_rule(level: str | None):
    return DIFFICULTY_RULES.get(level or "L2", DIFFICULTY_RULES["L2"])


def get_safety_rule():
    return SAFETY_RULES
