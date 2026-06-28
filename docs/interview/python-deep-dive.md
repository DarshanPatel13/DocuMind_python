# Python deep-dive — rehearsal sheet (for a Python-expert interviewer)

Questions a senior Python engineer is likely to ask about **this** codebase, with
answers grounded in the actual files. Read the file, then say the answer in your
own words.

---

## 1. Async & the event loop  ← they will ask this first

**Q: It's FastAPI/async — how do you keep blocking work off the event loop?**
Any synchronous/blocking call is pushed to a worker thread with
`asyncio.to_thread(...)`, so the loop stays free to handle other requests:
- pgvector via LangChain `PGVector` is a **sync** client → wrapped in `vector_store.py`.
- the raw `psycopg` full-text query → wrapped in `retrieval.py`.
- PDF parsing and the file write → wrapped in `ingestion.py` / `service.py`.

**Q: Where do you use real async I/O instead?**
Everywhere a native async driver exists: `asyncpg` (via SQLAlchemy async engine),
`Motor` (Mongo), `aiokafka` (produce/consume), `httpx.AsyncClient` (gateway proxy).
Rule of thumb: *async driver where one exists; thread-pool the unavoidable sync bits.*

**Q: Any concurrency within a request?**
Yes — the two retrieval arms run concurrently:
```python
vector_docs, keyword_docs = await asyncio.gather(
    _vector_candidates(...), _keyword_candidates(...))
```
(`retrieval.py`). They're independent, so `gather` halves latency.

**Q: `to_thread` vs `run_in_executor`?** `to_thread` is the 3.9+ high-level wrapper
over `loop.run_in_executor(None, ...)` with the default `ThreadPoolExecutor` —
same thing, nicer API. Fine for I/O-bound blocking; for CPU-bound you'd use a
`ProcessPoolExecutor`.

---

## 2. SSE token streaming end-to-end

**Q: How does a token reach the browser?**
`chat_model.astream(messages)` yields chunks → `ask_service.answer_stream` is an
**async generator** that `yield`s `data: {...}\n\n` SSE frames → wrapped in a
FastAPI `StreamingResponse`. The gateway forwards it **without buffering**:
`httpx` opens the upstream in stream mode and re-emits `aiter_raw()` chunks, with
the client built as `Timeout(60.0, read=None)` so an in-flight stream is never
cut off (`proxy.py`). The citations event is sent first, then tokens, then `done`.

---

## 3. Project layout & packaging

**Q: Why no `service/` / `repository/` / `util/` folders?**
Python expresses a layer as a **module**, not a folder of one-class files.
`routes.py` is the controller tier, `*_service.py` the service tier,
`vector_store.py`/`mongo.py`/`models.py` the persistence tier. Folders only appear
when a module grows too big — a flat module is the idiomatic default.

**Q: How is the code shared between services?**
`libs/documind_contracts` (DTOs/events) and `libs/documind_common` (config,
providers, retrieval, persistence) are **real installable packages** with their
own `pyproject.toml`, `pip install`-ed in each Dockerfile. So two services can't
disagree on a payload shape, and the build caches them as a separate layer
(libs → deps → app code).

**Q: Tooling?** `pyproject.toml` per project, `requires-python=">=3.12"`, **ruff**
(lint+format), `pytest` with `asyncio_mode="auto"`. `from __future__ import
annotations` everywhere for cheap lazy-evaluated type hints.

---

## 4. Pydantic v2 & config

**Q: How is config handled?**
`pydantic-settings` `Settings` loaded once from env/.env. The provider profile
(model, embedding model, dimensions, collection) is derived in a
`model_validator` from a single `LLM_PROVIDER` value, and any field stays
env-overridable. DTOs/events are Pydantic v2 models in the shared contracts lib —
validation at the boundary, typed everywhere inside.

---

## 5. Testing

**Q: How do you test the ask flow without calling an LLM?**
`AskService` takes an **injectable** `chat_model` (constructor arg); tests pass an
`AsyncMock` whose `astream` yields canned chunks, and `monkeypatch` swaps
retrieval/persistence. `asyncio_mode="auto"` lets `async def test_...` run without
boilerplate. See `tests/test_whole_document.py`, `test_ask_grounding.py`.

---

## 6. The AI/RAG specifics they may drill

- **Provider seam** — callers use `get_chat_model()` / `get_embeddings()` and
  depend only on LangChain's `BaseChatModel`/`Embeddings`, never a vendor class;
  switching is one env var (`providers.py`).
- **Embedding dimension is a storage contract** — a pgvector collection has a fixed
  dimension, so each provider gets its **own** collection (`documind_openai` 1536-d
  vs `documind_ollama` 768-d); that's why you can't hot-swap embeddings on existing
  vectors without re-indexing.
- **Hybrid retrieval + RRF** — dense (semantic) + sparse (exact tokens/IDs) fused by
  Reciprocal Rank Fusion (`score = Σ 1/(k+rank)`), no score calibration needed
  (`retrieval.py`). Measured better than either arm in `eval/`.
- **Grounded-only answering** — empty retrieval ⇒ fixed sentinel, the LLM is never
  called, so it can't hallucinate from nothing (`ask_service.py`).
- **Whole-document mode** — `intent.py` detects "list all / summarize" and reads all
  chunks of one doc instead of top-k (top-k can't enumerate a whole document).

---

## 7. Own the trade-offs (a senior *will* probe these)

- **Module-level singletons via `global`** (`get_vector_store`, `get_client`,
  `producer._producer`) — lazy, single-process, simple. Alternative I'd reach for
  under DI pressure: FastAPI `lifespan` + `app.state`, or a small DI container.
- **Broad `except Exception`** in the keyword arm and consumer retry — **deliberate**
  graceful degradation (keyword arm is best-effort; the consumer retries then
  dead-letters), tagged `# noqa: BLE001` so it's clearly intentional, not lazy.
- **`psycopg.connect` per keyword query** (no pool) — fine at this scale; under load
  I'd add `psycopg_pool` or move the query to async `asyncpg`.
- **Shared pgvector store across two services** — a documented compromise
  (`docs/adr/0001`); the clean version is a dedicated retrieval-service owning the
  store. Know it, name it as the next step.

---

## One-liners to have ready
- *"Async-first: native async drivers where they exist, `asyncio.to_thread` for the
  unavoidable sync libraries, `asyncio.gather` for independent work."*
- *"Shared code is packaged as installable libraries, so the wire contract can't
  drift between services."*
- *"The LLM provider is an abstraction seam behind two functions — OpenAI, Anthropic,
  or local Ollama by one env var, zero code change."*
- *"I lean on heuristics where they're explainable (intent, injection screening) and
  call them out as a first filter, not a complete defence."*
