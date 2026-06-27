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

Java analogy: a Strategy interface (`Reranker`) with swappable implementations,
chosen by config — like wiring a different `@Qualifier` bean.
"""
from __future__ import annotations

from typing import Protocol

from langchain_core.documents import Document

from documind_common.config import settings


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


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    """Lazily build the configured reranker singleton."""
    global _reranker
    if _reranker is None:
        if settings.reranker.lower() == "cross-encoder":
            _reranker = CrossEncoderReranker(settings.reranker_model)
        else:
            _reranker = NoOpReranker()
    return _reranker
