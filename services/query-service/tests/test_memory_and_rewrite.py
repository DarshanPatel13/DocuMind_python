"""Multi-turn memory and query rewriting.

The pairing matters: memory in the prompt lets the model resolve "it", but only
the rewrite lets RETRIEVAL resolve it. A follow-up like "and for digital goods?"
embeds as a question about digital goods and nothing else, so without the
rewrite the right chunks never come back — and no amount of prompt history can
fix a retrieval that already ran.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from documind_common import retrieval
from documind_common.config import settings
from documind_contracts import AskRequest

from app import conversation_service
from app.ask_service import AskService
from app.prompt import build_messages
from app.query_rewriter import QueryRewriter

HISTORY = [("What is the refund policy?", "Refunds within 30 days.")]


class _Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


async def _fake_astream(_messages, **_kwargs):
    yield _Chunk("ok")


def _rewriter_replying(reply: str) -> QueryRewriter:
    chat = MagicMock()
    chat.ainvoke = AsyncMock(return_value=MagicMock(content=reply))
    return QueryRewriter(chat_model=chat)


# --------------------------------------------------------------------------
# Query rewriting
# --------------------------------------------------------------------------

async def test_first_turn_is_not_rewritten() -> None:
    """No history means nothing to resolve — and no reason to pay for a call."""
    chat = MagicMock()
    chat.ainvoke = AsyncMock()
    rewriter = QueryRewriter(chat_model=chat)

    assert await rewriter.rewrite("What is the refund policy?", []) == "What is the refund policy?"
    chat.ainvoke.assert_not_awaited()


async def test_follow_up_is_condensed_into_a_standalone_query() -> None:
    rewriter = _rewriter_replying("refund policy for digital goods")

    result = await rewriter.rewrite("and for digital goods?", HISTORY)

    assert result == "refund policy for digital goods"


async def test_rewrite_failure_falls_back_to_the_original_question() -> None:
    chat = MagicMock()
    chat.ainvoke = AsyncMock(side_effect=RuntimeError("provider down"))
    rewriter = QueryRewriter(chat_model=chat)

    assert await rewriter.rewrite("and for digital goods?", HISTORY) == "and for digital goods?"


async def test_a_runaway_rewrite_is_discarded() -> None:
    """A rewrite that balloons means the model started answering instead of
    rewriting; embedding a paragraph would be worse than the original."""
    rewriter = _rewriter_replying("x" * 500)

    assert await rewriter.rewrite("and for digital goods?", HISTORY) == "and for digital goods?"


async def test_empty_rewrite_is_discarded() -> None:
    assert await _rewriter_replying("   ").rewrite("follow up?", HISTORY) == "follow up?"


# --------------------------------------------------------------------------
# Prompt memory
# --------------------------------------------------------------------------

def test_history_is_replayed_as_alternating_turns() -> None:
    docs = [Document(page_content="ctx", metadata={"filename": "f.pdf", "chunk_index": 0})]

    messages = build_messages("and for digital goods?", docs, history=HISTORY)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "What is the refund policy?"
    assert isinstance(messages[2], AIMessage)
    assert messages[2].content == "Refunds within 30 days."
    # The live question comes last and still carries the retrieved context.
    assert isinstance(messages[-1], HumanMessage)
    assert "ctx" in messages[-1].content
    assert "and for digital goods?" in messages[-1].content


def test_no_history_keeps_the_original_two_message_shape() -> None:
    docs = [Document(page_content="ctx", metadata={"filename": "f.pdf", "chunk_index": 0})]

    assert len(build_messages("q", docs)) == 2


# --------------------------------------------------------------------------
# Wiring: the rewritten query drives retrieval, the original drives the answer
# --------------------------------------------------------------------------

async def test_retrieval_uses_the_rewritten_query_but_the_prompt_keeps_the_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rewrite_enabled", True)
    doc = Document(page_content="Digital goods: 14 days.", metadata={"filename": "p.pdf", "chunk_index": 1})
    retrieve_mock = AsyncMock(
        return_value=retrieval.RetrievalResult([(doc, 0.2)], True, 0.2, 0)
    )
    monkeypatch.setattr(retrieval, "retrieve_scored", retrieve_mock)
    monkeypatch.setattr(conversation_service, "save_turn", AsyncMock())
    monkeypatch.setattr(conversation_service, "recent_turns", AsyncMock(return_value=HISTORY))

    captured = {}

    async def capture_astream(messages, **_kwargs):
        captured["messages"] = messages
        yield _Chunk("ok")

    chat = MagicMock()
    chat.astream = capture_astream
    service = AskService(
        chat_model=chat, rewriter=_rewriter_replying("refund policy for digital goods")
    )

    _ = [c async for c in service.answer_stream(AskRequest(question="and for digital goods?"))]

    # Retrieval saw the standalone query...
    assert retrieve_mock.await_args.args[0] == "refund policy for digital goods"
    # ...while the answer model was asked the user's actual words.
    assert "and for digital goods?" in captured["messages"][-1].content
    # ...and the prior turn is present so "it" still resolves.
    assert any(isinstance(m, AIMessage) for m in captured["messages"])


async def test_rewriting_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Toggle exists so the eval suite can A/B the rewrite's contribution."""
    monkeypatch.setattr(settings, "rewrite_enabled", False)
    retrieve_mock = AsyncMock(return_value=retrieval.RetrievalResult([], False, None, 0))
    monkeypatch.setattr(retrieval, "retrieve_scored", retrieve_mock)
    monkeypatch.setattr(conversation_service, "save_turn", AsyncMock())
    monkeypatch.setattr(conversation_service, "recent_turns", AsyncMock(return_value=HISTORY))

    chat = MagicMock()
    chat.astream = _fake_astream
    rewriter = _rewriter_replying("should not be used")
    service = AskService(chat_model=chat, rewriter=rewriter)

    _ = [c async for c in service.answer_stream(AskRequest(question="and for digital goods?"))]

    assert retrieve_mock.await_args.args[0] == "and for digital goods?"
