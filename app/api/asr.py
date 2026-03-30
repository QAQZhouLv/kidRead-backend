import base64
import json

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
    流式识别 websocket 协议

    前端消息格式建议：
    1. {"type":"start"}
    2. {"type":"audio","audio_base64":"..."}
    3. {"type":"audio","audio_base64":"..."}
    4. {"type":"stop"}

    服务端返回：
    - {"type":"ready"}
    - {"type":"partial","text":"..."}
    - {"type":"final","text":"..."}
    - {"type":"done","text":"..."}
    - {"type":"error","message":"..."}
    """
    await websocket.accept()

    current_text = ""

    async def on_partial(text: str):
        nonlocal current_text
        if text:
            current_text = text
        await websocket.send_text(json.dumps({
            "type": "partial",
            "text": current_text or ""
        }, ensure_ascii=False))

    async def on_final(text: str):
        nonlocal current_text
        if text:
            current_text = text
        await websocket.send_text(json.dumps({
            "type": "final",
            "text": current_text or ""
        }, ensure_ascii=False))

    bridge = ASRStreamBridge(
        on_partial=on_partial,
        on_final=on_final,
    )

    try:
        await bridge.start()

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "start":
                await websocket.send_text(json.dumps({
                    "type": "ready"
                }, ensure_ascii=False))

            elif msg_type == "audio":
                audio_base64 = data.get("audio_base64", "")
                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                    await bridge.send_audio_frame(audio_bytes)

            elif msg_type == "stop":
                await bridge.stop()
                await websocket.send_text(json.dumps({
                    "type": "done",
                    "text": current_text
                }, ensure_ascii=False))
                break

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"unknown message type: {msg_type}"
                }, ensure_ascii=False))

    except WebSocketDisconnect:
        try:
            await bridge.stop()
        except Exception:
            pass

    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }, ensure_ascii=False))
        except Exception:
            pass

        try:
            await bridge.stop()
        except Exception:
            pass