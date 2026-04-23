
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

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

TTS_META_DIR = TTS_DIR.parent / "tts_meta"
TTS_META_DIR.mkdir(parents=True, exist_ok=True)

_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;\n]?", re.UNICODE)
_SPEAKABLE_RE = re.compile(r'[\s"“”‘’《》〈〉「」『』〖〗（）()<>、，,。！？!?；;：:\-—…·~]+')


def _build_cache_key(text: str, voice: str, rate: str) -> str:
    raw = f"{voice}|{rate}|{text}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _build_message_key(
    lead_text: str,
    story_text: str,
    guide_text: str,
    voice: str,
    rate: str,
    segment_char_limit: int,
    max_sentences_per_segment: int,
) -> str:
    raw = json.dumps(
        {
            "lead_text": lead_text or "",
            "story_text": story_text or "",
            "guide_text": guide_text or "",
            "voice": voice,
            "rate": rate,
            "segment_char_limit": segment_char_limit,
            "max_sentences_per_segment": max_sentences_per_segment,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _has_speakable_content(text: str) -> bool:
    cleaned = _SPEAKABLE_RE.sub("", str(text or ""))
    return bool(cleaned.strip())


def split_text_to_sentences(text: str) -> List[str]:
    normalized = str(text or "").replace("\r", "").strip()
    if not normalized:
        return []
    parts = _SENTENCE_RE.findall(normalized)
    if not parts:
        return [normalized]
    return [part.strip() for part in parts if part and part.strip()]


def split_sentences_to_segments(
    sentences: List[str],
    max_chars: int = 90,
    max_sentences_per_segment: int = 3,
) -> List[Dict[str, Any]]:
    if not sentences:
        return []

    segments: List[Dict[str, Any]] = []
    current: List[str] = []
    start_index = 0
    current_len = 0

    for idx, sentence in enumerate(sentences):
        sentence_len = len(sentence)
        should_flush = False
        if current and len(current) >= max_sentences_per_segment:
            should_flush = True
        elif current and current_len + sentence_len > max_chars:
            should_flush = True

        if should_flush:
            segments.append(
                {
                    "text": "".join(current).strip(),
                    "sentences": current[:],
                    "start_sentence_index": start_index,
                    "end_sentence_index": start_index + len(current) - 1,
                }
            )
            current = []
            start_index = idx
            current_len = 0

        if not current:
            start_index = idx

        current.append(sentence)
        current_len += sentence_len

    if current:
        segments.append(
            {
                "text": "".join(current).strip(),
                "sentences": current[:],
                "start_sentence_index": start_index,
                "end_sentence_index": start_index + len(current) - 1,
            }
        )

    return [seg for seg in segments if seg["text"]]


def _to_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        value = float(value)
    except Exception:
        return 0.0
    if value > 1000:
        return value / 10_000_000.0
    return value


def _extract_boundary_info(chunk: dict) -> dict:
    text = (
        chunk.get("text")
        or chunk.get("Text")
        or chunk.get("word")
        or chunk.get("Word")
        or ""
    )
    text_offset = (
        chunk.get("text_offset")
        or chunk.get("textOffset")
        or chunk.get("offset_text")
        or 0
    )
    duration = (
        chunk.get("duration")
        or chunk.get("Duration")
        or chunk.get("audio_duration")
        or 0
    )
    offset = (
        chunk.get("offset")
        or chunk.get("Offset")
        or chunk.get("audio_offset")
        or 0
    )
    return {
        "text": str(text or ""),
        "text_offset": int(text_offset or 0),
        "start": _to_seconds(offset),
        "duration": _to_seconds(duration),
    }


def _build_sentence_ranges(sentences: List[str]) -> List[dict]:
    ranges = []
    cursor = 0
    for idx, sentence in enumerate(sentences):
        start_char = cursor
        end_char = cursor + len(sentence)
        ranges.append(
            {
                "index": idx,
                "text": sentence,
                "start_char": start_char,
                "end_char": end_char,
            }
        )
        cursor = end_char
    return ranges


def _estimate_timelines_by_length(sentences: List[str], total_duration: float) -> List[dict]:
    if not sentences:
        return []
    safe_total = max(float(total_duration or 0), 0.1)
    weights = [max(len(re.sub(r"\s+", "", s)), 1) for s in sentences]
    all_weight = sum(weights) or len(sentences)
    cursor = 0.0
    result = []
    for idx, sentence in enumerate(sentences):
        if idx == len(sentences) - 1:
            end = safe_total
        else:
            end = cursor + safe_total * (weights[idx] / all_weight)
        result.append(
            {
                "index": idx,
                "text": sentence,
                "start": round(cursor, 3),
                "end": round(max(end, cursor + 0.05), 3),
            }
        )
        cursor = end
    if result:
        result[-1]["end"] = round(max(result[-1]["end"], safe_total), 3)
    return result


def _build_timelines_from_boundaries(
    sentences: List[str], boundaries: List[dict], total_duration: float
) -> List[dict]:
    if not sentences:
        return []
    if not boundaries:
        return _estimate_timelines_by_length(sentences, total_duration)

    sentence_ranges = _build_sentence_ranges(sentences)
    grouped: Dict[int, List[dict]] = {idx: [] for idx in range(len(sentences))}

    for boundary in boundaries:
        pos = int(boundary.get("text_offset", 0))
        target_idx = None
        for item in sentence_ranges:
            if item["start_char"] <= pos < item["end_char"]:
                target_idx = item["index"]
                break
        if target_idx is None and sentence_ranges:
            if pos >= sentence_ranges[-1]["end_char"]:
                target_idx = sentence_ranges[-1]["index"]
            else:
                target_idx = 0
        grouped[target_idx].append(boundary)

    result = []
    fallback = _estimate_timelines_by_length(sentences, total_duration)

    for idx, sentence in enumerate(sentences):
        items = grouped.get(idx) or []
        if items:
            start = min(max(float(x["start"]), 0.0) for x in items)
            end_candidates = [
                max(float(x["start"] + x["duration"]), float(x["start"])) for x in items
            ]
            end = max(end_candidates) if end_candidates else start
            if idx + 1 < len(sentences):
                next_items = grouped.get(idx + 1) or []
                if next_items:
                    next_start = min(max(float(x["start"]), 0.0) for x in next_items)
                    end = min(end, next_start) if end > next_start else end
            if end <= start:
                end = start + 0.05
            result.append(
                {
                    "index": idx,
                    "text": sentence,
                    "start": round(start, 3),
                    "end": round(end, 3),
                }
            )
        else:
            result.append(fallback[idx])

    for idx in range(len(result) - 1):
        if result[idx]["end"] > result[idx + 1]["start"]:
            result[idx]["end"] = round(
                max(result[idx + 1]["start"], result[idx]["start"] + 0.05), 3
            )
        if result[idx]["end"] <= result[idx]["start"]:
            result[idx]["end"] = round(result[idx]["start"] + 0.05, 3)

    if result:
        result[-1]["end"] = round(max(result[-1]["end"], total_duration or result[-1]["end"]), 3)

    return result


async def synthesize_text_to_file(
    text: str,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
) -> dict:
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("text 不能为空")
    if not _has_speakable_content(clean_text):
        raise ValueError("text 没有可朗读内容")
    if edge_tts is None:
        raise RuntimeError(f"edge-tts 未安装: {EDGE_TTS_IMPORT_ERROR}")

    cache_key = _build_cache_key(clean_text, voice, rate)
    audio_filename = f"{cache_key}.mp3"
    meta_filename = f"{cache_key}.json"
    output_path = TTS_DIR / audio_filename
    meta_path = TTS_META_DIR / meta_filename

    if output_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text("utf-8"))
        if meta.get("audio_url"):
            return meta

    communicate = edge_tts.Communicate(text=clean_text, voice=voice, rate=rate)
    audio_bytes = bytearray()
    boundaries: List[dict] = []

    async for chunk in communicate.stream():
        chunk_type = chunk.get("type")
        if chunk_type == "audio":
            audio_bytes.extend(chunk.get("data", b""))
        elif chunk_type in {"WordBoundary", "SentenceBoundary", "word_boundary", "sentence_boundary"}:
            info = _extract_boundary_info(chunk)
            if info["text"]:
                boundaries.append(info)

    if not audio_bytes:
        raise RuntimeError("TTS 未生成音频数据")

    output_path.write_bytes(audio_bytes)
    total_duration = 0.0
    if boundaries:
        total_duration = max((item["start"] + item["duration"] for item in boundaries), default=0.0)

    sentences = split_text_to_sentences(clean_text)
    timelines = _build_timelines_from_boundaries(sentences, boundaries, total_duration)
    if timelines:
        total_duration = max(total_duration, timelines[-1]["end"])
    else:
        total_duration = max(total_duration, 0.1)

    relative_url = f"/static/tts/{audio_filename}"
    absolute_url = f"{HTTP_PUBLIC_BASE_URL}{relative_url}" if HTTP_PUBLIC_BASE_URL else relative_url
    result = {
        "audio_url": relative_url,
        "absolute_audio_url": absolute_url,
        "filename": audio_filename,
        "duration": round(total_duration, 3),
        "sentences": timelines,
    }
    meta_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _build_section_manifest(
    *,
    section: str,
    text: str,
    voice: str,
    rate: str,
    segment_char_limit: int,
    max_sentences_per_segment: int,
) -> Dict[str, Any]:
    sentences = split_text_to_sentences(text)
    segments = split_sentences_to_segments(
        sentences,
        max_chars=segment_char_limit,
        max_sentences_per_segment=max_sentences_per_segment,
    )

    manifest_segments = []
    for idx, segment in enumerate(segments):
        segment_text = segment["text"]
        cache_key = _build_cache_key(segment_text, voice, rate)
        manifest_segments.append(
            {
                "segment_id": f"{section}_{idx}",
                "section": section,
                "segment_index": idx,
                "text": segment_text,
                "cache_key": cache_key,
                "sentence_count": len(segment["sentences"]),
                "start_sentence_index": int(segment["start_sentence_index"]),
                "end_sentence_index": int(segment["end_sentence_index"]),
            }
        )

    return {
        "section": section,
        "text": text or "",
        "sentence_count": len(sentences),
        "segment_count": len(manifest_segments),
        "segments": manifest_segments,
    }


def prepare_message_tts_manifest(
    *,
    lead_text: str = "",
    story_text: str = "",
    guide_text: str = "",
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
    segment_char_limit: int = 90,
    max_sentences_per_segment: int = 3,
) -> Dict[str, Any]:
    normalized = {
        "lead": str(lead_text or "").strip(),
        "story": str(story_text or "").strip(),
        "guide": str(guide_text or "").strip(),
    }

    if not any(_has_speakable_content(value) for value in normalized.values()):
        raise ValueError("message 没有可朗读内容")

    sections = []
    all_segments = []
    order = ["lead", "story", "guide"]

    for section in order:
        text = normalized[section]
        if not _has_speakable_content(text):
            continue
        section_manifest = _build_section_manifest(
            section=section,
            text=text,
            voice=voice,
            rate=rate,
            segment_char_limit=segment_char_limit,
            max_sentences_per_segment=max_sentences_per_segment,
        )
        sections.append(section_manifest)
        all_segments.extend(section_manifest["segments"])

    return {
        "manifest_version": 1,
        "message_key": _build_message_key(
            normalized["lead"],
            normalized["story"],
            normalized["guide"],
            voice,
            rate,
            segment_char_limit,
            max_sentences_per_segment,
        ),
        "voice": voice,
        "rate": rate,
        "segment_char_limit": segment_char_limit,
        "max_sentences_per_segment": max_sentences_per_segment,
        "sections": sections,
        "segments": all_segments,
    }
