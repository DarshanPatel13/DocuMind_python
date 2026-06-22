"""The /api/ask endpoint: streams a grounded answer as SSE. Rate-limited per IP."""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.schemas import AskRequest
from app.services.ask_service import AskService

router = APIRouter(prefix="/api/ask", tags=["ask"])

_service = AskService()


@router.post("")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def ask(request: Request, body: AskRequest) -> StreamingResponse:
    # `request` is required by slowapi to read the client IP. The text/event-stream
    # media type tells the browser to treat the body as Server-Sent Events.
    return StreamingResponse(
        _service.answer_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
