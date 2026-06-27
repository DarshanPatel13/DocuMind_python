"""Correlation-id propagation — a grep-able distributed trace across services.

A pure-ASGI middleware that:
  * reads `X-Request-ID` (set by the gateway) or generates one,
  * binds it to structlog's contextvars so EVERY log line in this request carries
    `request_id=…` automatically,
  * echoes it back on the response header.

Because the gateway forwards the same header to the upstream services, one user
request shows the SAME `request_id` in the gateway, document-service, and
query-service logs — so you can follow a single request across the whole system
with `docker compose logs | grep <request_id>`.

Why a pure-ASGI middleware (not BaseHTTPMiddleware): it runs in the *same* async
context as the endpoint, so contextvars bound here reliably propagate down to the
handlers and the LLM call. Java analogy: an MDC filter putting a `traceId` into
the logging context — exactly what Spring Sleuth / Micrometer Tracing do.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog

REQUEST_ID_HEADER = "X-Request-ID"
_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode()


def get_request_id() -> str | None:
    """The request id bound to the current context, if any (used by the proxy)."""
    return structlog.contextvars.get_contextvars().get("request_id")


class RequestIdMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw = headers.get(_HEADER_BYTES)
        request_id = raw.decode() if raw else uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].append((_HEADER_BYTES, request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
