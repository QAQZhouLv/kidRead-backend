from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.tts_service import synthesize_text_to_file

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSSynthesizeRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"


@router.post("/synthesize")
async def synthesize_tts_api(data: TTSSynthesizeRequest):
    try:
        return await synthesize_text_to_file(
            text=data.text,
            voice=data.voice,
            rate=data.rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
