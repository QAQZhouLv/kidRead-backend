import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.stream_runner import run_story_stream
from app.db.session import SessionLocal
from app.schemas.chat import ChatRequest
from app.schemas.message import (
    StoryMessageCreateAssistant,
    StoryMessageCreateUser,
)
from app.services.message_service import (
    create_assistant_message,
    create_user_message,
)

router = APIRouter(tags=["chat-stream"])


@router.websocket("/ws/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()

    db = SessionLocal()

    async def emit(payload):
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            req = ChatRequest(**data)

            # 1. 先存 user message
            create_user_message(
                db,
                StoryMessageCreateUser(
                    scene=req.scene,
                    story_id=req.story_id or 0,
                    session_id=req.session_id,
                    input_mode=req.input_mode,
                    user_text=req.text,
                )
            )

            # 2. 真流式生成
            result = await run_story_stream(req, emit)

            # 3. 最后存 assistant message
            create_assistant_message(
                db,
                StoryMessageCreateAssistant(
                    scene=req.scene,
                    story_id=req.story_id or 0,
                    session_id=req.session_id,
                    intent=result.intent,
                    lead_text=result.lead_text,
                    story_text=result.story_text,
                    guide_text=result.guide_text,
                    choices=result.choices,
                    should_save=result.should_save,
                )
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await emit({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        db.close()