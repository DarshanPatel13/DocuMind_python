"""Async ingestion consumer (aiokafka).

Runs as a background asyncio task started in the FastAPI lifespan. Policy:
3 retries with exponential backoff (1s, 2s, 4s); on final failure mark the
document FAILED and publish the original event to the DLT. Offsets are
committed manually only after a message is fully handled (success OR routed to
the DLT), so nothing is silently dropped.
"""
from __future__ import annotations

import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.logging import get_logger
from app.db.postgres import SessionLocal
from app.kafka import producer
from app.models.document import DocumentRow, DocumentStatus
from app.models.events import DocumentUploadedEvent
from app.services import ingestion_service
from app.services.errors import DocumentNotFoundError

log = get_logger(__name__)

MAX_RETRIES = 3


class IngestionConsumer:
    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            settings.document_events_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._run())
        log.info("kafka consumer started", stage="consume-start")

    async def _run(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                await self._handle(msg.value)
                await self._consumer.commit()
        except asyncio.CancelledError:
            pass  # normal shutdown

    async def _handle(self, raw: dict) -> None:
        event = DocumentUploadedEvent.model_validate(raw)
        delay = 1.0
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with SessionLocal() as session:
                    await ingestion_service.ingest(session, event)
                return
            except DocumentNotFoundError as exc:
                # Retrying will never make a missing row appear.
                await self._dead_letter(event, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 — retry any other failure
                log.warning(
                    "ingestion attempt failed",
                    stage="retry",
                    document_id=str(event.document_id),
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt == MAX_RETRIES:
                    await self._dead_letter(event, str(exc))
                    return
                await asyncio.sleep(delay)
                delay *= 2

    async def _dead_letter(self, event: DocumentUploadedEvent, reason: str) -> None:
        async with SessionLocal() as session:
            row = await session.get(DocumentRow, event.document_id)
            if row is not None:
                row.status = DocumentStatus.FAILED.value
                row.failure_reason = reason
                await session.commit()
        await producer.publish(
            settings.document_events_dlt_topic,
            key=str(event.document_id),
            value=event.model_dump(mode="json"),
        )
        log.error(
            "document sent to DLT",
            stage="dlt",
            document_id=str(event.document_id),
            reason=reason,
        )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._consumer is not None:
            await self._consumer.stop()
        log.info("kafka consumer stopped", stage="consume-stop")
