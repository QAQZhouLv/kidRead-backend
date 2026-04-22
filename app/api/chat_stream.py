import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.stream_runner import run_story_stream
from app.core.runtime import build_runtime
from app.core.security import AuthError, get_current_user_from_ws
from app.db.session import SessionLocal
from app.schemas.chat import ChatRequest
from app.services.chat_context_service import update_session_context_snapshot
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
            runtime = build_runtime(db)

            runtime.message_repo.create_user_message(
                user_id=current_user.id,
                scene=req.scene,
                story_id=req.story_id or 0,
                session_id=req.session_id,
                input_mode=req.input_mode,
                user_text=req.text,
            )

            result = await run_story_stream(req, emit, user_id=current_user.id)

            runtime.message_repo.create_assistant_message(
                user_id=current_user.id,
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

            assistant_text = "\n".join([result.lead_text, result.story_text, result.guide_text])
            context_payload = {
                "session_id": req.session_id,
                "snapshot": getattr(result, "_context_snapshot", {}) or {},
                "guard_result": getattr(result, "_guard_result", None),
                "user_id": current_user.id,
            }
            title_payload = {
                "session_id": req.session_id,
                "user_text": req.text,
                "assistant_text": assistant_text,
                "user_id": current_user.id,
            }

            if runtime.flags.use_async_side_effects:
                runtime.task_queue.enqueue("auto_title_session", title_payload)
                runtime.task_queue.enqueue("update_context_snapshot", context_payload)
            else:
                auto_title_session_if_needed(
                    db=db,
                    user_id=current_user.id,
                    session_id=req.session_id,
                    user_text=req.text,
                    assistant_text=assistant_text,
                )
                update_session_context_snapshot(
                    db=db,
                    session_id=req.session_id,
                    snapshot=context_payload["snapshot"],
                    guard_result=context_payload["guard_result"],
                    user_id=current_user.id,
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
