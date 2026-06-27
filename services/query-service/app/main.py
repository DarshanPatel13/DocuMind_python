"""query-service FastAPI app: the RAG ask flow + conversation history.

Run locally:  uvicorn app.main:app --reload --port 8002
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from documind_common.logging import configure_logging, get_logger
from documind_contracts import ErrorResponse

from app.errors import ConversationNotFoundError
from app.mongo import close_client, get_client, init_indexes
from app.routes_ask import router as ask_router
from app.routes_conversations import router as conversations_router

configure_logging()
structlog.contextvars.bind_contextvars(service="query-service")
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_indexes()
    log.info("startup complete", stage="startup")
    yield
    await close_client()
    log.info("shutdown complete", stage="shutdown")


app = FastAPI(title="DocuMind query-service", version="1.0.0", lifespan=lifespan)


def _error(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, message=message).model_dump(),
    )


@app.exception_handler(ConversationNotFoundError)
async def _conversation_not_found(_: Request, exc: ConversationNotFoundError) -> JSONResponse:
    return _error(404, "Not Found", f"Conversation not found: {exc}")


app.include_router(ask_router)
app.include_router(conversations_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> JSONResponse:
    """Readiness: verify MongoDB (conversation history) is reachable."""
    try:
        await get_client().admin.command("ping")
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "not-ready", "reason": str(exc)}, status_code=503)
