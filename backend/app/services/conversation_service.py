"""Conversation history persistence and retrieval (MongoDB)."""
from __future__ import annotations

from datetime import datetime

from app.db.mongo import conversations
from app.models.schemas import Citation, ConversationHistoryResponse, ConversationTurnResponse
from app.services.errors import ConversationNotFoundError


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
