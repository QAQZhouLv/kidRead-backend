from __future__ import annotations

import httpx

from app.core.config import EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL


def _resolve_embeddings_url(base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    if base.endswith("/embeddings"):
        return base
    return f"{base}/embeddings"


def _request_embeddings(inputs: list[str]) -> list[list[float]]:
    if not inputs:
        return []
    if not EMBEDDING_MODEL or not EMBEDDING_API_KEY or not EMBEDDING_BASE_URL:
        return []

    url = _resolve_embeddings_url(EMBEDDING_BASE_URL)
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": inputs,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    items = data.get("data") or []
    vectors: list[list[float]] = []
    for item in items:
        embedding = item.get("embedding") or []
        vectors.append(embedding if isinstance(embedding, list) else [])
    return vectors


def embed_query(text: str) -> list[float]:
    payload_text = (text or "").strip()
    if not payload_text:
        return []
    vectors = _request_embeddings([payload_text])
    return vectors[0] if vectors else []


def embed_texts(texts: list[str]) -> list[list[float]]:
    payload = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not payload:
        return []
    return _request_embeddings(payload)
