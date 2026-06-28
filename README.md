# DocuMind — Microservices RAG Document Q&A

[![CI](https://github.com/DarshanPatel13/DocuMind_python/actions/workflows/ci.yml/badge.svg)](https://github.com/DarshanPatel13/DocuMind_python/actions/workflows/ci.yml)

DocuMind is a full-stack app where you upload PDFs and ask natural-language
questions about them. Answers use **retrieval-augmented generation (RAG)**: the
question is embedded, the most similar chunks are retrieved from
PostgreSQL/pgvector, and the LLM answers **only** from that context — streaming
token-by-token to a React UI with `[filename, chunk N]` citations.

It runs the hosted models (OpenAI/Anthropic) **or 100% free and offline on your
own machine** (Ollama) — switched with a single environment variable. It runs as
**three independent services behind an API gateway**:

| Service | Stack | Responsibility |
|---|---|---|
| **gateway** | FastAPI · PyJWT · bcrypt · Redis · httpx | JWT auth, CORS, rate limiting, streaming reverse proxy |
| **document-service** | FastAPI · aiokafka · SQLAlchemy async | uploads, metadata, async ingestion (extract→chunk→embed) |
| **query-service** | FastAPI · LangChain · Motor | RAG ask flow (streamed SSE), conversation history |
| **frontend** | React 18 · TS · Vite · TanStack Query · Tailwind | upload, streaming chat, history, login |

Shared code lives in two libraries: **`libs/documind_contracts`** (Pydantic
events + DTOs) and **`libs/documind_common`** (LLM/embeddings providers + the
pgvector store + the embedding config the writer and reader must agree on).

> 📐 **Full design:** [`docs/HLD.md`](docs/HLD.md) is the complete high-level
> design — every service, the data stores, the AI pipeline, and the UI, with
> diagrams. Coming from Java/Spring? See [`docs/for-java-devs.md`](docs/for-java-devs.md).

## Architecture

See [`docs/architecture/container.md`](docs/architecture/container.md) for the C4
container diagram and the two request flows. In short:

```
                         ┌────────────┐
  Browser ──HTTPS──▶ gateway ──REST──▶ document-service ──▶ Postgres (documents)
  (React)            (JWT, CORS,        │  └─Kafka──▶ ingestion consumer ──▶ pgvector (write)
                      rate-limit,       │
                      SSE passthrough) ─┴─REST + SSE──▶ query-service ──▶ pgvector (read)
                                                         └──▶ MongoDB (conversation history)
                         Redis (rate-limit)              └──▶ OpenAI / Ollama (embeddings + chat)
```

## Prerequisites
- Docker Desktop
- Either an OpenAI API key ([platform.openai.com](https://platform.openai.com)) **or**
  nothing at all — run free/offline with Ollama (below).
- (For local, non-Docker dev: Python 3.12, Node 20+)

## Quickstart — one command

```bash
cp .env.example .env          # then set OPENAI_API_KEY in .env
docker compose up --build     # or:  make up
```

- Frontend: <http://localhost:5173>
- Gateway (API): <http://localhost:8080> — interactive docs at `/docs`
- **Login:** `demo` / `demo12345`

Then: **Upload** a PDF, watch the status go `UPLOADED → PROCESSING → READY`, go to
**Ask**, and watch a grounded answer stream in with citation chips.

### …or run it free & offline (no API key)
```bash
make ollama-up                # starts Ollama + pulls llama3.2:3b + nomic-embed-text
echo "LLM_PROVIDER=ollama" >> .env
docker compose up -d document-service query-service
```
That one variable derives the local models, dimensions, and a dedicated vector
collection. Details: [`docs/ai/local-ollama.md`](docs/ai/local-ollama.md).

## Make targets

```bash
make up      # build + start the whole stack
make down    # stop it
make logs    # tail all logs
make test    # run every service's unit tests (in containers)
make ps      # show running containers
```

## API (through the gateway)

```bash
# 1. Log in -> JWT
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Upload a PDF (202, async ingestion)
curl -X POST http://localhost:8080/api/documents \
  -H "Authorization: Bearer $TOKEN" -F "file=@mydoc.pdf"

# 3. List documents (poll until READY)
curl http://localhost:8080/api/documents -H "Authorization: Bearer $TOKEN"

# 4. Ask — streams Server-Sent Events
curl -N -X POST http://localhost:8080/api/ask \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'
```

The `/api/ask` stream emits one JSON object per SSE line: first
`{"type":"citations",...}`, then many `{"type":"token","token":"..."}`, then
`{"type":"done"}`.

## Tests

```bash
make test                                   # all services, in containers
# or per service, locally:
cd services/gateway          && pytest      # JWT + bcrypt
cd services/document-service && pytest      # chunking, upload validation
cd services/query-service    && pytest      # grounding, retrieval
cd frontend                  && npm test    # Vitest + RTL
```

## Switching the LLM provider (one variable)
Set **only** `LLM_PROVIDER`; the chat model, embedding model, dimensions, and a
**per-provider vector collection** are derived automatically (so switching back and
forth never needs a re-index):

| `LLM_PROVIDER` | Chat | Embeddings | Cost |
|---|---|---|---|
| `openai` *(default)* | gpt-4o-mini | text-embedding-3-small | paid |
| `anthropic` | claude-sonnet-4-6 | OpenAI (no Anthropic embeddings) | paid |
| `ollama` | llama3.2:3b | nomic-embed-text | **free / offline** |

Then `docker compose up -d document-service query-service`. Any field is still
overridable (e.g. `CHAT_MODEL=qwen2.5:1.5b` for low-RAM boxes — fits the full stack
in a ~3.66 GB Docker cap). Details:
[`docs/ai/local-ollama.md`](docs/ai/local-ollama.md).

## AI / LLM engineering
- **Hybrid retrieval** (pgvector + Postgres full-text) fused with Reciprocal Rank
  Fusion, plus an optional cross-encoder **reranker**.
- **Evaluation:** `make eval` reports hit-rate@k / MRR (±rerank) and Ragas
  faithfulness/relevancy/precision/recall — see [`docs/ai/evaluation.md`](docs/ai/evaluation.md).
- **Observability:** Langfuse traces every LLM call (`make observability`).
- **Guardrails:** grounded-only answering + prompt-injection screening.

Full AI docs: [`docs/ai/`](docs/ai/).

## UI & quality
- An **apple.com-style landing page** (gradient hero, product sections, integrated
  sign-in) plus a shadcn/ui + Radix + Tailwind app — light/dark theme, glass
  surfaces, streaming chat with skeletons, and citation chips that open a
  **source-text preview**.
- **Distributed trace** via a propagated `X-Request-ID` correlation id across all
  services (see the runbook).
- Tests: pytest (29) + Vitest/RTL (4) + a hermetic **Playwright** E2E.

## Documentation
| Doc | What |
|---|---|
| [`docs/HLD.md`](docs/HLD.md) | **High-level design** — everything, with diagrams (start here) |
| [`docs/architecture/container.md`](docs/architecture/container.md) | C4 diagram + request flows |
| [`docs/adr/0001-microservices-split.md`](docs/adr/0001-microservices-split.md) | why the split, trade-offs, deferred work |
| [`docs/for-java-devs.md`](docs/for-java-devs.md) | Python/React/AI ↔ Spring/Java glossary |
| [`docs/architecture/code-structure.md`](docs/architecture/code-structure.md) | **where each file lives + its Spring layer** (read if "why no service/repo folders?") |
| [`docs/ai/`](docs/ai/) | RAG architecture, evaluation, observability, guardrails |
| [`docs/interview/cheatsheet.md`](docs/interview/cheatsheet.md) | Q&A grounded in this code |
| [`docs/runbook.md`](docs/runbook.md) | run it, demo script, failure drill, trace how-to |

## Deferred (deliberate next steps)
gRPC for internal calls, a dedicated retrieval-service, Traefik/Keycloak,
Kubernetes/Helm, OpenTelemetry + Jaeger, and the AI items in
[`docs/ai/next-steps.md`](docs/ai/next-steps.md) (agents, MCP, semantic caching,
model router). Each is noted so it can be discussed, not hand-waved.
