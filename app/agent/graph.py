from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.tools import classify_intent_tool
from app.db.session import SessionLocal
from app.schemas.chat import ChatRequest
from app.services.chat_context_service import enrich_chat_request_from_db


class ChatAgentState(TypedDict, total=False):
    req: ChatRequest
    user_id: int | None
    intent: str
    skill: Literal["create", "continue", "qa", "adjust", "unsafe", "end"]
    snapshot: dict[str, Any]


def _intent_to_skill(intent: str) -> Literal["create", "continue", "qa", "adjust", "unsafe", "end"]:
    mapping = {
        "create_story": "create",
        "continue_story": "continue",
        "ask_about_story": "qa",
        "adjust_story": "adjust",
        "unsafety": "unsafe",
        "end_chat": "end",
    }
    return mapping.get(intent, "continue")


def load_context_node(state: ChatAgentState) -> ChatAgentState:
    req = state["req"]
    db = SessionLocal()
    try:
        snapshot = enrich_chat_request_from_db(db=db, req=req, user_id=state.get("user_id"))
    finally:
        db.close()
    return {"req": req, "snapshot": snapshot}


def route_intent_node(state: ChatAgentState) -> ChatAgentState:
    req = state["req"]
    intent = classify_intent_tool.invoke({
        "scene": req.scene,
        "user_text": req.text,
    })
    return {
        "intent": intent,
        "skill": _intent_to_skill(intent),
    }


def build_prepare_graph():
    builder = StateGraph(ChatAgentState)
    builder.add_node("load_context", load_context_node)
    builder.add_node("route_intent", route_intent_node)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "route_intent")
    builder.add_edge("route_intent", END)
    return builder.compile()


PREPARE_CHAT_GRAPH = build_prepare_graph()


def prepare_chat_state(req: ChatRequest, *, user_id: int | None = None) -> ChatAgentState:
    return PREPARE_CHAT_GRAPH.invoke({
        "req": req,
        "user_id": user_id,
    })
