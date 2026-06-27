"""Kafka event payloads (JSON over the wire).

This is THE contract between document-service (producer) and its ingestion
consumer. If the two sides disagreed on this shape, ingestion would break at
runtime with no compiler to catch it — which is exactly why it lives in a
shared package instead of being duplicated in each service.
"""
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
