"""Chunking maths with production settings: 800 tokens * 4 chars = 3200-char
chunks, 100 tokens * 4 = 400-char overlap, so windows step by 2800 chars.

We feed a separator-free string so RecursiveCharacterTextSplitter falls back to
character splitting and the windows are exactly predictable.
"""
from __future__ import annotations

from app.chunking import split_text

CHUNK_CHARS = 3200
OVERLAP_CHARS = 400


def _text(length: int) -> str:
    # Deterministic letters only (no spaces/newlines) -> pure character windows.
    return "".join(chr(ord("a") + (i % 26)) for i in range(length))


def test_empty_or_blank_text_yields_no_chunks() -> None:
    assert split_text("") == []
    assert split_text("   ") == []


def test_short_text_is_a_single_chunk() -> None:
    chunks = split_text("hello world")
    assert chunks == ["hello world"]


def test_chunks_never_exceed_configured_size() -> None:
    chunks = split_text(_text(10_000))
    assert len(chunks) == 4  # windows at 0, 2800, 5600, 8400
    assert all(len(c) <= CHUNK_CHARS for c in chunks)
    assert len(chunks[0]) == CHUNK_CHARS


def test_consecutive_chunks_share_the_overlap_region() -> None:
    chunks = split_text(_text(10_000))
    for i in range(len(chunks) - 1):
        assert chunks[i][-OVERLAP_CHARS:] == chunks[i + 1][:OVERLAP_CHARS]


def test_custom_chunk_settings_are_respected() -> None:
    # 10 tokens * 2 chars = 20-char chunks, 2 tokens * 2 = 4-char overlap.
    chunks = split_text(_text(100), chunk_size_tokens=10, overlap_tokens=2, chars_per_token=2)
    assert all(len(c) <= 20 for c in chunks)
    assert len(chunks) > 1
