# Interview cheatsheet — grounded in DocuMind

Answers you can give with *"let me show you in my project."* Keep them concrete.

---

## Microservices

**Q: Walk me through your architecture.**
Three services behind a gateway. `document-service` owns uploads + metadata +
async ingestion; `query-service` owns the RAG ask flow + conversation history;
the `gateway` is the only public entry point (JWT auth, CORS, rate limiting, and a
streaming reverse proxy). Kafka decouples upload from ingestion; Postgres/pgvector,
MongoDB, and Redis are the stores. Diagram: `docs/architecture/container.md`.

**Q: How do services communicate?**
Async via **Kafka** (`document.uploaded` event) so upload returns `202` instantly
and ingestion happens independently. Sync via **REST** through the gateway. The
event shape is a shared Pydantic contract (`documind_contracts`).

**Q: What happens when a service is down?**
If `document-service`'s ingestion consumer is down, uploads still succeed — the
event sits in Kafka and drains when it recovers (demo: the failure drill in the
runbook). If `query-service` is down, the gateway returns the upstream error; auth
and rate-limit still happen at the edge. Failed ingestions retry 3× then go to a
**dead-letter topic** and the doc is marked `FAILED`.

**Q: Database-per-service — did you follow it?**
Mostly, with one *documented* exception (ADR-0001): `document-service` writes
vectors and `query-service` reads them from a shared pgvector store. I made the
embedding model/dimensions/collection a shared contract so they can't drift, and
the next step is a dedicated retrieval-service that owns pgvector.

**Q: How do you trace a request across services?**
A correlation id: the gateway assigns `X-Request-ID`, forwards it, and every
service binds it to structlog — so one request shares an id across all logs
(`docs/runbook.md` shows the grep). It's the MDC/`traceId` pattern; the next step
is OpenTelemetry + Jaeger.

---

## Python

**Q: Why async? How does it work here?**
FastAPI runs on an event loop; `async def` handlers never block it, so one process
serves many concurrent requests. Blocking/native calls (pgvector, pypdf) are pushed
off the loop with `asyncio.to_thread`. Java analogy: reactive `Flux` or virtual
threads.

**Q: How is config/validation handled?**
pydantic-settings (`@ConfigurationProperties`) for typed env config; Pydantic models
validate every request/response and Kafka event. The streamed answer is a FastAPI
`StreamingResponse` over Server-Sent Events.

**Q: How do you test it?**
pytest + monkeypatch (JUnit + Mockito). E.g. the grounding test asserts that with
no retrieved chunks the LLM is **never called** and the sentinel is returned; the
guardrail test asserts an injection attempt is blocked before retrieval.

---

## React / Frontend

**Q: How do you manage server vs client state?**
**TanStack Query** owns server state (documents, history) with caching + polling;
local component state / Context for UI. The streaming answer uses `fetch` +
`ReadableStream` (axios can't stream in the browser).

**Q: What's your component system?**
shadcn/ui — Radix primitives + Tailwind tokens + a `cn()` helper, so I *own the
component source* and theming is CSS variables (instant dark mode). Accessible by
default (Radix Dialog for the citation preview, focus rings, ARIA).

**Q: How do you test the frontend?**
Vitest + React Testing Library for components (streaming, citations, upload
validation) and **one Playwright E2E** for login → ask → cited answer, with the
gateway mocked so it runs hermetically.

---

## AI / LLM engineering

**Q: How do you know your RAG is good?**
`make eval`. Retrieval: hit-rate@k and MRR on a gold set — that's how I justified
reranking (MRR ~0.72 → ~0.93). Generation: Ragas faithfulness / relevancy /
context precision+recall. Details: `docs/ai/evaluation.md`.

**Q: Why hybrid retrieval + reranking?**
Vectors match meaning, keyword search matches exact tokens (IDs, names); I fuse both
with Reciprocal Rank Fusion, then a cross-encoder reranks the top-N because it scores
the (query, chunk) pair jointly. `docs/ai/rag-architecture.md`.

**Q: Hallucination / prompt injection?**
Grounded-only answering (no context → fixed sentinel, LLM never called) + an input
injection screen that refuses jailbreaks before retrieval. Faithfulness is my
generation-side metric. `docs/ai/guardrails.md`.

**Q: Cost / debugging in production?**
Every LLM call is traced in Langfuse (prompt, tokens, cost, latency); rate limiting
at the gateway caps spend. Deferred (and I can speak to): semantic caching, a model
router, agentic tool-calling — `docs/ai/next-steps.md`.

**Q: Are you locked into OpenAI?**
No — the LLM layer is profile-driven. One env var (`LLM_PROVIDER`) switches between
OpenAI, Anthropic, and a 100%-local/free Ollama stack; the model, embeddings,
dimensions, and a per-provider vector collection are derived, so I can flip back and
forth with no re-index. `docs/ai/local-ollama.md`.

---

## Frontend / UX

**Q: Walk me through the UI.**
A React 18 + TS app with a shadcn/ui (Radix + Tailwind) design system and an
apple.com-style marketing landing for signed-out users. CSS-variable tokens give
instant light/dark; the chat streams tokens with a skeleton, and citation chips open
the exact source passage. Served by Nginx with `no-cache` on `index.html` so deploys
show immediately. Tested with Vitest + a hermetic Playwright E2E.

---

## The closer
*"Every decision is documented with its trade-off — there are ADRs, a Java glossary,
and an eval suite. I optimized for being able to defend the system, not just demo
it."*
