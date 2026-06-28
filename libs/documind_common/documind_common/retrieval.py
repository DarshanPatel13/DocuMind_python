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

Java analogy: think of this as composing two Spring Data queries (a vector
similarity query + a full-text query) and merging the result pages with a
fusion ranker.
"""
from __future__ import annotations

import asyncio
import uuid

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


async def _vector_candidates(query: str, n: int, document_id: uuid.UUID | None) -> list[Document]:
    store = get_vector_store()
    flt = {"document_id": {"$eq": str(document_id)}} if document_id is not None else None
    pairs = await asyncio.to_thread(store.similarity_search_with_score, query, k=n, filter=flt)
    return [doc for doc, _score in pairs]


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


async def retrieve(
    query: str,
    k: int,
    document_id: uuid.UUID | None = None,
    *,
    use_reranker: bool | None = None,
) -> list[tuple[Document, float]]:
    """Public entrypoint used by the ask flow and the eval harness.

    Returns up to `k` (Document, score) pairs, best-first. `use_reranker`
    overrides the configured default (handy for before/after eval)."""
    n = settings.retrieval_candidates

    if settings.hybrid_enabled:
        vector_docs, keyword_docs = await asyncio.gather(
            _vector_candidates(query, n, document_id),
            _keyword_candidates(query, n, document_id),
        )
        fused = reciprocal_rank_fusion([vector_docs, keyword_docs])
    else:
        fused = [(d, 1.0 / (i + 1)) for i, d in enumerate(await _vector_candidates(query, n, document_id))]

    docs = [doc for doc, _ in fused]
    should_rerank = (settings.reranker.lower() != "none") if use_reranker is None else use_reranker

    if should_rerank and docs:
        reranked = await asyncio.to_thread(get_reranker().rerank, query, docs)
        return reranked[:k]
    return fused[:k]
