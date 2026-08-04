"""Pluggable reranker for the second stage of retrieval.

A reranker re-scores the candidate chunks against the query with a model that
sees the *pair* (query, chunk) together — a cross-encoder — which is far more
accurate than the bi-encoder cosine similarity used for first-stage recall, but
too slow to run over the whole corpus. So the pattern is: cheap recall (vector +
keyword) → expensive precision (rerank the top ~20).

Default is `none` (keeps the fused order) so the container image stays
torch-free. Set `RERANKER=cross-encoder` to load a sentence-transformers
cross-encoder. Cohere's rerank API is a lighter production alternative (no local
torch) — noted in docs/ai/rag-architecture.md.

This is the Strategy pattern: a `Reranker` `Protocol` with swappable
implementations selected by the `RERANKER` config value.
"""
from __future__ import annotations

import re
from typing import Protocol

from langchain_core.documents import Document

from documind_common.config import settings
from documind_common.logging import get_logger

log = get_logger(__name__)


class Reranker(Protocol):
    def rerank(self, query: str, docs: list[Document]) -> list[tuple[Document, float]]:
        """Return docs newly ordered best-first, each with a relevance score."""
        ...


class NoOpReranker:
    """Keeps the incoming (fused) order. Scores are a descending rank proxy so
    callers get a uniform (Document, score) shape regardless of backend."""

    def rerank(self, query: str, docs: list[Document]) -> list[tuple[Document, float]]:
        n = len(docs)
        return [(doc, float(n - i)) for i, doc in enumerate(docs)]


class CrossEncoderReranker:
    """sentence-transformers cross-encoder. Imported lazily so the dependency
    (and torch) is only needed when this backend is actually selected."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, docs: list[Document]) -> list[tuple[Document, float]]:
        if not docs:
            return []
        pairs = [(query, doc.page_content) for doc in docs]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(docs, scores), key=lambda t: float(t[1]), reverse=True)
        return [(doc, float(score)) for doc, score in ranked]


class LlmReranker:
    """Listwise reranker: shows the model every candidate at once and asks for
    their indices in relevance order.

    Listwise (one call ranking everything) rather than pointwise (one call each)
    because it is N times cheaper, one round-trip of latency instead of N, and it
    lets the model compare candidates against each other — the judgement RRF
    structurally cannot make.

    Pick this over the cross-encoder when you want reranking without torch: it
    reuses the already-configured chat model, so it works with every provider the
    app supports and adds nothing to the image. A cross-encoder is faster and
    cheaper per query if you can afford the install — that is the trade, and
    `Reranker` is the seam that makes choosing between them a config change.
    """

    _SYSTEM = (
        "You rank search results by how well they answer a question.\n"
        "You are given numbered passages. Reply with ONLY the passage numbers,\n"
        'most relevant first, comma-separated (e.g. "3,1,7").\n'
        "Include every number exactly once. No other text, no explanations."
    )

    def __init__(self, chat_model=None) -> None:
        self._chat_model = chat_model            # injectable for tests

    @property
    def chat_model(self):
        if self._chat_model is None:             # lazy: importing must not need a key
            from documind_common.providers import get_chat_model

            self._chat_model = get_chat_model()
        return self._chat_model

    def rerank(self, query: str, docs: list[Document]) -> list[tuple[Document, float]]:
        if not docs:
            return []
        if len(docs) == 1:
            return [(docs[0], 1.0)]              # nothing to decide; skip the call

        from langchain_core.messages import HumanMessage, SystemMessage

        limit = settings.rerank_snippet_chars
        passages = "\n\n".join(
            f"{i + 1}. {doc.page_content[:limit]}".replace("\n", " ")
            for i, doc in enumerate(docs)
        )
        try:
            response = self.chat_model.invoke(
                [
                    SystemMessage(content=self._SYSTEM),
                    HumanMessage(content=f"Question: {query}\n\nPassages:\n{passages}"),
                ]
            )
            reply = response.content if isinstance(response.content, str) else ""
        except Exception as exc:  # noqa: BLE001 — fail open; an outage must not break retrieval
            log.warning("rerank failed; keeping fusion order", stage="rerank-failed", error=str(exc))
            return NoOpReranker().rerank(query, docs)

        ordered = _apply_order(reply, docs)
        if not ordered:
            log.warning("rerank unparseable; keeping fusion order", stage="rerank-unparseable")
            return NoOpReranker().rerank(query, docs)

        n = len(ordered)
        return [(doc, float(n - i)) for i, doc in enumerate(ordered)]


def _apply_order(reply: str, docs: list[Document]) -> list[Document]:
    """Parse "3,1,7" into candidate order.

    Tolerant by design: ignores junk and out-of-range numbers, dedupes, and
    appends anything the model omitted, so no candidate is ever silently lost."""
    if not reply or not reply.strip():
        return []
    seen: list[int] = []
    for match in re.findall(r"\d+", reply):
        idx = int(match) - 1                     # the model is 1-based
        if 0 <= idx < len(docs) and idx not in seen:
            seen.append(idx)
    if not seen:
        return []
    ordered = [docs[i] for i in seen]
    ordered.extend(doc for i, doc in enumerate(docs) if i not in seen)
    return ordered


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    """Lazily build the configured reranker singleton."""
    global _reranker
    if _reranker is None:
        backend = settings.reranker.lower()
        if backend == "cross-encoder":
            _reranker = CrossEncoderReranker(settings.reranker_model)
        elif backend == "llm":
            _reranker = LlmReranker()
        else:
            _reranker = NoOpReranker()
    return _reranker
