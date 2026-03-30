import hashlib
from pathlib import Path

from app.core.config import HTTP_PUBLIC_BASE_URL, TTS_OUTPUT_DIR

try:
    import edge_tts
except Exception as exc:  # pragma: no cover
    edge_tts = None
    EDGE_TTS_IMPORT_ERROR = exc
else:
    EDGE_TTS_IMPORT_ERROR = None

TTS_DIR = Path(TTS_OUTPUT_DIR)
TTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_cache_name(text: str, voice: str, rate: str) -> str:
    raw = f"{voice}|{rate}|{text}".encode("utf-8")
    return hashlib.md5(raw).hexdigest() + ".mp3"


async def synthesize_text_to_file(text: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%") -> dict:
    if not text or not text.strip():
        raise ValueError("text 不能为空")

    if edge_tts is None:
        raise RuntimeError(f"edge-tts 未安装: {EDGE_TTS_IMPORT_ERROR}")

    filename = _build_cache_name(text.strip(), voice, rate)
    output_path = TTS_DIR / filename

    if not output_path.exists():
        communicate = edge_tts.Communicate(text=text.strip(), voice=voice, rate=rate)
        await communicate.save(str(output_path))

    relative_url = f"/static/tts/{filename}"
    absolute_url = f"{HTTP_PUBLIC_BASE_URL}{relative_url}" if HTTP_PUBLIC_BASE_URL else relative_url

    return {
        "audio_url": relative_url,
        "absolute_audio_url": absolute_url,
        "filename": filename,
    }
