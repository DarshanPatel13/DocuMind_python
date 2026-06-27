"""Conversation history endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from documind_contracts import ConversationHistoryResponse

from app import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(conversation_id: str) -> ConversationHistoryResponse:
    return await conversation_service.get_history(conversation_id)
