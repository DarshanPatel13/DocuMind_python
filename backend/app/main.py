"""FastAPI application: lifespan wiring, CORS, rate limiting, exception
handlers, and route registration.

Run locally with:  uvicorn app.main:app --reload
Interactive docs:   http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import routes_ask, routes_conversations, routes_documents
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.mongo import close_client, init_indexes
from app.db.postgres import init_db
from app.kafka import producer
from app.kafka.consumer import IngestionConsumer
from app.models.schemas import ErrorResponse
from app.services.errors import (
    ConversationNotFoundError,
    DocumentNotFoundError,
    InvalidFileError,
)

configure_logging()
log = get_logger(__name__)

_consumer = IngestionConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: metadata tables, Mongo indexes, Kafka producer, ingestion consumer.
    await init_db()
    await init_indexes()
    await producer.start_producer()
    await _consumer.start()
    log.info("startup complete", stage="startup")
    yield
    # Shutdown: reverse order.
    await _consumer.stop()
    await producer.stop_producer()
    await close_client()
    log.info("shutdown complete", stage="shutdown")


app = FastAPI(title="DocuMind API", version="1.0.0", lifespan=lifespan)

# Rate limiting (slowapi) — applied to /api/ask via the decorator on the route.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.exception_handler(ConversationNotFoundError)
async def _conversation_not_found(_: Request, exc: ConversationNotFoundError) -> JSONResponse:
    return _error(404, "Not Found", f"Conversation not found: {exc}")


app.include_router(routes_documents.router)
app.include_router(routes_ask.router)
app.include_router(routes_conversations.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
