"""DocuMind shared contracts.

The single source of truth for everything that crosses a service boundary:
Kafka event payloads and the request/response DTOs every service agrees on.

Packaged as a standalone installable library that every service depends on (an
`*-api`/`*-contracts` distribution), so the payload shape can never silently
drift between producers and consumers.
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
