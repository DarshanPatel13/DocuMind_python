# ADR-0001: Split the DocuMind monolith into gateway + document-service + query-service

**Status:** Accepted (Day 1)
**Date:** 2026-06-27

## Context
DocuMind started as a FastAPI **modular monolith**: one process handled uploads,
async Kafka ingestion, RAG retrieval, streamed answers, and conversation history
over Postgres/pgvector + MongoDB. The code was already cleanly layered, but a
single deployable can't demonstrate the things a microservices role asks about:
service boundaries, independent scaling/deploys, an API gateway, auth at the edge,
and failure isolation. We want a **minimal but real** split — not a cosmetic one,
and not so granular that the ops overhead drowns the signal.

## Decision
Extract three independently deployable services plus two shared libraries.

- **gateway** — the only public entry point. JWT auth (bcrypt-hashed passwords in
  a tiny `users` table), CORS, Redis-backed rate limiting, and a streaming reverse
  proxy that **passes SSE through unbuffered**.
- **document-service** — owns the `documents` metadata table and file storage;
  validates and stores uploads; publishes `document.uploaded`; runs the ingestion
  consumer (extract → chunk → embed → write pgvector → `READY`) with 3 retries +
  a dead-letter topic.
- **query-service** — owns conversation history (MongoDB); runs the RAG ask flow
  (retrieve → grounded prompt → stream SSE → persist turn).
- **`libs/documind_contracts`** — Pydantic event + DTO models shared by all
  services (the wire contract).
- **`libs/documind_common`** — LLM/embeddings providers + pgvector access, because
  the embedding model, dimensions, and collection name are a **contract** between
  the writer (document-service) and the reader (query-service).

## Consequences

**Positive**
- Clear ownership; each service scales and deploys independently.
- Kafka decouples upload from ingestion — an upload still succeeds (202) even if
  the ingestion consumer is down; the work drains when it returns.
- Cross-cutting concerns (auth, CORS, rate limit) live once, at the edge.
- The split forced the implicit contracts (event shape, embedding settings) to
  become explicit shared packages.

**Negative / accepted compromises**
- **Shared pgvector store.** document-service writes vectors and query-service
  reads them — both touch one Postgres/pgvector database. This is a conscious
  exception to *database-per-service*. We mitigate it by centralizing the
  embedding/collection contract in `documind_common`, so the two sides can't
  silently diverge.
- **Shared libraries couple deploy cadence.** Bumping a lib rebuilds every service
  that depends on it. Acceptable for contracts that *must* agree.
- **More to run locally.** Mitigated by one `docker compose up --build`.

## Alternatives considered
- **Keep the monolith.** Rejected: doesn't demonstrate the target competency.
- **Six services** (separate ingestion-worker, retrieval-service,
  conversation-service, auth-service, …). Rejected for a 3-day scope: more network
  hops and operational surface than the interview signal justifies. The pieces are
  factored so this is an easy future step.

## Next steps (deliberately out of scope — discuss in the interview)
- **Dedicated retrieval-service** that solely owns pgvector behind a `search`/`upsert`
  API → removes the shared-store compromise above.
- **gRPC** for internal service-to-service calls (typed, faster than JSON/REST).
- **Traefik / a managed API gateway** instead of the hand-rolled FastAPI gateway.
- **Keycloak / OIDC** instead of the local `users` table.
- **Kubernetes + Helm** for deployment; **OpenTelemetry** tracing across services.
