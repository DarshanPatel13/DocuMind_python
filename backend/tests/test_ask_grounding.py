"""Grounding guard: with no retrieved chunks, AskService returns the exact
sentinel and never calls the LLM."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import AskRequest
from app.rag import vector_store
from app.rag.prompt import NO_INFO_ANSWER
from app.services import ask_service, conversation_service
from app.services.ask_service import AskService


async def test_empty_retrieval_returns_sentinel_without_calling_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vector_store, "search", AsyncMock(return_value=[]))
    save_mock = AsyncMock()
    monkeypatch.setattr(conversation_service, "save_turn", save_mock)

    chat = MagicMock()
    chat.astream = MagicMock()  # must NOT be invoked
    service = AskService(chat_model=chat)

    events = [chunk async for chunk in service.answer_stream(AskRequest(question="anything?"))]
    body = "".join(events)

    assert NO_INFO_ANSWER in body
    chat.astream.assert_not_called()        # the whole point of the guard
    save_mock.assert_awaited_once()         # the miss is still recorded
