"""Grounding guard: without RELEVANT retrieved chunks, AskService returns the
exact sentinel and never calls the LLM."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from documind_common import retrieval
from documind_contracts import AskRequest

from app import conversation_service
from app.ask_service import AskService
from app.prompt import NO_INFO_ANSWER


def _doc(text: str) -> Document:
    return Document(page_content=text, metadata={"filename": "policy.pdf", "chunk_index": 1})


def _service(monkeypatch: pytest.MonkeyPatch, result: retrieval.RetrievalResult):
    monkeypatch.setattr(retrieval, "retrieve_scored", AsyncMock(return_value=result))
    save_mock = AsyncMock()
    monkeypatch.setattr(conversation_service, "save_turn", save_mock)
    monkeypatch.setattr(conversation_service, "recent_turns", AsyncMock(return_value=[]))

    chat = MagicMock()
    chat.astream = MagicMock()  # must NOT be invoked
    return AskService(chat_model=chat), chat, save_mock


async def test_empty_retrieval_returns_sentinel_without_calling_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = retrieval.RetrievalResult([], False, None, 0)
    service, chat, save_mock = _service(monkeypatch, result)

    events = [chunk async for chunk in service.answer_stream(AskRequest(question="anything?"))]
    body = "".join(events)

    assert NO_INFO_ANSWER in body
    chat.astream.assert_not_called()        # the whole point of the guard
    save_mock.assert_awaited_once()         # the miss is still recorded


async def test_irrelevant_chunks_are_refused_without_calling_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bug this gate exists for.

    Retrieval returns a full top-k for a question the corpus has never heard of —
    `LIMIT k` always yields k rows. Only the distance reveals it, and the old
    `if not docs` guard could never see the difference."""
    result = retrieval.RetrievalResult(
        [(_doc("Flood is excluded under form CP-10."), 0.81)],
        relevant=False,
        best_vector_distance=0.81,
        keyword_hits=0,
    )
    service, chat, save_mock = _service(monkeypatch, result)

    events = [
        chunk
        async for chunk in service.answer_stream(
            AskRequest(question="What is our cyber liability limit?")
        )
    ]
    body = "".join(events)

    assert NO_INFO_ANSWER in body
    chat.astream.assert_not_called()
    save_mock.assert_awaited_once()
