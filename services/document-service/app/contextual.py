"""Contextual retrieval: give each chunk enough context to be found on its own.

Chunking destroys context. A chunk reading "Unused days above this cap are
forfeited on 31 March" is unambiguous inside the handbook and meaningless as an
isolated vector — nothing in it says *PTO carryover*, so a question about
carryover embeds nowhere near it. This is the single biggest silent source of
retrieval misses, and it looks like a model problem when it is a chunking one.

The fix (Anthropic's "contextual retrieval"): before embedding, prepend one or
two sentences that situate the chunk inside its document. The prefix is embedded
and indexed, so it changes what the chunk MATCHES; the original text still
carries the answer.

Cost is one small LLM call per chunk at ingestion — real, but paid once at write
time rather than on every query, and ingestion is already async behind Kafka.
Off by default (`CONTEXTUAL_RETRIEVAL_ENABLED`) so it is an opt-in you can A/B
against the eval suite rather than an invisible cost.
"""
from __future__ import annotations

import asyncio

from documind_common.config import settings
from documind_common.logging import get_logger
from documind_common.providers import get_chat_model

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You situate an excerpt inside its source document so it can be understood "
    "and searched on its own.\n"
    "Reply with ONE short sentence naming the document's subject and the section "
    "or topic this excerpt belongs to.\n"
    "Do not summarize the excerpt. Do not add facts. No preamble, no quotes."
)

# A context line that runs long stops being a locator and starts competing with
# the chunk's own text for the embedding.
_MAX_CONTEXT_CHARS = 220


def _prompt(document_summary: str, chunk: str) -> str:
    return (
        f"Document (beginning):\n{document_summary}\n\n"
        f"Excerpt:\n{chunk}\n\n"
        "One-sentence context for this excerpt:"
    )


async def _context_for(chat_model, document_summary: str, chunk: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        response = await chat_model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_prompt(document_summary, chunk)),
            ]
        )
        text = (response.content or "").strip() if isinstance(response.content, str) else ""
    except Exception as exc:  # noqa: BLE001 — enrichment must never fail an ingest
        log.warning("context failed", stage="contextual-failed", error=str(exc))
        return ""

    if len(text) > _MAX_CONTEXT_CHARS:
        return ""
    return text


async def enrich(chunks: list[str], *, chat_model=None) -> list[str]:
    """Return chunks with a one-line context prefix, or unchanged if disabled.

    Fails open per chunk: any chunk whose context call fails is kept exactly as
    it was, so a provider blip degrades retrieval quality rather than losing
    documents. Calls run concurrently — this is the slowest stage otherwise."""
    if not settings.contextual_retrieval_enabled or not chunks:
        return chunks

    model = chat_model or get_chat_model()
    document_summary = chunks[0][: settings.contextual_context_chars]

    contexts = await asyncio.gather(
        *(_context_for(model, document_summary, chunk) for chunk in chunks)
    )
    enriched = [f"{ctx}\n\n{chunk}" if ctx else chunk for ctx, chunk in zip(contexts, chunks)]

    added = sum(1 for c in contexts if c)
    log.info("contextualized", stage="contextual", chunks=len(chunks), enriched=added)
    return enriched
