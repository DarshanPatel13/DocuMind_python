"""Text chunking via LangChain's RecursiveCharacterTextSplitter.

WHY ~800 tokens with 100 overlap:
  * One embedding summarizes a whole chunk, so chunk size sets retrieval
    resolution. Too big -> the vector averages many topics and search blurs;
    too small -> retrieved snippets lose the context the LLM needs.
  * The 100-token overlap means a sentence cut at a boundary still appears
    whole in the neighbouring chunk.

TOKEN ESTIMATION: models tokenize with their own tokenizer, but chunking only
needs to be roughly right, and English averages ~4 characters per token. So an
800-token chunk ≈ 3200 characters and the 100-token overlap ≈ 400 characters.
RecursiveCharacterTextSplitter measures length in characters (length_function=len),
so we pre-multiply the token counts by chars_per_token.

RecursiveCharacterTextSplitter tries to split on paragraph -> line -> word
boundaries before falling back to raw characters, so chunks break at natural
seams when possible — nicer than fixed windows.
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


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
