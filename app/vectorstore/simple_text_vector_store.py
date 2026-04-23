from __future__ import annotations

import re

from app.vectorstore.base import StoryVectorStore

_QUERY_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,}")
_STOPWORDS = {"这个", "那个", "怎么", "为什么", "然后", "继续", "故事", "一下", "可以", "我们", "他们", "你们", "是不是"}


def _split_paragraphs(full_content: str) -> list[str]:
    paragraphs = [p.strip() for p in (full_content or "").replace("\r", "").split("\n")]
    return [p for p in paragraphs if p]


def _extract_keywords(query_text: str) -> list[str]:
    result = []
    seen = set()
    for token in _QUERY_TOKEN_RE.findall(query_text or ""):
        token = token.strip().lower()
        if len(token) < 2 or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result[:8]


def _score_paragraph(paragraph: str, query_text: str, keywords: list[str]) -> int:
    if not paragraph:
        return 0
    paragraph_lower = paragraph.lower()
    score = 0
    raw_query = (query_text or "").strip()
    if raw_query and raw_query in paragraph:
        score += 5
    for keyword in keywords:
        count = paragraph_lower.count(keyword)
        if count:
            score += count * 2
    return score


class SimpleTextVectorStore(StoryVectorStore):
    def search_story_chunks(
        self,
        *,
        story_id: int,
        query_text: str,
        full_content: str,
        top_k: int = 3,
    ) -> list[str]:
        paragraphs = _split_paragraphs(full_content)
        keywords = _extract_keywords(query_text)
        if not paragraphs:
            return []

        scored: list[tuple[int, int, str]] = []
        for idx, para in enumerate(paragraphs):
            score = _score_paragraph(para, query_text, keywords)
            if score > 0:
                scored.append((score, idx, para))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = scored[:top_k]
        selected.sort(key=lambda item: item[1])
        return [item[2] for item in selected]

    def upsert_story_chunks(self, *, story_id: int, chunks: list[str]) -> None:
        return None

    def delete_story_chunks(self, *, story_id: int) -> None:
        return None
