"""SQLAlchemy model + status enum for document metadata."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class DocumentStatus(str, enum.Enum):
    """Lifecycle of an uploaded document through the ingestion pipeline."""

    UPLOADED = "UPLOADED"      # stored + event published, not yet processed
    PROCESSING = "PROCESSING"  # consumer is extracting/chunking/embedding
    READY = "READY"            # chunks in pgvector; searchable
    FAILED = "FAILED"          # ingestion failed after retries; see failure_reason


class DocumentRow(Base):
    """One row per uploaded PDF. Status is stored as a plain string (not a DB
    enum type) to keep migrations trivial."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
