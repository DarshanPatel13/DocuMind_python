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
from app.intent import is_aggregate_query
from app.observability import get_langfuse_handler
from app.prompt import NO_INFO_ANSWER, build_messages

log = get_logger(__name__)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


class AskService:
    """The RAG ask use-case — the service layer behind the /api/ask endpoint.

    One public coroutine, `answer_stream`, runs the whole pipeline for a question:
    guardrail check -> choose retrieval strategy -> gather context chunks -> build a
    grounded prompt -> stream the LLM's tokens out as SSE -> persist the turn. The
    chat model is injectable (constructor arg) so tests can pass a fake instead of
    calling a real LLM."""

    def __init__(self, chat_model=None, top_k: int | None = None) -> None:
        self._chat_model = chat_model            # injectable for tests
        self.top_k = top_k or settings.top_k

    @property
    def chat_model(self):
        if self._chat_model is None:             # lazily built so import needs no API key
            self._chat_model = get_chat_model()
        return self._chat_model

    async def _gather_docs(self, req: AskRequest, whole_doc: bool):
        """Pick chunks for the prompt. Whole-document mode (list-all / summarize)
        reads the entire target document; otherwise we use hybrid top-k."""
        if whole_doc:
            document_id = req.document_id
            if document_id is None:
                # No scope chosen: pick the single most relevant document, then read
                # all of it (this is what "list all questions" across docs needs).
                top = await retrieval.retrieve(req.question, 1, None)
                if top:
                    document_id = top[0][0].metadata.get("document_id")
            if document_id is not None:
                docs = await retrieval.fetch_document_chunks(document_id)
                if docs:
                    return docs
        results = await retrieval.retrieve(req.question, self.top_k, req.document_id)
        return [doc for doc, _score in results]

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

        # 1. Choose a retrieval strategy. "List all / summarize the whole document"
        #    queries can't be answered by top-k (it only sees k of N chunks), so for
        #    that intent we read the ENTIRE target document instead.
        whole_doc = is_aggregate_query(req.question)
        docs = await self._gather_docs(req, whole_doc)

        # Cap displayed citations in whole-doc mode (don't flood the UI with N chips).
        cite_docs = docs[:6] if whole_doc else docs
        citations = [
            Citation(
                filename=str(doc.metadata.get("filename", "unknown")),
                chunk_index=int(doc.metadata.get("chunk_index", 0)),
                snippet=doc.page_content[:600],  # source preview for the UI
            )
            for doc in cite_docs
        ]
        chunk_ids = [str(doc.metadata.get("chunk_id")) for doc in docs]
        log.info(
            "retrieved",
            stage="retrieve",
            conversation_id=conversation_id,
            matches=len(docs),
            mode="whole_document" if whole_doc else "hybrid",
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
            messages = build_messages(req.question, docs, whole_document=whole_doc)
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
