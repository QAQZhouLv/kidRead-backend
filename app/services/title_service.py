import re
from langchain_core.output_parsers import StrOutputParser
from app.agent.llm import get_chat_model


DEFAULT_SESSION_TITLES = {"新对话", "新创作", "历史会话"}
DEFAULT_STORY_TITLES = {"未命名故事", "我的新故事"}


def _clean_title(text: str, fallback: str) -> str:
    value = (text or "").strip().replace("\n", " ")
    value = re.sub(r"[《》\"“”‘’]+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -—_，。；：")
    if not value:
        return fallback
    return value[:18]


def build_fast_story_title(content: str, fallback: str = "我的新故事") -> str:
    text = (content or "").strip()
    if not text:
        return fallback

    first = text.split("\n")[0].strip()
    first = re.sub(r"[，。！？、；：“”‘’（）()《》【】\[\]<>]", "", first)
    first = re.sub(r"\s+", "", first)

    if len(first) >= 6:
        return first[:12]
    return fallback

def generate_session_title(scene: str, user_text: str, assistant_text: str, fallback: str = "新对话") -> str:
    llm = get_chat_model()
    prompt = f"""
你是标题总结助手。
请根据下面内容，为一次儿童故事会话生成一个简短自然的标题。

要求：
1. 只输出标题本身
2. 不要加书名号
3. 6~14字优先
4. 要具体，不要输出“新对话”“本次创作”“故事会话”

scene: {scene}
用户首轮输入: {user_text}
AI回复摘要: {assistant_text[:300]}
""".strip()

    chain = llm | StrOutputParser()
    try:
        result = chain.invoke(prompt)
        return _clean_title(result, fallback)
    except Exception:
        return fallback


def generate_story_title(content: str, age: int = 6, fallback: str = "我的新故事") -> str:
    llm = get_chat_model()
    prompt = f"""
你是童书命名助手。
请为下面这个儿童故事生成一个正式书名。

要求：
1. 只输出书名本身
2. 6~14字优先
3. 要像绘本或童话书名
4. 不要输出“未命名故事”“我的新故事”
5. 适合 {age} 岁儿童

故事正文：
{(content or "")[:2000]}
""".strip()

    chain = llm | StrOutputParser()
    try:
        result = chain.invoke(prompt)
        return _clean_title(result, fallback)
    except Exception:
        return fallback