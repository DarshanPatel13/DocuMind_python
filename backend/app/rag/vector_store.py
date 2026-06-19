"""pgvector access via LangChain's PGVector integration.

PGVector's client is synchronous (it does blocking DB I/O and, for queries,
a blocking embeddings HTTP call). We wrap each call in `asyncio.to_thread` so
it runs on a worker thread and never blocks FastAPI's event loop — simpler and
more robust than PGVector's newer async mode.
"""
from __future__ import annotations

import asyncio
import uuid

from langchain_core.documents import Document
from langchain_postgres import PGVector

from app.core.config import settings
from app.rag.providers import get_embeddings

_store: PGVector | None = None


def get_vector_store() -> PGVector:
    """Lazily build the singleton store. use_jsonb=True enables metadata
    filtering (e.g. scope a query to one document_id)."""
    global _store
    if _store is None:
        _store = PGVector(
            embeddings=get_embeddings(),
            collection_name=settings.vector_collection,
            connection=settings.pgvector_url,
            use_jsonb=True,
        )
    return _store


async def add_chunks(document_id: uuid.UUID, filename: str, chunks: list[str]) -> int:
    """Embed and upsert chunks. IDs are deterministic ("{document_id}:{i}") so a
    re-run overwrites by id instead of duplicating — that, plus the READY guard
    in the consumer, is what makes ingestion idempotent."""
    store = get_vector_store()
    ids = [f"{document_id}:{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "document_id": str(document_id),
            "filename": filename,
            "chunk_index": i,
            "chunk_id": ids[i],
        }
        for i in range(len(chunks))
    ]
    await asyncio.to_thread(store.add_texts, texts=chunks, metadatas=metadatas, ids=ids)
    return len(chunks)


async def search(
    query: str, k: int, document_id: uuid.UUID | None
) -> list[tuple[Document, float]]:
    """Top-k cosine similarity search, optionally scoped to one document.
    Returns (Document, distance) pairs — lower distance = more similar."""
    store = get_vector_store()
    flt = {"document_id": {"$eq": str(document_id)}} if document_id is not None else None
    return await asyncio.to_thread(
        store.similarity_search_with_score, query, k=k, filter=flt
    )
