"""gateway FastAPI app — the single public entry point.

Responsibilities (all the cross-cutting concerns, kept out of the business
services): JWT auth, CORS, Redis rate limiting, and routing/streaming to the
internal document-service and query-service.

Run locally:  uvicorn app.main:app --reload --port 8080
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text

from documind_contracts import LoginRequest, TokenResponse

from app import proxy
from app.auth import get_current_user, login
from app.config import settings
from app.db import engine, init_db
from app.rate_limit import close_redis, enforce_rate_limit, get_redis

from documind_common.correlation import RequestIdMiddleware  # isort: skip
from documind_common.logging import configure_logging, get_logger  # isort: skip

configure_logging()
structlog.contextvars.bind_contextvars(service="gateway")
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()                 # users table + demo user
    await proxy.start_client()      # shared httpx client
    log.info("startup complete", stage="startup")
    yield
    await proxy.stop_client()
    await close_redis()
    log.info("shutdown complete", stage="shutdown")


app = FastAPI(title="DocuMind gateway", version="1.0.0", lifespan=lifespan)

# Added last = outermost: a correlation id is assigned before anything else runs.
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Public routes (no token required) ----
@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login_route(body: LoginRequest) -> TokenResponse:
    return await login(body)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> JSONResponse:
    """Readiness: users DB + Redis reachable (the gateway's own dependencies)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await get_redis().ping()
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "not-ready", "reason": str(exc)}, status_code=503)


# ---- Authenticated reverse proxy ----
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_proxy(
    path: str, request: Request, user: str = Depends(get_current_user)
) -> StreamingResponse:
    full_path = f"/api/{path}"

    if full_path.startswith("/api/documents"):
        upstream = settings.document_service_url
    elif full_path.startswith("/api/ask"):
        await enforce_rate_limit(user)   # the expensive LLM call is rate-limited
        upstream = settings.query_service_url
    elif full_path.startswith("/api/conversations"):
        upstream = settings.query_service_url
    else:
        raise HTTPException(status_code=404, detail="Unknown route")

    return await proxy.proxy(request, upstream)
