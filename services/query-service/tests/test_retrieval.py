"""Retrieval routing: top_k and document_id reach the (mocked) hybrid retriever,
citations are built from chunk metadata, and tokens stream through."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from documind_common import retrieval
from documind_contracts import AskRequest

from app import conversation_service
from app.ask_service import AskService


class _Chunk:
    """Minimal stand-in for an AIMessageChunk (has a .content str)."""

    def __init__(self, content: str) -> None:
        self.content = content


async def _fake_astream(_messages, **_kwargs):
    # **_kwargs absorbs the Langfuse `config=` passed by the ask flow.
    for token in ["Refunds ", "within 30 days ", "[policy.pdf, chunk 2]"]:
        yield _Chunk(token)


def _result(pairs, *, relevant=True, best=0.12, keyword_hits=0):
    return retrieval.RetrievalResult(pairs, relevant, best, keyword_hits)


def _make_service(monkeypatch: pytest.MonkeyPatch, retrieve_mock: AsyncMock) -> AskService:
    monkeypatch.setattr(retrieval, "retrieve_scored", retrieve_mock)
    monkeypatch.setattr(conversation_service, "save_turn", AsyncMock())
    monkeypatch.setattr(conversation_service, "recent_turns", AsyncMock(return_value=[]))
    chat = AsyncMock()
    chat.astream = _fake_astream
    return AskService(chat_model=chat, top_k=4)


async def test_streams_answer_and_emits_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = Document(
        page_content="Refunds are issued within 30 days.",
        metadata={"filename": "policy.pdf", "chunk_index": 2, "chunk_id": "d:2"},
    )
    retrieve_mock = AsyncMock(return_value=_result([(doc, 0.12)]))
    service = _make_service(monkeypatch, retrieve_mock)

    events = [c async for c in service.answer_stream(AskRequest(question="refund policy?"))]
    body = "".join(events)

    assert "policy.pdf" in body          # citation chip
    assert "within 30 days" in body      # streamed answer token
    # top_k and document_id are forwarded positionally:
    # retrieve_scored(query, k, document_id)
    retrieve_mock.assert_awaited_once()
    assert retrieve_mock.await_args.args[1] == 4
    assert retrieve_mock.await_args.args[2] is None


async def test_document_id_is_forwarded_to_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    retrieve_mock = AsyncMock(return_value=_result([], relevant=False, best=None))
    service = _make_service(monkeypatch, retrieve_mock)

    _ = [c async for c in service.answer_stream(
        AskRequest(question="any coverage here", document_id=document_id)
    )]

    assert retrieve_mock.await_args.args[2] == document_id
