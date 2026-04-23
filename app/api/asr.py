import base64
import json
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException

from app.services.asr_stream_service import ASRStreamBridge, transcribe_file_bytes

router = APIRouter(tags=["asr"])


@router.post("/api/asr")
async def asr_upload(file: UploadFile = File(...)):
    """
    上传整段音频文件识别
    """
    try:
        content = await file.read()
        text = await transcribe_file_bytes(content)
        return {"text": text or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/asr/stream")
async def asr_stream(websocket: WebSocket):
    """
    持久连接版流式识别 websocket 协议

    新协议：
    - {"type":"begin_utterance","utterance_id":"..."}
    - {"type":"audio","utterance_id":"...","audio_base64":"..."}
    - {"type":"end_utterance","utterance_id":"..."}
    - {"type":"reset"}
    - {"type":"ping"}

    兼容旧协议：
    - {"type":"start"}
    - {"type":"audio","audio_base64":"..."}
    - {"type":"stop"}

    服务端返回：
    - {"type":"ready"}
    - {"type":"utterance_ready","utterance_id":"..."}
    - {"type":"partial","utterance_id":"...","text":"..."}
    - {"type":"final","utterance_id":"...","text":"..."}
    - {"type":"done","utterance_id":"...","text":"..."}
    - {"type":"reset_done"}
    - {"type":"pong"}
    - {"type":"error","message":"..."}
    """
    await websocket.accept()

    active_bridge: Optional[ASRStreamBridge] = None
    active_utterance_id: Optional[str] = None
    current_text = ""

    async def safe_send(payload: dict):
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def cleanup_bridge(send_done: bool = False):
        nonlocal active_bridge, active_utterance_id, current_text
        if not active_bridge:
            active_utterance_id = None
            current_text = ""
            return

        utterance_id = active_utterance_id
        bridge = active_bridge
        active_bridge = None
        active_utterance_id = None

        try:
            await bridge.stop()
        except Exception:
            pass

        final_text = bridge.final_text or current_text or ""
        current_text = ""

        if send_done and utterance_id:
            await safe_send({
                "type": "done",
                "utterance_id": utterance_id,
                "text": final_text,
            })

    async def start_utterance(utterance_id: str):
        nonlocal active_bridge, active_utterance_id, current_text

        if active_bridge:
            await cleanup_bridge(send_done=False)

        current_text = ""
        active_utterance_id = utterance_id

        async def on_partial(text: str):
            nonlocal current_text
            if utterance_id != active_utterance_id:
                return
            if text:
                current_text = text
            await safe_send({
                "type": "partial",
                "utterance_id": utterance_id,
                "text": current_text or "",
            })

        async def on_final(text: str):
            nonlocal current_text
            if utterance_id != active_utterance_id:
                return
            if text:
                current_text = text
            await safe_send({
                "type": "final",
                "utterance_id": utterance_id,
                "text": current_text or "",
            })

        bridge = ASRStreamBridge(on_partial=on_partial, on_final=on_final)
        await bridge.start()
        active_bridge = bridge

        await safe_send({
            "type": "utterance_ready",
            "utterance_id": utterance_id,
        })

    await safe_send({"type": "ready"})

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "ping":
                await safe_send({"type": "pong"})
                continue

            if msg_type == "reset":
                await cleanup_bridge(send_done=False)
                await safe_send({"type": "reset_done"})
                continue

            if msg_type == "start":
                await safe_send({"type": "ready"})
                continue

            if msg_type == "begin_utterance":
                utterance_id = data.get("utterance_id") or f"utt_{uuid.uuid4().hex}"
                await start_utterance(utterance_id)
                continue

            if msg_type == "audio":
                utterance_id = data.get("utterance_id") or active_utterance_id
                audio_base64 = data.get("audio_base64", "")

                if not audio_base64:
                    continue

                if not active_bridge:
                    if not utterance_id:
                        await safe_send({
                            "type": "error",
                            "message": "no active utterance",
                        })
                        continue
                    await start_utterance(utterance_id)

                if utterance_id and active_utterance_id and utterance_id != active_utterance_id:
                    await safe_send({
                        "type": "error",
                        "message": f"utterance mismatch: active={active_utterance_id}, got={utterance_id}",
                    })
                    continue

                audio_bytes = base64.b64decode(audio_base64)
                await active_bridge.send_audio_frame(audio_bytes)
                continue

            if msg_type in ("end_utterance", "stop"):
                utterance_id = data.get("utterance_id") or active_utterance_id
                if utterance_id and active_utterance_id and utterance_id != active_utterance_id:
                    await safe_send({
                        "type": "error",
                        "message": f"utterance mismatch: active={active_utterance_id}, got={utterance_id}",
                    })
                    continue

                await cleanup_bridge(send_done=True)
                continue

            await safe_send({
                "type": "error",
                "message": f"unknown message type: {msg_type}",
            })

    except WebSocketDisconnect:
        try:
            await cleanup_bridge(send_done=False)
        except Exception:
            pass

    except Exception as e:
        try:
            await safe_send({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
        try:
            await cleanup_bridge(send_done=False)
        except Exception:
            pass
