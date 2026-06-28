"""Whole-document mode: an aggregate query reads ALL of the document's chunks
(via fetch_document_chunks) instead of top-k retrieval."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from documind_common import retrieval
from documind_contracts import AskRequest

from app import conversation_service
from app.ask_service import AskService


class _Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


async def _fake_astream(_messages, **_kwargs):
    yield _Chunk("1. Design LeetCode  2. Design Typeahead")


async def test_aggregate_query_reads_whole_document(monkeypatch: pytest.MonkeyPatch) -> None:
    all_chunks = [
        Document(
            page_content=f"Question {i}",
            metadata={"filename": "System Design.pdf", "chunk_index": i, "chunk_id": f"d:{i}", "document_id": "d1"},
        )
        for i in range(12)
    ]
    fetch_mock = AsyncMock(return_value=all_chunks)
    monkeypatch.setattr(retrieval, "fetch_document_chunks", fetch_mock)
    # No scope chosen -> the flow first finds the most relevant document.
    monkeypatch.setattr(retrieval, "retrieve", AsyncMock(return_value=[(all_chunks[0], 0.1)]))
    monkeypatch.setattr(conversation_service, "save_turn", AsyncMock())

    chat = AsyncMock()
    chat.astream = _fake_astream
    service = AskService(chat_model=chat)

    events = [
        c
        async for c in service.answer_stream(
            AskRequest(question="Can you list all the system design questions mentioned")
        )
    ]
    body = "".join(events)

    fetch_mock.assert_awaited_once()                 # whole-document path was used
    assert fetch_mock.await_args.args[0] == "d1"     # for the most-relevant document
    assert "Design LeetCode" in body                 # the model's answer streamed through
