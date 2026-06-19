"""Retrieval routing: top_k and document_id reach the (mocked) vector store,
citations are built from chunk metadata, and tokens stream through."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from app.models.schemas import AskRequest
from app.rag import vector_store
from app.services import conversation_service
from app.services.ask_service import AskService


class _Chunk:
    """Minimal stand-in for an AIMessageChunk (has a .content str)."""

    def __init__(self, content: str) -> None:
        self.content = content


async def _fake_astream(_messages):
    for token in ["Refunds ", "within 30 days ", "[policy.pdf, chunk 2]"]:
        yield _Chunk(token)


def _make_service(monkeypatch: pytest.MonkeyPatch, search_mock: AsyncMock) -> AskService:
    monkeypatch.setattr(vector_store, "search", search_mock)
    monkeypatch.setattr(conversation_service, "save_turn", AsyncMock())
    chat = AsyncMock()
    chat.astream = _fake_astream
    return AskService(chat_model=chat, top_k=4)


async def test_streams_answer_and_emits_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = Document(
        page_content="Refunds are issued within 30 days.",
        metadata={"filename": "policy.pdf", "chunk_index": 2, "chunk_id": "d:2"},
    )
    search_mock = AsyncMock(return_value=[(doc, 0.12)])
    service = _make_service(monkeypatch, search_mock)

    events = [c async for c in service.answer_stream(AskRequest(question="refund policy?"))]
    body = "".join(events)

    assert "policy.pdf" in body          # citation chip
    assert "within 30 days" in body      # streamed answer token
    # top_k and document_id are forwarded positionally: search(question, k, document_id)
    search_mock.assert_awaited_once()
    assert search_mock.await_args.args[1] == 4
    assert search_mock.await_args.args[2] is None


async def test_document_id_is_forwarded_to_search(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    search_mock = AsyncMock(return_value=[])
    service = _make_service(monkeypatch, search_mock)

    _ = [c async for c in service.answer_stream(
        AskRequest(question="q", document_id=document_id)
    )]

    assert search_mock.await_args.args[2] == document_id
