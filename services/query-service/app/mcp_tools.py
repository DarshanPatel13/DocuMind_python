"""DocuMind exposed as MCP (Model Context Protocol) tools.

MCP is the open protocol that lets an external AI client — Claude Desktop, an
IDE assistant, another agent — discover and call tools on a server. Adding it
turns this from "a RAG app with its own UI" into "a knowledge source any agent
can query", with the same retrieval, guardrails and grounding rules the HTTP
flow uses.

Two tools with deliberately different shapes:

  * `search_documents` returns raw cited passages, so the CALLING model can
    reason over them itself.
  * `ask_documind` runs the full grounded pipeline and returns a finished,
    citation-bearing answer.

The grounding rules are not relaxed for machine callers. An agent that receives
near-miss passages will launder them into its own context and answer from them,
so the relevance gate applies here exactly as it does in the UI — arguably more,
because there is no human reading the citations.
"""
from __future__ import annotations

import uuid

from documind_common import retrieval
from documind_common.config import settings
from documind_common.logging import get_logger
from documind_common.providers import get_chat_model

from app.guardrails import INJECTION_REFUSAL, detect_prompt_injection
from app.intent import is_aggregate_query
from app.prompt import NO_INFO_ANSWER, build_messages

log = get_logger(__name__)

SNIPPET_CHARS = 800

NO_PASSAGES = "No matching passages found in the uploaded documents."


def _parse_id(document_id: str | None) -> uuid.UUID | None:
    if not document_id or not document_id.strip():
        return None
    try:
        return uuid.UUID(document_id.strip())
    except ValueError:
        return None                              # treat a malformed id as "search everything"


def _truncate(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS] + "…"


async def search_documents(query: str, document_id: str | None = None) -> str:
    """Search the user's uploaded documents and return the most relevant passages,
    each labelled [filename, chunk N]. Use this when you want the raw source text
    to reason over or quote yourself."""
    if detect_prompt_injection(query):
        return INJECTION_REFUSAL

    result = await retrieval.retrieve_scored(query, settings.top_k, _parse_id(document_id))
    log.info("mcp search", stage="mcp-search", matches=len(result.docs), relevant=result.relevant)

    if not result.relevant:
        return NO_PASSAGES

    return "\n---\n".join(
        f"[{doc.metadata.get('filename', 'unknown')}, "
        f"chunk {doc.metadata.get('chunk_index', 0)}]\n{_truncate(doc.page_content)}"
        for doc in result.docs
    )


async def ask_documind(question: str, document_id: str | None = None, chat_model=None) -> str:
    """Ask a natural-language question about the user's uploaded documents and get
    a grounded answer with [filename, chunk N] citations. Answers strictly from
    the documents; says it lacks the information rather than guessing."""
    if detect_prompt_injection(question):
        return INJECTION_REFUSAL

    doc_id = _parse_id(document_id)
    whole_doc = is_aggregate_query(question)

    if whole_doc:
        docs = await retrieval.fetch_document_chunks(doc_id) if doc_id else []
        result = retrieval.RetrievalResult.scoped(docs)
    else:
        result = await retrieval.retrieve_scored(question, settings.top_k, doc_id)

    # Same grounding guard as the HTTP flow: no RELEVANT context -> no LLM call.
    if not result.relevant:
        log.info("mcp refused", stage="mcp-refuse", best=result.best_vector_distance)
        return NO_INFO_ANSWER

    model = chat_model or get_chat_model()
    messages = build_messages(question, result.docs, whole_document=whole_doc)
    response = await model.ainvoke(messages)
    log.info("mcp ask", stage="mcp-ask", matches=len(result.docs), mode="whole" if whole_doc else "hybrid")
    return response.content if isinstance(response.content, str) else str(response.content)


def register(mcp) -> None:
    """Attach the tools to a FastMCP server.

    Kept as a function rather than import-time decorators so the module can be
    imported (and unit-tested) without the MCP dependency present."""
    mcp.tool()(search_documents)
    mcp.tool()(ask_documind)
