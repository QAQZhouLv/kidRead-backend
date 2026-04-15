import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.stream_runner import run_story_stream
from app.core.security import AuthError, get_current_user_from_ws
from app.db.session import SessionLocal
from app.schemas.chat import ChatRequest
from app.schemas.message import StoryMessageCreateAssistant, StoryMessageCreateUser
from app.services.message_service import create_assistant_message, create_user_message
from app.services.session_service import auto_title_session_if_needed

router = APIRouter(tags=["chat-stream"])


@router.websocket("/ws/chat/stream")
async def chat_stream(websocket: WebSocket):
    db = SessionLocal()

    try:
        current_user = get_current_user_from_ws(db, websocket)
    except AuthError as exc:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False))
        await websocket.close(code=4401)
        db.close()
        return

    await websocket.accept()

    async def emit(payload):
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            req = ChatRequest(**data)

            create_user_message(
                db,
                StoryMessageCreateUser(
                    scene=req.scene,
                    story_id=req.story_id or 0,
                    session_id=req.session_id,
                    input_mode=req.input_mode,
                    user_text=req.text,
                ),
                user_id=current_user.id,
            )

            result = await run_story_stream(req, emit)

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
                ),
                user_id=current_user.id,
            )

            auto_title_session_if_needed(
                db=db,
                user_id=current_user.id,
                session_id=req.session_id,
                user_text=req.text,
                assistant_text=f"{result.lead_text}\n{result.story_text}\n{result.guide_text}",
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await emit({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
