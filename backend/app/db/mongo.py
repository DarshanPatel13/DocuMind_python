"""MongoDB (Motor async driver) for conversation history.

Conversation history is an append-only, schema-flexible log always read back
whole by conversation_id — a document store's sweet spot.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def conversations() -> AsyncIOMotorCollection:
    return get_client()[settings.mongo_db]["conversation_turns"]


async def init_indexes() -> None:
    """History lookups are always by conversation_id, so index it."""
    await conversations().create_index("conversation_id")


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
