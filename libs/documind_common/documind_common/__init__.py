"""DocuMind shared RAG plumbing.

Why these specific pieces are shared (and not the whole app):

The vector store has a **writer** (document-service, during ingestion) and a
**reader** (query-service, during retrieval). For retrieval to return anything,
both sides MUST use the same embedding model, the same vector dimensions, and the
same pgvector collection name. Those three settings are therefore a *contract* —
if they drift, retrieval silently returns nothing and nobody gets an error.

So we centralize exactly that contract here: the providers (`get_embeddings`,
`get_chat_model`), the vector-store access, and the config that pins the
embedding model/dimensions/collection. Everything else stays inside each service.
"""
from documind_common.config import settings
from documind_common.logging import configure_logging, get_logger
from documind_common.providers import get_chat_model, get_embeddings
from documind_common.reranker import get_reranker
from documind_common.retrieval import reciprocal_rank_fusion, retrieve
from documind_common.vector_store import add_chunks, get_vector_store, search

__all__ = [
    "settings",
    "configure_logging",
    "get_logger",
    "get_chat_model",
    "get_embeddings",
    "add_chunks",
    "get_vector_store",
    "search",
    "retrieve",
    "reciprocal_rank_fusion",
    "get_reranker",
]
