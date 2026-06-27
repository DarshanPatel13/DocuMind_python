"""The /api/ask endpoint: streams a grounded answer as SSE.

Rate limiting now lives at the gateway (Redis-backed), so this route stays a
thin streaming endpoint.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from documind_contracts import AskRequest

from app.ask_service import AskService

router = APIRouter(prefix="/api/ask", tags=["ask"])

_service = AskService()


@router.post("")
async def ask(body: AskRequest) -> StreamingResponse:
    # text/event-stream tells the browser (and the gateway proxy) to treat the
    # body as Server-Sent Events and not buffer it.
    return StreamingResponse(
        _service.answer_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
