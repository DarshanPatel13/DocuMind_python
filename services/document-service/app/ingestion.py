"""The ingestion pipeline: PROCESSING -> extract -> chunk -> embed/store -> READY.

Called from the Kafka consumer. Idempotent: a READY document is skipped, and
chunks upsert by deterministic id, so an at-least-once redelivery is harmless.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from documind_common import vector_store
from documind_common.logging import get_logger
from documind_contracts import DocumentStatus, DocumentUploadedEvent

from app.chunking import split_text
from app.errors import DocumentNotFoundError, IngestionError
from app.models import DocumentRow
from app.pdf_extract import extract_pdf_text

log = get_logger(__name__)


async def ingest(session: AsyncSession, event: DocumentUploadedEvent) -> None:
    row = await session.get(DocumentRow, event.document_id)
    if row is None:
        raise DocumentNotFoundError(f"Document not found: {event.document_id}")

    # Idempotency guard: skip work already done (Kafka is at-least-once).
    if row.status == DocumentStatus.READY.value:
        log.info("skip already-ready", stage="skip", document_id=str(event.document_id))
        return

    row.status = DocumentStatus.PROCESSING.value
    await session.commit()
    log.info("processing", stage="processing", document_id=str(event.document_id))

    text = await asyncio.to_thread(extract_pdf_text, event.storage_path)
    if not text.strip():
        raise IngestionError(
            f"No extractable text in {event.document_id} (scanned/image-only PDF?)"
        )

    chunks = split_text(text)
    log.info(
        "chunked", stage="chunked", document_id=str(event.document_id), chunks=len(chunks)
    )

    count = await vector_store.add_chunks(event.document_id, event.filename, chunks)

    row.status = DocumentStatus.READY.value
    row.chunk_count = count
    row.failure_reason = None
    await session.commit()
    log.info("ready", stage="ready", document_id=str(event.document_id), chunk_count=count)
