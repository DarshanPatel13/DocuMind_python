# DocuMind — Architecture (C4 Container view)

DocuMind is a RAG document Q&A app: upload PDFs, ask questions, get a grounded,
streamed answer with `[filename, chunk N]` citations.

## Container diagram

```mermaid
C4Container
  title DocuMind — Container Diagram (Day-1 target)
  Person(user, "User", "Uploads PDFs, asks questions")

  System_Boundary(dm, "DocuMind") {
    Container(fe, "Frontend", "React 18 + Vite + Nginx", "Chat UI, upload, streaming answers")
    Container(gw, "API Gateway / BFF", "FastAPI + httpx", "JWT auth, CORS, Redis rate-limit, routing + SSE pass-through")
    Container(doc, "document-service", "FastAPI + aiokafka", "Upload, metadata, ingestion consumer (extract->chunk->embed)")
    Container(qry, "query-service", "FastAPI + LangChain", "RAG retrieve->prompt->stream SSE, conversation history")
    ContainerDb(pg, "PostgreSQL + pgvector", "Postgres 16", "documents metadata + chunk vectors (shared store)")
    ContainerDb(mongo, "MongoDB", "Mongo 7", "conversation history")
    ContainerQueue(kafka, "Kafka", "KRaft", "document-events + DLT")
    ContainerDb(redis, "Redis", "Redis 7", "rate-limit counters")
  }
  System_Ext(openai, "OpenAI", "Embeddings + chat (Claude pluggable)")

  Rel(user, fe, "Uses", "HTTPS")
  Rel(fe, gw, "API calls + SSE", "HTTPS/JSON")
  Rel(gw, doc, "REST", "JSON")
  Rel(gw, qry, "REST + SSE stream", "JSON")
  Rel(gw, redis, "rate-limit check", "")
  Rel(doc, pg, "metadata + WRITE vectors", "SQL")
  Rel(doc, kafka, "publish + consume document-events", "")
  Rel(doc, openai, "embeddings", "HTTPS")
  Rel(qry, pg, "READ vectors (retrieval)", "SQL")
  Rel(qry, mongo, "read/write turns", "")
  Rel(qry, openai, "embeddings + chat", "HTTPS")
```

## The two request flows

**Upload & ingestion (async).** Browser → gateway → document-service stores the
PDF, writes an `UPLOADED` row, and publishes `document.uploaded`. The ingestion
consumer (inside document-service) extracts → chunks → embeds → writes vectors to
pgvector → marks `READY`. Failures retry 3× then land on the DLT as `FAILED`.

**Ask (sync, streamed).** Browser → gateway (JWT + rate-limit) → query-service
embeds the question, does a top-k cosine search in pgvector, builds a grounded
prompt, and **streams** the answer back as SSE — passed through the gateway
unbuffered — then persists the turn to MongoDB.

## Service responsibilities

| Service | Owns | Talks to |
|---|---|---|
| **gateway** | `users` table, JWT, rate-limit counters | document-service, query-service, Redis |
| **document-service** | `documents` table, file storage, ingestion | Postgres, Kafka, pgvector (write), OpenAI |
| **query-service** | `conversation_turns` | Postgres/pgvector (read), MongoDB, OpenAI |

## Shared building blocks

- **`libs/documind_contracts`** — Pydantic events + DTOs (the wire contract).
- **`libs/documind_common`** — providers + pgvector access + the embedding
  config that the writer and reader must agree on.

See [`../adr/0001-microservices-split.md`](../adr/0001-microservices-split.md)
for why the split looks like this and the trade-offs we accepted.
