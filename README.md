# DocuMind — Microservices RAG Document Q&A

DocuMind is a full-stack app where you upload PDFs and ask natural-language
questions about them. Answers use **retrieval-augmented generation (RAG)**: the
question is embedded, the most similar chunks are retrieved from
PostgreSQL/pgvector, and the LLM answers **only** from that context — streaming
token-by-token to a React UI with `[filename, chunk N]` citations.

As of Day 1 it runs as **three independent services behind an API gateway**:

| Service | Stack | Responsibility |
|---|---|---|
| **gateway** | FastAPI · PyJWT · bcrypt · Redis · httpx | JWT auth, CORS, rate limiting, streaming reverse proxy |
| **document-service** | FastAPI · aiokafka · SQLAlchemy async | uploads, metadata, async ingestion (extract→chunk→embed) |
| **query-service** | FastAPI · LangChain · Motor | RAG ask flow (streamed SSE), conversation history |
| **frontend** | React 18 · TS · Vite · TanStack Query · Tailwind | upload, streaming chat, history, login |

Shared code lives in two libraries: **`libs/documind_contracts`** (Pydantic
events + DTOs) and **`libs/documind_common`** (LLM/embeddings providers + the
pgvector store + the embedding config the writer and reader must agree on).

> Coming from Java/Spring? Every component maps to something you know — see
> [`docs/for-java-devs.md`](docs/for-java-devs.md) *(added Day 3)* and the
> architecture decision record [`docs/adr/0001`](docs/adr/0001-microservices-split.md).

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
                         Redis (rate-limit)              └──▶ OpenAI (embeddings + chat)
```

## Prerequisites
- Docker Desktop
- An OpenAI API key with a little credit ([platform.openai.com](https://platform.openai.com))
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

## Switching the chat model to Claude
Embeddings stay on OpenAI (Anthropic has no embeddings API); the chat model swaps
with zero code changes. In `.env`: `LLM_PROVIDER=anthropic`,
`CHAT_MODEL=claude-sonnet-4-6`, `ANTHROPIC_API_KEY=...`, add `langchain-anthropic`
to `services/query-service/requirements.txt`, and rebuild.

## Roadmap
- **Day 2** — AI/LLM depth: hybrid retrieval + reranking, Ragas evaluation
  (`make eval`), Langfuse LLM observability, formalized guardrails.
- **Day 3** — UI glow-up (shadcn/ui), distributed tracing, Playwright E2E, and the
  docs that explain it all (`docs/for-java-devs.md`, interview cheatsheet, runbook).

See [`docs/adr/0001-microservices-split.md`](docs/adr/0001-microservices-split.md)
for why the architecture looks the way it does and what's deliberately deferred.
