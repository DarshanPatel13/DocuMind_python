"""document-service FastAPI app: uploads, metadata, and the ingestion consumer.

Run locally:  uvicorn app.main:app --reload --port 8001
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from documind_common.logging import configure_logging, get_logger
from documind_contracts import ErrorResponse

from app import producer
from app.consumer import IngestionConsumer
from app.db import engine, init_db
from app.errors import DocumentNotFoundError, InvalidFileError
from app.routes import router

configure_logging()
structlog.contextvars.bind_contextvars(service="document-service")
log = get_logger(__name__)

_consumer = IngestionConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    await producer.start_producer()
    await _consumer.start()
    log.info("startup complete", stage="startup")
    yield
    await _consumer.stop()
    await producer.stop_producer()
    log.info("shutdown complete", stage="shutdown")


app = FastAPI(title="DocuMind document-service", version="1.0.0", lifespan=lifespan)


def _error(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, message=message).model_dump(),
    )


@app.exception_handler(InvalidFileError)
async def _invalid_file(_: Request, exc: InvalidFileError) -> JSONResponse:
    return _error(400, "Bad Request", str(exc))


@app.exception_handler(DocumentNotFoundError)
async def _document_not_found(_: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return _error(404, "Not Found", str(exc))


app.include_router(router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness: the process is up. Cheap, never touches dependencies."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> JSONResponse:
    """Readiness: can we actually serve? Verifies the metadata DB is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "not-ready", "reason": str(exc)}, status_code=503)
