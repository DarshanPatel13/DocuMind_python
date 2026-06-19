# DocuMind Learning Guide (Full-Stack Edition)

This guide makes the project *yours*. Read it top to bottom, then have Claude quiz you on Section 4 — alternating AI, Python, and React.

---

## 1. Big picture

### What RAG is

A large language model only knows its training data. It knows nothing about *your* PDFs, and when asked about things it hasn't seen it tends to produce fluent, confident, wrong answers — hallucinations. **Retrieval-Augmented Generation (RAG)** splits the job in two: a *retrieval* system finds the passages most relevant to the question, and the LLM is asked to answer **only from those passages**. The model stops being an oracle and becomes a reading-comprehension engine over your data, with citations, and with no training or fine-tuning.

The enabling trick is the **embedding**: a function mapping text to a point in high-dimensional space so that texts with similar *meaning* land near each other. "What's the refund window?" and "Customers may return products within 30 days" share almost no words, yet their embeddings are neighbours — which is why retrieval is semantic, not keyword.

### Why this architecture

- **FastAPI** — async Python web framework; ideal for an app that is mostly I/O (DB, Kafka, OpenAI calls) and needs streaming.
- **LangChain** — orchestrates the RAG plumbing: text splitting, the PGVector store, embeddings, message/prompt types, and streaming.
- **PostgreSQL + pgvector** — chunks and vectors in one boring, transactional database.
- **Kafka** — decouples the slow ingestion work from the upload request; gives retries, backpressure, a dead-letter topic, and idempotency.
- **MongoDB** — append-only conversation history, always read back whole by id.
- **React + TanStack Query** — typed UI; TanStack Query handles server-state caching, polling, and invalidation; the answer streams in via SSE.

### Walkthrough 1 — upload → ingestion

1. The **UploadDropzone** component (`frontend/src/components/UploadDropzone.tsx`) validates the file client-side and calls the **useUpload** hook, which posts to the API via `uploadDocument` (`frontend/src/api/documind.ts`).
2. **`upload_document`** in `backend/app/api/routes_documents.py` reads the bytes and calls **`document_service.upload`**.
3. **`document_service.upload`** (`backend/app/services/document_service.py`) runs **`validate_pdf`** (size, type, `%PDF` magic bytes), writes the file to `./storage/{id}.pdf`, inserts a `DocumentRow` (status `UPLOADED`) via SQLAlchemy, and calls **`producer.publish`** with a `DocumentUploadedEvent`. The API returns **202** immediately.
4. **`IngestionConsumer._run`** (`backend/app/kafka/consumer.py`, group `documind-ingestion`) receives the event and calls **`_handle`**, which drives the retry loop around **`ingestion_service.ingest`**.
5. **`ingestion_service.ingest`** (`backend/app/services/ingestion_service.py`) checks idempotency (skip if `READY`), sets `PROCESSING`, extracts text with **`extract_pdf_text`** (pypdf), splits it with **`split_text`** (`backend/app/rag/chunking.py`), and calls **`vector_store.add_chunks`**.
6. **`vector_store.add_chunks`** (`backend/app/rag/vector_store.py`) embeds the chunks (OpenAI, via LangChain's PGVector) and upserts them with deterministic ids; status becomes `READY` with the chunk count.
7. On repeated failure, **`_dead_letter`** marks the document `FAILED` and republishes the event to `document-events.DLT`.
8. Meanwhile the **useDocuments** hook is polling `GET /api/documents` every 3s, so the **StatusBadge** advances to READY on its own.

### Walkthrough 2 — ask → retrieval → stream

1. In **ChatView** (`frontend/src/components/ChatView.tsx`) the user submits a question; the **useAsk** hook calls **`streamAsk`** (`frontend/src/api/documind.ts`).
2. **`streamAsk`** issues `POST /api/ask` with `fetch` and reads the response body as a stream.
3. **`ask`** in `backend/app/api/routes_ask.py` (rate-limited 10/min/IP by slowapi) returns a `StreamingResponse` wrapping **`AskService.answer_stream`**.
4. **`AskService.answer_stream`** (`backend/app/services/ask_service.py`) calls **`vector_store.search`** — embed the question, cosine top-4 in pgvector (optionally filtered to one `document_id`).
5. It emits an SSE `citations` event (with the `conversation_id`), then **grounding guard**: if no chunks were retrieved it streams the exact sentinel and never calls the LLM.
6. Otherwise it builds the grounded prompt (**`build_messages`**, `backend/app/rag/prompt.py`) and `async for chunk in chat_model.astream(...)`, emitting a `token` SSE event per chunk.
7. After `done`, it persists the turn via **`conversation_service.save_turn`** (MongoDB).
8. Back in the browser, **`streamAsk`** parses each SSE line and calls handlers; **useAsk** appends each token to `answer`, so **ChatView** re-renders token-by-token and shows **CitationChip**s.

---

## 2. File-by-file walkthrough

### Backend

- **`app/core/config.py`** — `pydantic-settings` Settings: every knob, typed, read once from env/.env. Computes the two Postgres URLs (asyncpg for metadata, psycopg for PGVector).
- **`app/core/logging.py`** — structlog setup; each stage logs `event ... stage=...` key/value lines.
- **`app/core/rate_limit.py`** — the shared slowapi `Limiter`, keyed by client IP.
- **`app/db/postgres.py`** — async SQLAlchemy engine + session factory + `init_db` (creates the `documents` table). The `get_session` dependency yields a session per request.
- **`app/db/mongo.py`** — Motor client, the `conversation_turns` collection, and an index on `conversation_id`.
- **`app/models/document.py`** — the `DocumentRow` ORM model and the `DocumentStatus` enum.
- **`app/models/events.py`** — `DocumentUploadedEvent` (the Kafka payload).
- **`app/models/schemas.py`** — Pydantic request/response models; the API contract that mirrors the frontend types.
- **`app/rag/providers.py`** — `get_embeddings()` / `get_chat_model()`; the only place a concrete provider is named. The Anthropic swap lives here.
- **`app/rag/chunking.py`** — `split_text` wraps `RecursiveCharacterTextSplitter`; converts token counts to characters with the /4 heuristic.
- **`app/rag/vector_store.py`** — the PGVector singleton plus `add_chunks` (upsert by deterministic id) and `search` (cosine top-k with optional filter), each offloaded with `asyncio.to_thread`.
- **`app/rag/prompt.py`** — the system prompt, the `NO_INFO_ANSWER` sentinel, and `build_messages`.
- **`app/rag/pdf_extract.py`** — pypdf behind one function.
- **`app/kafka/producer.py` / `consumer.py`** — aiokafka producer; the `IngestionConsumer` background task with retry/backoff → DLT and manual offset commits.
- **`app/services/document_service.py`** — upload validation + store + metadata + publish; document listing.
- **`app/services/ingestion_service.py`** — the idempotent ingestion pipeline.
- **`app/services/ask_service.py`** — the streamed RAG flow (the five steps in Walkthrough 2).
- **`app/services/conversation_service.py`** — Mongo save/read for history.
- **`app/api/routes_*.py`** — thin FastAPI routers.
- **`app/main.py`** — lifespan (boot DB/Mongo/Kafka, start consumer), CORS, slowapi, exception handlers, route registration, `/health`.

### Frontend

- **`src/types/index.ts`** — TypeScript types mirroring the Pydantic models, plus the `StreamEvent` union.
- **`src/api/client.ts`** — axios instance + `API_BASE_URL` (from `VITE_API_BASE_URL`).
- **`src/api/documind.ts`** — `listDocuments`, `uploadDocument`, `getConversation`, and `streamAsk` (fetch + ReadableStream SSE parser).
- **`src/hooks/useDocuments.ts`** — `useQuery` with `refetchInterval` that polls only while something is still ingesting.
- **`src/hooks/useUpload.ts`** — `useMutation` that invalidates the documents query on success.
- **`src/hooks/useAsk.ts`** — owns the live answer/citations/conversationId state; calls `streamAsk` and appends tokens.
- **`src/hooks/useConversation.ts`** — `useQuery` for one conversation's history (disabled until selected).
- **`src/components/UploadDropzone.tsx`** — drag/drop + click upload, client validation, progress bar.
- **`src/components/DocumentList.tsx` / `StatusBadge.tsx`** — the document list with status badges.
- **`src/components/ChatView.tsx`** — the chat input + streamed answer + citation chips.
- **`src/components/CitationChip.tsx`** — renders `[filename, chunk N]`.
- **`src/components/HistorySidebar.tsx`** — past conversation ids.
- **`src/pages/UploadPage.tsx` / `AskPage.tsx`** — compose the above; `AskPage` adds the document scope selector and history panel.
- **`src/App.tsx` / `main.tsx`** — router, nav, and the providers (QueryClient, Router).

---

## 3. Deep dives

### Chunking (why ~800 tokens + overlap)

One embedding summarizes a whole chunk, so chunk size sets retrieval resolution. **Too big** (e.g. 4,000 tokens): the vector averages many topics, search blurs, and you pay to stuff irrelevant text into every prompt. **Too small** (e.g. 100 tokens): vectors are sharp but the retrieved snippets lack the context the model needs, and answers fragment across chunks. ~800 tokens balances the two. The **100-token overlap** guarantees a sentence cut at a boundary still appears whole in the next chunk. The **chars/4 heuristic**: exact token counts need the model's tokenizer, but chunking only needs to be roughly right, and English averages ~4 chars/token.

### Embeddings & cosine similarity

`text-embedding-3-small` maps text to 1,536 floats. No single dimension is human-meaningful; what matters is geometry — similar meanings sit close. **Cosine similarity** measures the angle between two vectors (it ignores length): `cos(θ) = (A·B)/(‖A‖‖B‖)`, ranging 1 (same direction) → 0 (unrelated) → −1 (opposite). pgvector's `<=>` returns cosine *distance* = 1 − similarity, so smaller is closer and "top-k nearest" is an `ORDER BY ... LIMIT k`.

### pgvector indexing: IVFFlat vs HNSW

**IVFFlat** k-means-clusters vectors and probes only the nearest clusters — cheap to build, light on memory, great to ~100k vectors, but clusters reflect build-time data (REINDEX after a big load). **HNSW** is a layered proximity graph — better recall/latency at scale, no training step, but slower builds and more memory. Rule: IVFFlat until millions of vectors or measurable recall problems, then switch (a one-line index change).

### Grounded prompting / hallucination control

Four layers: (1) **retrieval scoping** — the model only sees text from the user's documents; (2) **the prompt contract** — answer only from context, cite `[filename, chunk N]`, and return an exact sentinel when context is insufficient (exact strings are testable); (3) **temperature 0.2** — low randomness; (4) **the code short-circuit** — zero retrieved chunks ⇒ return the sentinel without calling the model. Citations also give a human verification loop.

### What LangChain actually does here — and life without it

In this project LangChain provides four concrete things: `RecursiveCharacterTextSplitter` (chunking), `OpenAIEmbeddings` (batch embedding calls), `PGVector` (table management + the `<=>` similarity SQL + metadata filtering), and the message/`astream` abstraction over the chat model. **Without LangChain**, the ask path becomes, in raw SDKs:

```python
# 1. embed the question
emb = openai.embeddings.create(model="text-embedding-3-small", input=question).data[0].embedding
# 2. similarity search (raw SQL via psycopg)
rows = cur.execute(
    "SELECT content, filename, chunk_index "
    "FROM chunks ORDER BY embedding <=> %s::vector LIMIT 4", (emb,)
).fetchall()
# 3. build the prompt yourself, then stream
stream = openai.chat.completions.create(
    model="gpt-4o-mini", temperature=0.2, stream=True,
    messages=[{"role": "system", "content": SYSTEM_PROMPT},
              {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}],
)
for chunk in stream:
    token = chunk.choices[0].delta.content or ""
```

So LangChain is *convenience and portability*, not magic: it normalizes providers (the Anthropic swap), owns the pgvector schema, and gives one streaming interface. The cost is a dependency and some indirection — worth it here; for a single hard-coded provider you could drop it.

### Python: FastAPI, async, Pydantic, the consumer

**FastAPI** because the app is I/O-bound (DB, Kafka, OpenAI) and async lets one process handle many concurrent waits cheaply; it also gives Pydantic validation and OpenAPI/Swagger for free, and first-class streaming responses. **Where `await` matters**: every call that waits on the network or disk — `session.commit()`, `producer.send_and_wait`, `chat_model.astream`, Motor queries. Blocking libraries (PGVector, pypdf, file writes) are pushed off the event loop with `asyncio.to_thread`, so one slow embedding call doesn't freeze every other request. **Pydantic** validates request bodies (`AskRequest` rejects an empty question with a 422) and serializes responses; `pydantic-settings` does typed config. **The consumer** runs as an `asyncio.create_task` started in the FastAPI lifespan; it `async for`s over aiokafka, handles each message with the retry/DLT policy, and commits offsets manually so nothing is dropped.

### React: data flow, TanStack Query, streaming, controlled inputs

**Data flow**: pages compose components; components call hooks; hooks call the typed API layer. **TanStack Query vs raw `useEffect`**: Query gives caching, dedup, background refetch, polling (`refetchInterval`), and cache invalidation out of the box — with `useEffect` you'd hand-roll loading/error state, races, and refetch-after-mutation. After an upload, `useUpload` calls `invalidateQueries(['documents'])` so the list refreshes, and `useDocuments` polls until everything is READY. **Streaming**: `streamAsk` uses `fetch` + `response.body.getReader()` (axios can't stream in the browser), decodes chunks, splits on the SSE blank-line, and dispatches `citations`/`token` events; `useAsk` does `setAnswer(prev => prev + token)` so React re-renders incrementally. **Controlled inputs**: the question box is controlled (`value={question}` + `onChange`), so the component state is the single source of truth — enabling the disabled-while-streaming button and a clean reset.

### Why Kafka in the ingestion path

Ingestion takes seconds to minutes (extraction + many embedding calls) and doesn't belong in an HTTP request. Kafka gives: **async** (instant 202), **backpressure** (a burst of uploads queues instead of stampeding the embeddings rate limit), **retries** (exponential backoff for transient failures), **DLT** (poison inputs parked + document marked FAILED), and **idempotency** (at-least-once delivery means duplicates happen, so the READY-skip guard + upsert-by-id make redelivery harmless). Keying by `document_id` preserves per-document ordering and allows horizontal scaling up to the partition count.

### What changes at 10x scale

Run multiple FastAPI workers behind a load balancer (state already lives in Postgres/Mongo/Kafka; move the slowapi limiter to Redis). Add Kafka partitions and ingestion consumers. Pool/replica Postgres; consider HNSW as chunk count grows. Batch embeddings harder and watch provider rate-limit tiers. Add a re-rank step (retrieve 20 → re-rank to 4) and cache embeddings/answers for repeated questions. The shape doesn't change — that's the point of starting with queues and stateless services.

---

## 4. Interview Q&A (first person)

### AI / RAG

**Why ~800-token chunks with 100 overlap?** I picked ~800 tokens as the balance between retrieval precision and answer context. One embedding summarizes a whole chunk, so size sets search resolution: much bigger and the vector averages multiple topics so retrieval blurs and prompts get expensive; much smaller and the snippets lose context and answers fragment across chunks. The 100-token overlap means a sentence cut at a boundary still shows up whole in the next chunk, for about 14% duplication — cheap insurance. I size in characters via chars/4 because chunking only needs to be approximately right.

**How does similarity search work?** Chunks are embedded at ingestion; I embed the question with the same model so they share one space. Cosine similarity measures the angle between vectors — ignoring length — which after training means "how close in meaning." pgvector's `<=>` gives cosine distance, so retrieval is `ORDER BY embedding <=> :q LIMIT 4`, accelerated by the ANN index.

**Why pgvector over Pinecone?** Operational simplicity at my scale. I already run Postgres for metadata, so vectors live transactionally next to their rows — delete a document and its chunks cascade, no cross-system sync. Dedicated vector DBs earn their keep at hundreds of millions of vectors with strict latency SLAs; at tens of thousands of chunks pgvector answers in milliseconds, and the query is plain SQL behind a function so migrating later is bounded.

**Walk through an upload — why Kafka?** Validate (size, type, %PDF bytes) → store under a UUID → insert metadata → publish a Kafka event → return 202. A consumer then sets PROCESSING, extracts, chunks, embeds in batches, upserts to pgvector, sets READY. Kafka is there because ingestion is slow and doesn't belong in the request: I get an instant durable ack, backpressure against the embeddings rate limit, automatic retries, and a DLT for poison inputs — and because delivery is at-least-once, the consumer is idempotent (skip READY, upsert by deterministic id).

**How do you stop hallucination?** Retrieval scoping, a strict prompt contract with an exact "I don't have enough information" sentinel, temperature 0.2, and a code short-circuit that returns the sentinel without calling the model when nothing is retrieved — there's a test asserting the LLM isn't called in that case. Citations make every claim checkable.

**What does each question cost?** Embedding the question: ~30 tokens at $0.02/M ≈ $0.0000006. Chat input ≈ system prompt + 4×800-token chunks + question ≈ 3,300 tokens at $0.15/M ≈ $0.0005; output ~250 tokens at $0.60/M ≈ $0.00015. **≈ $0.00065 per question, ~1,500 per dollar.** A 100-page PDF ingests for ~$0.0015.

**Scale to 1,000 concurrent users?** Stateless FastAPI workers behind a load balancer; rate limiter to Redis; Postgres pooling/replicas and HNSW as vectors grow; more Kafka partitions + consumers for ingestion; the LLM provider's rate limit becomes the bottleneck, so queue requests, cache embeddings, and cache answers for hot question+document pairs.

### Python

**Why FastAPI over Flask/Django?** The app is I/O-bound and benefits from async concurrency, which FastAPI is built around; it also gives Pydantic validation, automatic OpenAPI docs, and clean streaming responses. Django is heavier than I need (no ORM-templating story required here) and Flask's async story is bolt-on.

**Where does async actually help?** Everywhere the app waits on something external — Postgres, Mongo, Kafka, and especially the streamed OpenAI call. `await` lets the event loop serve other requests during those waits. The blocking libraries (PGVector, pypdf) are wrapped in `asyncio.to_thread` so they don't stall the loop.

**What is LangChain doing, and could you do it without it?** Here it gives the text splitter, batched embeddings, the PGVector store (schema + similarity SQL + metadata filter), and a uniform streaming chat interface. I could replace it with the raw OpenAI SDK plus psycopg `ORDER BY embedding <=> %s::vector` and hand-built prompts — I show that in the guide. LangChain buys provider portability and less plumbing, at the cost of a dependency.

**How does Pydantic validation work here?** Request bodies are typed models — `AskRequest` enforces a non-empty, ≤2000-char question, returning a 422 automatically on violation; responses are Pydantic models serialized by FastAPI; and `pydantic-settings` validates configuration at startup.

### React

**Why TanStack Query?** Server state isn't UI state — it's cached, shared, and goes stale. Query handles caching, dedup, background refetch, polling, and invalidation declaratively. I use `refetchInterval` to poll documents only while something is ingesting, and `invalidateQueries` after an upload so the list refreshes without manual wiring.

**How do you render a streamed response token-by-token?** The backend sends SSE; `streamAsk` reads `response.body` with a `ReadableStream` reader, decodes and splits on the SSE delimiter, and calls an `onToken` handler per token. `useAsk` does `setAnswer(prev => prev + token)`, so each token triggers a re-render and the answer grows live. I also send citations as the first event so the chips appear immediately.

**How do you keep the document list fresh after upload?** The upload mutation calls `queryClient.invalidateQueries(['documents'])` on success, which refetches the list; `useDocuments` then polls every 3s while any document is UPLOADED/PROCESSING and stops once all are READY/FAILED.

**Controlled vs uncontrolled inputs in your upload form?** The question input is controlled — React state is the source of truth, which makes the submit button's disabled state and resets trivial. The file input is effectively uncontrolled (you can't set a file's value programmatically for security); I read `e.target.files[0]` on change and validate it.

---

## 5. Glossary

- **RAG** — answering with an LLM whose prompt is augmented by retrieved documents.
- **Embedding** — text → vector mapping where nearby = similar meaning.
- **Token** — sub-word unit models read/bill by; ~4 English chars.
- **Chunking / overlap** — splitting docs into retrieval-sized pieces; repeating boundaries so nothing is lost.
- **Cosine similarity / distance** — closeness of vector directions; distance = 1 − similarity (pgvector `<=>`).
- **Vector store / ANN** — DB indexing vectors for (approximate) nearest-neighbour search.
- **IVFFlat / HNSW** — two pgvector ANN index types (cluster-probe vs proximity graph).
- **Top-K** — number of nearest chunks retrieved (4 here).
- **Grounding / hallucination** — constraining the model to the context / confident unsupported output.
- **System prompt / temperature** — the rule-setting message / sampling randomness.
- **SSE (Server-Sent Events)** — one-way streaming of `data:` lines over HTTP; how tokens reach the browser.
- **Consumer group / at-least-once / idempotency** — Kafka subscription sharing / delivery may duplicate / safe to process twice.
- **DLT / backoff** — dead-letter topic for exhausted retries / doubling retry delays.
- **FastAPI / Uvicorn** — async Python web framework / its ASGI server.
- **async/await / event loop** — cooperative concurrency for I/O / the scheduler running coroutines.
- **Pydantic / SQLAlchemy / Motor** — validation+models / SQL ORM / async Mongo driver.
- **LangChain / PGVector** — RAG orchestration lib / its pgvector store integration.
- **TanStack Query** — React server-state cache (queries, mutations, invalidation).
- **Controlled input** — form element whose value is React state.
- **Vite / Vitest / RTL** — frontend build tool / test runner / React Testing Library.

---

## 6. "Explain it like I built it" (60 seconds)

> "DocuMind is a full-stack RAG app — a FastAPI/LangChain backend and a React/TypeScript frontend — for asking natural-language questions over your own PDFs. You upload a document and the API returns instantly with a 202 while a Kafka consumer does the slow work asynchronously: it extracts the text with pypdf, splits it into ~800-token overlapping chunks, embeds them with OpenAI, and stores the vectors in Postgres with pgvector — with retries, a dead-letter topic, and an idempotent consumer, because at-least-once delivery means duplicates are a *when*. When you ask a question, I embed it, run a cosine-similarity search for the four nearest chunks, and send the model a grounded prompt — answer only from this context, cite every claim, say 'I don't have enough information' otherwise — and if retrieval comes back empty my code returns that sentence without ever calling the model. The answer streams back over Server-Sent Events and the React UI renders it token-by-token with citation chips, while TanStack Query handles caching, polling documents to READY, and refreshing after uploads. It's all behind LangChain interfaces, so switching the chat model to Claude is a config change. Each question costs about a fifteenth of a cent, and I can show you exactly where that number comes from."

---

*Now close this file and have Claude quiz you on Section 4 — one question at a time, alternating AI, Python, and React.*
