"""Document lifecycle status — shared because BOTH services reason about it:
document-service writes it, and it surfaces in the DocumentResponse the
query/UI side reads."""
from __future__ import annotations

import enum


class DocumentStatus(str, enum.Enum):
    """Lifecycle of an uploaded document through the ingestion pipeline."""

    UPLOADED = "UPLOADED"      # stored + event published, not yet processed
    PROCESSING = "PROCESSING"  # consumer is extracting/chunking/embedding
    READY = "READY"            # chunks in pgvector; searchable
    FAILED = "FAILED"          # ingestion failed after retries; see failure_reason
