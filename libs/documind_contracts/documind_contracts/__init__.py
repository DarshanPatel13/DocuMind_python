"""DocuMind shared contracts.

The single source of truth for everything that crosses a service boundary:
Kafka event payloads and the request/response DTOs every service agrees on.

Java analogy: this is the equivalent of a shared `*-api` / `*-contracts` Maven
module that your producer and consumer services both depend on, so the message
shape can never silently drift between them.
"""
from documind_contracts.events import DocumentUploadedEvent
from documind_contracts.schemas import (
    AskRequest,
    Citation,
    ConversationHistoryResponse,
    ConversationTurnResponse,
    DocumentResponse,
    ErrorResponse,
    LoginRequest,
    TokenResponse,
    UploadResponse,
)
from documind_contracts.status import DocumentStatus

__all__ = [
    "DocumentUploadedEvent",
    "AskRequest",
    "Citation",
    "ConversationHistoryResponse",
    "ConversationTurnResponse",
    "DocumentResponse",
    "ErrorResponse",
    "LoginRequest",
    "TokenResponse",
    "UploadResponse",
    "DocumentStatus",
]
