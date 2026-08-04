"""Condense a follow-up question plus recent history into a standalone query.

Retrieval embeds the question on its own, with no memory. So "and for digital
goods?" embeds as a question about digital goods and nothing else — the topic it
is a follow-up *to* is missing from the vector, and the right chunks never come
back. Multi-turn memory in the prompt does not fix this: by the time the prompt
is built, retrieval has already happened against the wrong query.

So the rewrite happens BEFORE embedding, and only the RETRIEVAL query is
rewritten. The answer model still sees the user's original wording, because
rewriting what the user actually asked would put words in their mouth.

Costs one small LLM call per turn that has history. Toggle with REWRITE_ENABLED
to A/B it against the eval suite.
"""
from __future__ import annotations

from documind_common.logging import get_logger
from documind_common.providers import get_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You rewrite a follow-up question into a standalone search query.\n"
    "Use the conversation history to resolve pronouns and implied subjects.\n"
    "Reply with ONLY the rewritten query — no preamble, no quotes, no explanation.\n"
    "If the question is already standalone, reply with it unchanged."
)

# A rewrite that balloons is a sign the model started answering instead of
# rewriting; we fall back rather than embed a paragraph.
_MAX_REWRITE_CHARS = 300


def _format_history(history: list[tuple[str, str]]) -> str:
    return "\n".join(f"User: {q}\nAssistant: {a}" for q, a in history)


class QueryRewriter:
    """Chat model injectable so tests never call a real LLM."""

    def __init__(self, chat_model=None) -> None:
        self._chat_model = chat_model

    @property
    def chat_model(self):
        if self._chat_model is None:
            self._chat_model = get_chat_model()
        return self._chat_model

    async def rewrite(self, question: str, history: list[tuple[str, str]]) -> str:
        """Return a standalone retrieval query, or the original question.

        Fails open in every failure mode — a rewriter outage must degrade
        retrieval quality, never take the ask flow down."""
        if not history:
            return question                      # first turn: nothing to resolve

        user = (
            f"Conversation so far:\n{_format_history(history)}\n\n"
            f"Follow-up question: {question}\n\nStandalone search query:"
        )
        try:
            response = await self.chat_model.ainvoke(
                [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]
            )
            rewritten = (response.content or "").strip() if isinstance(response.content, str) else ""
        except Exception as exc:  # noqa: BLE001 — never break retrieval on a rewrite
            log.warning("rewrite failed", stage="rewrite-failed", error=str(exc))
            return question

        if not rewritten or len(rewritten) > _MAX_REWRITE_CHARS:
            log.warning("rewrite unusable; keeping original", stage="rewrite-unusable")
            return question

        log.info("rewrote query", stage="rewrite", original=question, rewritten=rewritten)
        return rewritten
