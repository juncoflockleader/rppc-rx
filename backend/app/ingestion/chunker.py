"""Chunking (design §11.1, §27).

~600-1000 token chunks with 100-150 token overlap, preserving char offsets and
page numbers. Token counts are a heuristic (~4 chars/token) in the MVP; real
counts come later from the model's tokenizer. Splits on paragraph/sentence
boundaries where possible so chunks don't cut mid-sentence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..config import get_settings
from .parser import ParsedDoc

CHARS_PER_TOKEN = 4


@dataclass
class Chunk:
    chunk_index: int
    text: str
    token_count: int
    char_start: int
    char_end: int
    page_start: int
    page_end: int


def _segments(text: str) -> List[tuple]:
    """Yield (start, end) spans on paragraph boundaries (falls back to whole text)."""
    spans = []
    pos = 0
    for para in text.split("\n\n"):
        start = text.find(para, pos)
        if start < 0:
            start = pos
        end = start + len(para)
        if para.strip():
            spans.append((start, end))
        pos = end
    return spans or [(0, len(text))]


def chunk_document(doc: ParsedDoc, target_tokens: int = None,
                   overlap_tokens: int = None) -> List[Chunk]:
    s = get_settings()
    target_chars = (target_tokens or s.chunk_target_tokens) * CHARS_PER_TOKEN
    overlap_chars = (overlap_tokens or s.chunk_overlap_tokens) * CHARS_PER_TOKEN
    text = doc.text

    chunks: List[Chunk] = []
    spans = _segments(text)
    cur_start = spans[0][0]
    cur_end = cur_start
    idx = 0

    def emit(start: int, end: int) -> None:
        nonlocal idx
        body = text[start:end].strip()
        if not body:
            return
        chunks.append(Chunk(
            chunk_index=idx,
            text=body,
            token_count=max(1, len(body) // CHARS_PER_TOKEN),
            char_start=start,
            char_end=end,
            page_start=doc.page_for_offset(start),
            page_end=doc.page_for_offset(end),
        ))
        idx += 1

    for (_, seg_end) in spans:
        # Grow the current window until it reaches the target size.
        if seg_end - cur_start >= target_chars:
            emit(cur_start, seg_end)
            # Start the next chunk `overlap_chars` back for continuity.
            cur_start = max(cur_start, seg_end - overlap_chars)
        cur_end = seg_end

    if cur_end > cur_start:
        emit(cur_start, cur_end)

    return chunks
