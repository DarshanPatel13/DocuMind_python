"""The RAG ask flow, streamed to the client as Server-Sent Events.

Stream protocol (one JSON object per `data:` line):
  {"type": "citations", "conversation_id": "...", "citations": [...]}  # first
  {"type": "token", "token": "..."}                                    # many
  {"type": "done"}                                                     # last

The full answer is assembled server-side and persisted to MongoDB after the
stream completes.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from documind_common import retrieval
from documind_common.config import settings
from documind_common.logging import get_logger
from documind_common.providers import get_chat_model
from documind_contracts import AskRequest, Citation

from app import conversation_service
from app.guardrails import INJECTION_REFUSAL, detect_prompt_injection
from app.observability import get_langfuse_handler
from app.prompt import NO_INFO_ANSWER, build_messages

log = get_logger(__name__)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


class AskService:
    def __init__(self, chat_model=None, top_k: int | None = None) -> None:
        self._chat_model = chat_model            # injectable for tests
        self.top_k = top_k or settings.top_k

    @property
    def chat_model(self):
        if self._chat_model is None:             # lazily built so import needs no API key
            self._chat_model = get_chat_model()
        return self._chat_model

    async def answer_stream(self, req: AskRequest) -> AsyncIterator[str]:
        conversation_id = req.conversation_id or uuid.uuid4().hex

        # 0. Guardrail: reject prompt-injection before any retrieval/LLM work.
        if detect_prompt_injection(req.question):
            log.warning(
                "blocked prompt injection", stage="guardrail", conversation_id=conversation_id
            )
            yield _sse({"type": "citations", "conversation_id": conversation_id, "citations": []})
            yield _sse({"type": "token", "token": INJECTION_REFUSAL})
            yield _sse({"type": "done"})
            await conversation_service.save_turn(
                conversation_id=conversation_id,
                question=req.question,
                answer=INJECTION_REFUSAL,
                citations=[],
                retrieved_chunk_ids=[],
                timestamp=datetime.now(timezone.utc),
            )
            return

        # 1. Hybrid retrieval (vector + keyword, fused + optionally reranked).
        results = await retrieval.retrieve(req.question, self.top_k, req.document_id)
        docs = [doc for doc, _score in results]
        citations = [
            Citation(
                filename=str(doc.metadata.get("filename", "unknown")),
                chunk_index=int(doc.metadata.get("chunk_index", 0)),
            )
            for doc in docs
        ]
        chunk_ids = [str(doc.metadata.get("chunk_id")) for doc in docs]
        log.info(
            "retrieved", stage="retrieve", conversation_id=conversation_id, matches=len(docs)
        )

        # 2. Emit citations + the conversation id up front so the UI can render
        #    the citation chips before the answer starts streaming.
        yield _sse(
            {
                "type": "citations",
                "conversation_id": conversation_id,
                "citations": [c.model_dump() for c in citations],
            }
        )

        # 3. Grounding guard: no context -> return the sentinel WITHOUT calling
        #    the LLM (it could only improvise).
        if not docs:
            answer = NO_INFO_ANSWER
            yield _sse({"type": "token", "token": answer})
        else:
            messages = build_messages(req.question, docs)
            # Trace this LLM call in Langfuse when configured (no-op otherwise).
            handler = get_langfuse_handler()
            config = {"callbacks": [handler]} if handler else {}
            parts: list[str] = []
            async for chunk in self.chat_model.astream(messages, config=config):
                token = chunk.content if isinstance(chunk.content, str) else ""
                if token:
                    parts.append(token)
                    yield _sse({"type": "token", "token": token})
            answer = "".join(parts)

        yield _sse({"type": "done"})

        # 4. Persist the completed turn.
        await conversation_service.save_turn(
            conversation_id=conversation_id,
            question=req.question,
            answer=answer,
            citations=citations,
            retrieved_chunk_ids=chunk_ids,
            timestamp=datetime.now(timezone.utc),
        )
        log.info("answered", stage="answer", conversation_id=conversation_id)
