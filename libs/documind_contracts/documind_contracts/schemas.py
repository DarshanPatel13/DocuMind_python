"""Pydantic request/response models — the typed HTTP API contract.

These mirror the shared TypeScript types in the frontend (src/types/index.ts).
Shared across services so the gateway, document-service, and query-service all
serialize/deserialize identical shapes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_id: uuid.UUID | None = None
    conversation_id: str | None = None


class Citation(BaseModel):
    """Pointer to the chunk a statement was grounded on; rendered as
    [filename, chunk N]."""

    filename: str
    chunk_index: int


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    message: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # build directly from the ORM row

    id: uuid.UUID
    filename: str
    status: str
    uploaded_at: datetime
    chunk_count: int
    failure_reason: str | None = None


class ConversationTurnResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    timestamp: datetime


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    turns: list[ConversationTurnResponse]


class ErrorResponse(BaseModel):
    error: str
    message: str


# ---- Auth (gateway) ----
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
