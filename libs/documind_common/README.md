# `documind_common` — shared RAG plumbing

The minimal set of RAG internals that **must behave identically** in the service
that writes vectors and the service that reads them.

| Module | What it does | Used by |
|---|---|---|
| `providers.py` | `get_chat_model()`, `get_embeddings()` — provider-pluggable LLM | query-service (chat + embeddings), document-service (embeddings) |
| `vector_store.py` | `add_chunks()` (write), `search()` (read) over pgvector | document-service writes, query-service reads |
| `config.py` | pins embedding model, dimensions, collection name, pgvector URL | both |
| `logging.py` | structlog setup, `get_logger()` | all services |

## Why is this shared, when "database per service" says don't share?

Because the **embedding contract** is the thing that must not drift:

- A vector written with `text-embedding-3-small` @ 1536 dims into collection
  `documind_chunks` is only findable by a query embedded with the *same* model,
  *same* dims, in the *same* collection.
- If document-service and query-service each kept their own copy of these
  settings and one changed, retrieval would return **nothing** — with no error.

So we treat the embedding model + dimensions + collection as a contract and keep
it in one place, exactly like `documind_contracts` does for event shapes.

## The honest trade-off (state this in the interview)

This package means document-service and query-service **share the pgvector
store** — a conscious exception to strict database-per-service. We accept it for
the 3-day scope and isolate the risk by centralizing the contract here.

> **Next step:** extract a dedicated **retrieval-service** that solely owns
> pgvector and exposes a `search`/`upsert` API (REST or gRPC). Then document- and
> query-service no longer touch the same database, and `vector_store.py` becomes
> that service's internals instead of a shared lib. See `docs/adr/0001`.

**Java analogy:** a shared `*-common` module for cross-cutting infra clients
(your shared `JdbcTemplate`/repository config). Convenient and DRY, but it
couples the deploy cadence of everything that depends on it — the same reason
some teams forbid shared libs between microservices.
