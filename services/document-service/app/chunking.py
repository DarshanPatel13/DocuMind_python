"""Text chunking via LangChain's RecursiveCharacterTextSplitter.

WHY ~800 tokens with 100 overlap:
  * One embedding summarizes a whole chunk, so chunk size sets retrieval
    resolution. Too big -> the vector averages many topics and search blurs;
    too small -> retrieved snippets lose the context the LLM needs.
  * The 100-token overlap means a sentence cut at a boundary still appears
    whole in the neighbouring chunk.

TOKEN ESTIMATION: English averages ~4 characters per token, and chunking only
needs to be roughly right. RecursiveCharacterTextSplitter measures length in
characters, so we pre-multiply token counts by chars_per_token.

The chunking knobs live in the shared `documind_common` config because chunk
size is part of what shapes the vectors both services rely on.
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from documind_common.config import settings


def split_text(
    text: str,
    *,
    chunk_size_tokens: int | None = None,
    overlap_tokens: int | None = None,
    chars_per_token: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks. Returns [] for empty/blank input."""
    if not text or not text.strip():
        return []

    cpt = chars_per_token or settings.chars_per_token
    chunk_chars = (chunk_size_tokens or settings.chunk_size_tokens) * cpt
    overlap_chars = (overlap_tokens or settings.overlap_tokens) * cpt

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]
