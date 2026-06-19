# DocuMind — Full-Stack RAG Document Q&A

DocuMind is a web app where you upload PDF documents and ask natural-language questions about them. Answers are generated with retrieval-augmented generation (RAG): the question is embedded, the most similar chunks are retrieved from PostgreSQL/pgvector, and `gpt-4o-mini` answers **only** from that context — streaming token-by-token to a React UI with `[filename, chunk N]` citations. Ingestion is asynchronous: uploads publish a Kafka event and a background consumer extracts (pypdf), chunks (LangChain), embeds (OpenAI), and indexes the document. Conversation history lives in MongoDB. The backend is **FastAPI + LangChain** (Python 3.12); the frontend is **React 18 + TypeScript + TanStack Query**. The chat model is provider-pluggable — swapping to Anthropic Claude is config + one dependency, no code changes.

## Architecture

```
 FLOW 1 — UPLOAD & INGESTION (async)
 ====================================
  React            FastAPI                         Kafka            Ingestion consumer
   │  POST /api/documents (PDF)                       │                    │
   │ ───────────────► validate (%PDF, <20MB)          │                    │
   │                  store ./storage/{id}.pdf        │                    │
   │                  INSERT documents (UPLOADED) ─────────► [Postgres]    │
   │                  publish document.uploaded ─────►│                    │
   │ ◄─── 202 {document_id}                           │ document-events ──►│
   │                                                  │                    │ status=PROCESSING
   │                                                  │                    │ pypdf extract
   │                                                  │                    │ LangChain split (~800 tok/100)
   │                                                  │                    │ embed batch ──► [OpenAI]
   │                                                  │                    │ upsert ──► [pgvector]
   │                                                  │                    │ status=READY
   │                                                  │  retries → DLT     │
   │                                                  │◄─ document-events.DLT (status=FAILED)

 FLOW 2 — ASK (sync, streamed)
 ====================================
  React (TanStack Query / fetch SSE)        FastAPI                    Stores / LLM
   │  POST /api/ask {question, document_id?}    │                          │
   │ ─────────────────────────────────────────►│ embed question ─────────► [OpenAI]
   │                                            │ top-4 cosine search ────► [pgvector]
   │ ◄── SSE: {citations, conversation_id}      │ grounded prompt ────────► [gpt-4o-mini]
   │ ◄── SSE: {token} {token} {token} …         │ (stream)                 │
   │ ◄── SSE: {done}                            │ persist turn ───────────► [MongoDB]
   │  render answer token-by-token + chips      │                          │
```

## Prerequisites

- Python 3.12, Node 20+, Docker Desktop
- An OpenAI API key with a few dollars of credit ([platform.openai.com](https://platform.openai.com))

## Run the backend

```bash
cd backend

# 1. Infra: Postgres+pgvector, MongoDB, Kafka (KRaft)
docker compose up -d

# 2. Python env + deps
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env        # then set OPENAI_API_KEY in .env

# 4. Run the API (creates tables + Kafka topics, starts the consumer)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs (Swagger): <http://localhost:8000/docs>

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_BASE_URL defaults to http://localhost:8000
npm run dev                 # http://localhost:5173
```

## API (curl)

```bash
# Upload a PDF (202, async ingestion)
curl -X POST http://localhost:8000/api/documents -F "file=@mydoc.pdf"

# List documents (poll until status READY)
curl http://localhost:8000/api/documents

# Ask — streams Server-Sent Events
curl -N -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'

# Scope to one document / continue a conversation
curl -N -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "And for digital goods?", "conversation_id": "<id-from-stream>"}'

# Conversation history
curl http://localhost:8000/api/conversations/<conversation_id>
```

The `/api/ask` stream emits one JSON object per SSE line: first `{"type":"citations",...}`, then many `{"type":"token","token":"..."}`, then `{"type":"done"}`.

## 5-step demo script

1. `docker compose up -d` and `uvicorn app.main:app --reload` (with `OPENAI_API_KEY` set), then `npm run dev` — open <http://localhost:5173>.
2. On **Upload**, drag in a PDF. Watch the status badge go `UPLOADED → PROCESSING → READY` (TanStack Query auto-polls); the backend log shows `stage=processing → chunked → ready`.
3. Go to **Ask**, type a question the document answers — watch the answer **stream in token-by-token** with citation chips.
4. Ask something the document does *not* cover — get the exact "I don't have enough information in the uploaded documents." (hallucination control, live).
5. Reload and open a past conversation from the sidebar — it loads from MongoDB via `GET /api/conversations/{id}`.

## Switching the chat model to Claude

Embeddings stay on OpenAI (Anthropic has no embeddings API), but the chat model swaps with zero code changes — `app/rag/providers.py` only returns a LangChain `BaseChatModel`:

1. `pip install langchain-anthropic`
2. In `backend/.env`: `LLM_PROVIDER=anthropic`, `CHAT_MODEL=claude-sonnet-4-6`, `ANTHROPIC_API_KEY=...`
3. Restart `uvicorn`.

## Tests

```bash
cd backend  && pytest                # chunking, upload validation, grounding, retrieval
cd frontend && npm test              # Vitest + RTL (streaming, citations, upload validation)
```

See [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for the full walkthrough, deep dives, and interview prep across AI/RAG, Python, and React.
