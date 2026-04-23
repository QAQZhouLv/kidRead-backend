
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.tts_service import prepare_message_tts_manifest, synthesize_text_to_file

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSSynthesizeRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"


class TTSPrepareMessageRequest(BaseModel):
    lead_text: str = ""
    story_text: str = ""
    guide_text: str = ""
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    segment_char_limit: int = Field(default=90, ge=40, le=240)
    max_sentences_per_segment: int = Field(default=3, ge=1, le=8)


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
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/prepare-message")
async def prepare_message_tts_api(data: TTSPrepareMessageRequest):
    try:
        return prepare_message_tts_manifest(
            lead_text=data.lead_text,
            story_text=data.story_text,
            guide_text=data.guide_text,
            voice=data.voice,
            rate=data.rate,
            segment_char_limit=data.segment_char_limit,
            max_sentences_per_segment=data.max_sentences_per_segment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
