"""Contextual retrieval: chunks get a locator line before embedding.

The behaviours worth pinning are the failure ones. Enrichment runs at ingestion,
so anything that throws here costs a document — it must degrade to the plain
chunk, never lose it."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from documind_common.config import settings

from app.contextual import enrich

CHUNKS = ["Unused days above this cap are forfeited on 31 March.", "Second chunk."]


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "contextual_retrieval_enabled", True)


def _model_replying(*replies: str) -> MagicMock:
    model = MagicMock()
    model.ainvoke = AsyncMock(side_effect=[MagicMock(content=r) for r in replies])
    return model


async def test_disabled_returns_chunks_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "contextual_retrieval_enabled", False)
    model = MagicMock()
    model.ainvoke = AsyncMock()

    assert await enrich(CHUNKS, chat_model=model) == CHUNKS
    model.ainvoke.assert_not_awaited()


async def test_prefixes_each_chunk_with_its_context() -> None:
    model = _model_replying("From the PTO carryover section.", "From the travel section.")

    out = await enrich(CHUNKS, chat_model=model)

    assert out[0].startswith("From the PTO carryover section.")
    assert CHUNKS[0] in out[0]           # the original text is preserved, not replaced
    assert out[1].startswith("From the travel section.")


async def test_a_failing_context_call_keeps_the_plain_chunk() -> None:
    model = MagicMock()
    model.ainvoke = AsyncMock(side_effect=RuntimeError("provider down"))

    assert await enrich(CHUNKS, chat_model=model) == CHUNKS


async def test_a_runaway_context_line_is_discarded() -> None:
    """A long reply means the model summarized instead of situating; that text
    would compete with the chunk's own content for the embedding."""
    model = _model_replying("x" * 400, "fine")

    out = await enrich(CHUNKS, chat_model=model)

    assert out[0] == CHUNKS[0]
    assert out[1].startswith("fine")


async def test_empty_input_is_a_no_op() -> None:
    model = MagicMock()
    model.ainvoke = AsyncMock()

    assert await enrich([], chat_model=model) == []
    model.ainvoke.assert_not_awaited()
