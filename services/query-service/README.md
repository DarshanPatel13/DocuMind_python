# query-service

Owns the **read side** of DocuMind: retrieval-augmented answering and
conversation history.

## Responsibility
- `POST /api/ask`: embed the question → top-k cosine search in pgvector
  (optionally scoped to one document) → build a grounded prompt → **stream** the
  answer token-by-token as SSE → persist the turn.
- Grounding guard: if retrieval returns nothing, return the exact sentinel and
  **never call the LLM** (hallucination control).
- `GET /api/conversations/{id}`: replay a conversation from MongoDB.

## API (behind the gateway)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/ask` | stream a grounded answer (SSE) |
| `GET` | `/api/conversations/{id}` | conversation history |
| `GET` | `/health` | liveness |
| `GET` | `/ready` | readiness (MongoDB reachable) |

## Data owned
- MongoDB `conversation_turns` collection.
- **Reads** the shared pgvector store for retrieval (see `docs/adr/0001`).

## Run / test
```bash
pip install -e ../../libs/documind_contracts -e ../../libs/documind_common
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
pytest
```

## Java analogy
A Spring Boot service whose controller returns a reactive `Flux<String>`
(token stream) — here it's a FastAPI `StreamingResponse` over Server-Sent Events.
