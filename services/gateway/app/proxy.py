"""Streaming reverse proxy to the internal services.

The critical detail: `/api/ask` returns Server-Sent Events. A naive proxy that
does `resp = await client.post(...)` would buffer the WHOLE response before
returning — killing token-by-token streaming. So we open the upstream response
in streaming mode and forward chunks as they arrive via `aiter_raw()`, wrapped in
a FastAPI `StreamingResponse`.
"""
from __future__ import annotations

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse

from documind_common.correlation import REQUEST_ID_HEADER, get_request_id

# Hop-by-hop headers must not be forwarded (RFC 7230 §6.1) + ones httpx recomputes.
_HOP_BY_HOP = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "upgrade",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
}

_client: httpx.AsyncClient | None = None


async def start_client() -> None:
    global _client
    if _client is None:
        # read=None: never time out an in-flight SSE stream.
        _client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))


async def stop_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def proxy(request: Request, upstream_base: str) -> StreamingResponse:
    assert _client is not None, "proxy client not started"

    url = upstream_base + request.url.path
    if request.url.query:
        url += f"?{request.url.query}"

    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}

    # Forward the correlation id so upstream logs share this request's trace.
    request_id = get_request_id()
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id

    upstream_req = _client.build_request(
        request.method, url, headers=headers, content=body
    )
    upstream_resp = await _client.send(upstream_req, stream=True)

    resp_headers = {
        k: v for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_BY_HOP
    }

    async def body_stream():
        try:
            async for chunk in upstream_resp.aiter_raw():
                yield chunk
        finally:
            await upstream_resp.aclose()

    return StreamingResponse(
        body_stream(),
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
