"""Kafka event payloads (JSON over the wire)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadedEvent(BaseModel):
    """Published to `document-events` after a successful upload and consumed by
    the ingestion pipeline. Carries the storage path so the consumer never has
    to call back into the web layer."""

    document_id: uuid.UUID
    filename: str
    storage_path: str
    uploaded_at: datetime
