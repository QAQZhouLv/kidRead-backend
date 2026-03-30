from langchain_openai import ChatOpenAI
from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def get_chat_model() -> ChatOpenAI:
    # 通用 LLM 模型。
    
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=0.3,
        max_retries=2,
    )


def get_json_model() -> ChatOpenAI:

    # 更偏向稳定 JSON 输出的模型实例。

    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=0.1,
        max_retries=2,
    )