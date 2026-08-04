"""Hybrid retrieval: dense vectors + sparse keywords, fused, then reranked.

Pipeline (the "two-stage retriever" pattern):
  1. RECALL — run two arms in parallel:
       * vector arm   : pgvector cosine similarity (semantic match)
       * keyword arm  : Postgres full-text search (exact term / acronym match)
  2. FUSE   — combine the two ranked lists with Reciprocal Rank Fusion (RRF),
              which needs no score calibration between the arms.
  3. RERANK — optionally re-score the fused top-N with a cross-encoder and trim
              to top-k (see reranker.py).

Why hybrid: dense vectors are great at meaning but miss rare exact tokens (IDs,
codes, names); keyword search nails those but misses paraphrases. Fusing both is
consistently better than either alone — the before/after is measured in
`eval/` (see docs/ai/evaluation.md).
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import psycopg
from langchain_core.documents import Document

from documind_common.config import settings
from documind_common.logging import get_logger
from documind_common.reranker import get_reranker
from documind_common.vector_store import get_vector_store

log = get_logger(__name__)

RRF_K = 60  # standard RRF damping constant; larger = flatter contribution by rank


def _doc_key(doc: Document) -> str:
    """Stable identity for de-duplication/fusion across the two arms."""
    cid = doc.metadata.get("chunk_id")
    if cid:
        return str(cid)
    return f"{doc.metadata.get('document_id')}:{doc.metadata.get('chunk_index')}"


async def _vector_candidates_scored(
    query: str, n: int, document_id: uuid.UUID | None
) -> list[tuple[Document, float]]:
    """Dense arm, keeping the cosine DISTANCE alongside each document.

    That distance is the only calibrated relevance signal in the whole pipeline —
    RRF replaces it with rank-only scores and a reranker only reorders — so it is
    deliberately carried out of here rather than dropped at the door."""
    store = get_vector_store()
    flt = {"document_id": {"$eq": str(document_id)}} if document_id is not None else None
    pairs = await asyncio.to_thread(store.similarity_search_with_score, query, k=n, filter=flt)
    # langchain-postgres returns `result.distance` under its default COSINE
    # strategy: 0 = identical direction, lower is closer.
    return [(doc, float(score)) for doc, score in pairs]


async def _vector_candidates(query: str, n: int, document_id: uuid.UUID | None) -> list[Document]:
    return [doc for doc, _ in await _vector_candidates_scored(query, n, document_id)]


def _keyword_sql_sync(query: str, n: int, document_id: uuid.UUID | None) -> list[Document]:
    # Query the same table pgvector uses (langchain_pg_embedding) so we don't keep
    # a second copy of the text. `websearch_to_tsquery` parses natural queries
    # safely (no injection of tsquery operators).
    sql = """
        SELECT e.document, e.cmetadata
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = %(coll)s
          AND (%(doc)s::text IS NULL OR e.cmetadata->>'document_id' = %(doc)s)
          AND to_tsvector('english', e.document) @@ websearch_to_tsquery('english', %(q)s)
        ORDER BY ts_rank(
            to_tsvector('english', e.document),
            websearch_to_tsquery('english', %(q)s)
        ) DESC
        LIMIT %(n)s
    """
    params = {
        "coll": settings.vector_collection,
        "doc": str(document_id) if document_id is not None else None,
        "q": query,
        "n": n,
    }
    with psycopg.connect(settings.psycopg_conninfo) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [Document(page_content=text, metadata=meta or {}) for text, meta in rows]


async def _keyword_candidates(query: str, n: int, document_id: uuid.UUID | None) -> list[Document]:
    if not query.strip():
        return []
    try:
        return await asyncio.to_thread(_keyword_sql_sync, query, n, document_id)
    except Exception as exc:  # noqa: BLE001 — keyword arm is best-effort; degrade to vector-only
        log.warning("keyword arm failed; vector-only", stage="retrieve", error=str(exc))
        return []


def _all_chunks_sync(document_id: str, limit: int) -> list[Document]:
    # Every chunk of one document, in reading order — used by "whole-document" mode
    # for list-all / summarize queries that top-k retrieval can't satisfy.
    sql = """
        SELECT e.document, e.cmetadata
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = %(coll)s
          AND e.cmetadata->>'document_id' = %(doc)s
        ORDER BY (e.cmetadata->>'chunk_index')::int ASC
        LIMIT %(n)s
    """
    params = {"coll": settings.vector_collection, "doc": document_id, "n": limit}
    with psycopg.connect(settings.psycopg_conninfo) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [Document(page_content=text, metadata=meta or {}) for text, meta in rows]


async def fetch_document_chunks(document_id: uuid.UUID | str, limit: int = 120) -> list[Document]:
    """Return up to `limit` chunks of one document, ordered by chunk_index.

    (At very large scale this is where you'd map-reduce instead of stuffing the
    whole document into one prompt — noted as a next step.)"""
    return await asyncio.to_thread(_all_chunks_sync, str(document_id), limit)


def reciprocal_rank_fusion(
    ranked_lists: list[list[Document]], k: int = RRF_K
) -> list[tuple[Document, float]]:
    """Fuse ranked lists. RRF score = sum over lists of 1 / (k + rank), so a doc
    near the top of either arm rises, and being in both arms compounds."""
    scores: dict[str, float] = {}
    keep: dict[str, Document] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            keep.setdefault(key, doc)
    ordered = sorted(keep.values(), key=lambda d: scores[_doc_key(d)], reverse=True)
    return [(doc, scores[_doc_key(doc)]) for doc in ordered]


@dataclass(frozen=True)
class RetrievalResult:
    """What retrieval found, plus whether any of it is actually about the question.

    The second part is why this type exists. A bare list of chunks cannot express
    "I returned four rows and none of them are relevant", yet that is the normal
    state of a RAG system asked something outside its corpus — and the state a
    grounding guard has to detect. Separating "what came back" from "is any of it
    evidence" stops callers inferring the second from the length of the first.

    `best_vector_distance` is the diagnostic to watch when calibrating
    `max_distance`; `keyword_hits` is independent evidence, because
    `websearch_to_tsquery` ANDs its terms, so a hit means every content word of
    the question appeared in one chunk.
    """

    scored_docs: list[tuple[Document, float]]
    relevant: bool
    best_vector_distance: float | None
    keyword_hits: int

    @property
    def docs(self) -> list[Document]:
        return [doc for doc, _ in self.scored_docs]

    @classmethod
    def scoped(cls, docs: list[Document]) -> "RetrievalResult":
        """Whole-document reads: the user scoped them, so presence is relevance."""
        return cls([(d, 0.0) for d in docs], bool(docs), None, 0)


def _is_relevant(best_distance: float | None, keyword_hits: int, has_docs: bool) -> bool:
    """Two independent ways to be relevant, because the arms fail on different
    questions and refusing when either succeeds would undo hybrid retrieval.

    Dense: the nearest chunk is within `max_distance` — semantic evidence.
    Sparse: the keyword arm matched at all — lexical evidence, and strong, since
    the tsquery ANDs its terms. That arm is exactly what rescues exact-token
    queries (a policy code, an ID) where embeddings are weakest, so gating on
    distance alone would refuse the queries hybrid search exists to answer."""
    if not has_docs:
        return False
    if settings.max_distance <= 0:
        return True                                     # gate disabled
    return (best_distance is not None and best_distance <= settings.max_distance) or keyword_hits > 0


async def retrieve_scored(
    query: str,
    k: int,
    document_id: uuid.UUID | None = None,
    *,
    use_reranker: bool | None = None,
) -> RetrievalResult:
    """Retrieval plus a relevance verdict — the entrypoint the ask flow uses.

    The verdict is computed on the RAW arms, before fusion, because that is the
    last point a calibrated distance exists."""
    n = settings.retrieval_candidates

    if settings.hybrid_enabled:
        vector_pairs, keyword_docs = await asyncio.gather(
            _vector_candidates_scored(query, n, document_id),
            _keyword_candidates(query, n, document_id),
        )
        fused = reciprocal_rank_fusion([[d for d, _ in vector_pairs], keyword_docs])
    else:
        vector_pairs = await _vector_candidates_scored(query, n, document_id)
        keyword_docs = []
        fused = [(d, 1.0 / (i + 1)) for i, (d, _) in enumerate(vector_pairs)]

    docs = [doc for doc, _ in fused]
    should_rerank = (settings.reranker.lower() != "none") if use_reranker is None else use_reranker

    if should_rerank and docs:
        pool = docs[: settings.rerank_pool]
        scored = (await asyncio.to_thread(get_reranker().rerank, query, pool))[:k]
    else:
        scored = fused[:k]

    best_distance = min((dist for _, dist in vector_pairs), default=None)
    relevant = _is_relevant(best_distance, len(keyword_docs), bool(scored))

    log.info(
        "relevance",
        stage="relevance",
        relevant=relevant,
        best_vector_distance=best_distance,
        keyword_hits=len(keyword_docs),
        threshold=settings.max_distance,
    )
    return RetrievalResult(scored, relevant, best_distance, len(keyword_docs))


async def retrieve(
    query: str,
    k: int,
    document_id: uuid.UUID | None = None,
    *,
    use_reranker: bool | None = None,
) -> list[tuple[Document, float]]:
    """Retrieval only, no relevance verdict — used by the eval harness, which
    measures raw retrieval quality separately from the refusal policy.

    Delegates to `retrieve_scored` so there is one implementation and the two
    entrypoints cannot drift."""
    result = await retrieve_scored(query, k, document_id, use_reranker=use_reranker)
    return result.scored_docs
