from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.runner import run_story_agent

def generate_chat_response(req: ChatRequest) -> ChatResponse:
    return run_story_agent(req)