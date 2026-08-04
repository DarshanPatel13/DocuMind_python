"""Conversation history persistence and retrieval (MongoDB)."""
from __future__ import annotations

from datetime import datetime

from documind_contracts import (
    Citation,
    ConversationHistoryResponse,
    ConversationTurnResponse,
)

from documind_common.logging import get_logger

from app.errors import ConversationNotFoundError
from app.mongo import conversations

log = get_logger(__name__)


async def save_turn(
    *,
    conversation_id: str,
    question: str,
    answer: str,
    citations: list[Citation],
    retrieved_chunk_ids: list[str],
    timestamp: datetime,
) -> None:
    await conversations().insert_one(
        {
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "citations": [c.model_dump() for c in citations],
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "timestamp": timestamp,
        }
    )


async def recent_turns(conversation_id: str, limit: int) -> list[tuple[str, str]]:
    """The last `limit` (question, answer) pairs, oldest-first.

    Feeds two things: the prompt, so the model can resolve "it" and "that", and
    the query rewriter, so retrieval can too. Fetched newest-first then reversed,
    because Mongo can only limit from one end and we want the most RECENT turns
    presented in reading order.

    Returns empty rather than raising for an unknown conversation — a first turn
    is the normal case, not an error. Fails open for the same reason: memory is
    an enhancement, not a requirement, so a lookup that errors degrades the turn
    to single-shot rather than failing the answer."""
    if limit <= 0:
        return []
    try:
        docs = (
            await conversations()
            .find({"conversation_id": conversation_id})
            .sort("timestamp", -1)
            .to_list(length=limit)
        )
    except Exception as exc:  # noqa: BLE001 — never fail an answer over memory
        log.warning("history lookup failed", stage="memory-failed", error=str(exc))
        return []
    return [(d["question"], d["answer"]) for d in reversed(docs)]


async def get_history(conversation_id: str) -> ConversationHistoryResponse:
    docs = (
        await conversations()
        .find({"conversation_id": conversation_id})
        .sort("timestamp", 1)
        .to_list(length=1000)
    )
    if not docs:
        raise ConversationNotFoundError(conversation_id)
    turns = [
        ConversationTurnResponse(
            question=d["question"],
            answer=d["answer"],
            citations=[Citation(**c) for c in d.get("citations", [])],
            timestamp=d["timestamp"],
        )
        for d in docs
    ]
    return ConversationHistoryResponse(conversation_id=conversation_id, turns=turns)
