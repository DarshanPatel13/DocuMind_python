"""Upload handling: validate -> store file -> record metadata -> publish event.

Everything slow (extraction, embeddings) happens later on the consumer side,
so the upload request returns in milliseconds with 202.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from documind_common.logging import get_logger
from documind_contracts import (
    DocumentResponse,
    DocumentStatus,
    DocumentUploadedEvent,
    UploadResponse,
)

from app import producer
from app.config import settings
from app.errors import InvalidFileError
from app.models import DocumentRow

log = get_logger(__name__)

_PDF_MAGIC = b"%PDF"


def validate_pdf(filename: str | None, content_type: str | None, content: bytes) -> None:
    """Reject anything that is not a real PDF under the size limit.

    Extension and Content-Type are client-supplied and trivially spoofed, so
    the %PDF magic-byte check is the one that actually matters."""
    if not content:
        raise InvalidFileError("A non-empty 'file' is required")
    if len(content) > settings.max_upload_bytes:
        raise InvalidFileError("File exceeds the 20 MB limit")
    name_ok = bool(filename) and filename.lower().endswith(".pdf")
    type_ok = content_type == "application/pdf"
    if not name_ok and not type_ok:
        raise InvalidFileError("Only PDF files are accepted")
    if content[:4] != _PDF_MAGIC:
        raise InvalidFileError("File content is not a valid PDF")


async def upload(
    session: AsyncSession, filename: str | None, content_type: str | None, content: bytes
) -> UploadResponse:
    validate_pdf(filename, content_type, content)

    document_id = uuid.uuid4()
    safe_name = Path(filename or "document.pdf").name  # strip any client path
    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    target = storage_dir / f"{document_id}.pdf"
    # File first, then the DB row, then the event — the event must never
    # reference something that does not exist yet.
    await asyncio.to_thread(target.write_bytes, content)

    uploaded_at = datetime.now(timezone.utc)
    session.add(
        DocumentRow(
            id=document_id,
            filename=safe_name,
            status=DocumentStatus.UPLOADED.value,
            uploaded_at=uploaded_at,
            chunk_count=0,
        )
    )
    await session.commit()

    event = DocumentUploadedEvent(
        document_id=document_id,
        filename=safe_name,
        storage_path=str(target.resolve()),
        uploaded_at=uploaded_at,
    )
    await producer.publish(
        settings.document_events_topic, key=str(document_id), value=event.model_dump(mode="json")
    )
    log.info("document uploaded", stage="upload", document_id=str(document_id), filename=safe_name)

    return UploadResponse(
        document_id=document_id,
        status=DocumentStatus.UPLOADED.value,
        message="Document accepted for processing",
    )


async def list_documents(session: AsyncSession) -> list[DocumentResponse]:
    rows = (
        await session.execute(select(DocumentRow).order_by(DocumentRow.uploaded_at.desc()))
    ).scalars().all()
    return [DocumentResponse.model_validate(row) for row in rows]
