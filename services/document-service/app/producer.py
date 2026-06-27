"""Async Kafka producer (aiokafka). Started/stopped in the FastAPI lifespan."""
from __future__ import annotations

import json
from typing import Any

from aiokafka import AIOKafkaProducer

from app.config import settings

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            key_serializer=lambda k: k.encode("utf-8"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )
        await _producer.start()


async def stop_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None


async def publish(topic: str, key: str, value: dict[str, Any]) -> None:
    if _producer is None:
        raise RuntimeError("Kafka producer not started")
    # Keyed by document_id so all events for one document keep partition order.
    await _producer.send_and_wait(topic, key=key, value=value)
